# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Hub'eau Water Quality Ingestion (DLT)
# MAGIC
# MAGIC Simple ingestion from Hub'eau API using Delta Live Tables.
# MAGIC
# MAGIC **Test period**: January 2021 (1 month)

# COMMAND ----------

import dlt
from pyspark.sql.functions import lit, current_timestamp
import requests
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"

# Test with 1 month
START_DATE = datetime(2021, 1, 1)
END_DATE = datetime(2021, 1, 31)

# COMMAND ----------

def fetch_water_quality_data(start_date, end_date):
    """Fetch water quality data from Hub'eau API."""
    parsing_date = start_date
    total_records = 0

    while parsing_date <= end_date:
        date_str = parsing_date.strftime("%Y-%m-%d")
        day_after = (parsing_date + timedelta(days=1)).strftime("%Y-%m-%d")

        page = 1
        day_total = 0

        while True:
            params = {
                "date_min_prelevement": date_str,
                "date_max_prelevement": day_after,
                "size": 20000,
                "page": page
            }

            try:
                response = requests.get(f"{BASE_URL}/resultats_dis", params=params, timeout=60)
                response.raise_for_status()
                results = response.json().get("data", [])

                if not results:
                    break

                for record in results:
                    yield record

                day_total += len(results)
                logger.info(f"{date_str} page {page}: {len(results)} records")

                if len(results) < 20000:
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error on {date_str} page {page}: {e}")
                break

        if day_total > 0:
            total_records += day_total
            logger.info(f"{date_str}: {day_total} records")

        parsing_date += timedelta(days=1)

    logger.info(f"Total: {total_records} records")

# COMMAND ----------

@dlt.table(
    name="water_quality_bronze",
    comment="Raw water quality data from Hub'eau API"
)
@dlt.expect("valid_date", "date_prelevement IS NOT NULL")
def water_quality_bronze():
    """Bronze table: raw data from API."""
    records = list(fetch_water_quality_data(START_DATE, END_DATE))

    if records:
        df = spark.createDataFrame(records)
        df = df.withColumn("ingestion_timestamp", current_timestamp())
        df = df.withColumn("source", lit("hubeau_api"))
        logger.info(f"Ingested {len(records)} records")
        return df
    else:
        logger.warning("No records fetched")
        return spark.createDataFrame([], schema="date_prelevement STRING")