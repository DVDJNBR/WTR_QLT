# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Hub'eau Water Quality Ingestion (Delta Live Tables)
# MAGIC
# MAGIC Ingestion pipeline from Hub'eau API to Bronze layer using **Delta Live Tables**.
# MAGIC
# MAGIC **Features**:
# MAGIC - Native Databricks DLT integration
# MAGIC - Data quality expectations
# MAGIC - Automatic monitoring and lineage
# MAGIC - Incremental ingestion support
# MAGIC
# MAGIC **Source**: https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import dlt
from pyspark.sql.functions import *
from pyspark.sql.types import *
import requests
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def fetch_water_quality_data(start_date: datetime, end_date: datetime):
    """
    Fetch water quality data from Hub'eau API for a date range.

    Args:
        start_date: Start date for ingestion
        end_date: End date for ingestion

    Yields:
        dict: Individual water quality records
    """
    parsing_date = start_date
    total_records = 0

    logger.info(f"Starting ingestion from {start_date.date()} to {end_date.date()}")

    while parsing_date <= end_date:
        date_str = parsing_date.strftime("%Y-%m-%d")
        day_after = parsing_date + timedelta(days=1)
        day_after_str = day_after.strftime("%Y-%m-%d")

        page = 1
        day_total = 0

        while True:
            # API parameters - date_min and date_max must be different
            params = {
                "date_min_prelevement": date_str,
                "date_max_prelevement": day_after_str,
                "size": 20000,
                "page": page
            }

            try:
                response = requests.get(
                    f"{BASE_URL}/resultats_dis",
                    params=params,
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("data", [])

                if not results:
                    break

                # Add metadata to each record
                for record in results:
                    record["ingestion_timestamp"] = datetime.now().isoformat()
                    record["source"] = "hubeau_api"
                    record["ingestion_year"] = parsing_date.year
                    yield record

                day_total += len(results)
                logger.info(f"{date_str} page {page}: {len(results)} records")

                # Last page if less than page size
                if len(results) < 20000:
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error on {date_str} page {page}: {e}")
                break

        if day_total > 0:
            total_records += day_total
            logger.info(f"{date_str}: TOTAL {day_total} records ({page} pages)")
        else:
            logger.info(f"{date_str}: 0 records")

        parsing_date += timedelta(days=1)

    logger.info(f"Ingestion complete: {total_records} total records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Table - Raw Data Ingestion

# COMMAND ----------

@dlt.table(
    name="water_quality_bronze",
    comment="Raw water quality data from Hub'eau API - Bronze layer",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.zOrderCols": "date_prelevement,code_commune"
    }
)
@dlt.expect("valid_date", "date_prelevement IS NOT NULL")
@dlt.expect("valid_result", "resultat_numerique IS NOT NULL OR resultat_alphanumerique IS NOT NULL")
def water_quality_bronze():
    """
    Bronze table containing raw water quality data from Hub'eau API.

    Data quality rules:
    - Warn if date_prelevement is missing
    - Warn if both resultat_numerique and resultat_alphanumerique are missing
    """
    # Configuration for ingestion dates
    # TODO: Make these configurable via widgets or pipeline parameters
    START_DATE = datetime(2021, 1, 1)
    END_DATE = datetime(2021, 12, 31)

    # Fetch data from API
    records = list(fetch_water_quality_data(START_DATE, END_DATE))

    # Convert to Spark DataFrame
    if records:
        df = spark.createDataFrame(records)
        logger.info(f"Created DataFrame with {len(records)} records")
        return df
    else:
        # Return empty DataFrame with schema if no records
        logger.warning("No records fetched, returning empty DataFrame")
        return spark.createDataFrame([], schema=StructType([]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Enriched - Add Computed Columns

# COMMAND ----------

@dlt.table(
    name="water_quality_bronze_enriched",
    comment="Bronze data with additional computed columns for downstream processing",
    table_properties={
        "quality": "bronze"
    }
)
@dlt.expect_all({
    "valid_prelevement_date": "prelevement_date IS NOT NULL",
    "valid_year": "prelevement_year BETWEEN 2020 AND 2030"
})
def water_quality_bronze_enriched():
    """
    Enriched bronze table with parsed dates and computed columns.

    Adds:
    - prelevement_date: Parsed date from date_prelevement
    - prelevement_year: Extracted year
    - prelevement_month: Extracted month
    - has_numeric_result: Boolean flag for numeric results
    """
    return (
        dlt.read("water_quality_bronze")
        .withColumn("prelevement_date", to_date(col("date_prelevement")))
        .withColumn("prelevement_year", year(col("date_prelevement")))
        .withColumn("prelevement_month", month(col("date_prelevement")))
        .withColumn("has_numeric_result", col("resultat_numerique").isNotNull())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Metrics

# COMMAND ----------

@dlt.table(
    name="bronze_quality_metrics",
    comment="Data quality metrics for bronze layer monitoring"
)
def bronze_quality_metrics():
    """
    Compute data quality metrics for monitoring and alerting.

    Metrics include:
    - Total record count
    - Records with missing dates
    - Records with missing results
    - Records by year
    - Records by source
    """
    df = dlt.read("water_quality_bronze")

    return df.agg(
        count("*").alias("total_records"),
        sum(when(col("date_prelevement").isNull(), 1).otherwise(0)).alias("missing_date_count"),
        sum(when(col("resultat_numerique").isNull(), 1).otherwise(0)).alias("missing_numeric_result_count"),
        countDistinct("code_commune").alias("distinct_communes"),
        countDistinct("libelle_parametre").alias("distinct_parameters"),
        min("date_prelevement").alias("min_date"),
        max("date_prelevement").alias("max_date")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete
# MAGIC
# MAGIC To run this pipeline:
# MAGIC 1. Create a new DLT pipeline in Databricks UI
# MAGIC 2. Select this notebook as the source
# MAGIC 3. Configure target schema and storage location
# MAGIC 4. Run the pipeline
# MAGIC
# MAGIC Next steps:
# MAGIC - Silver layer transformations
# MAGIC - Gold layer aggregations
