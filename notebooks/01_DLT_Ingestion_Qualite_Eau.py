# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Hub'eau Water Quality API Ingestion
# MAGIC
# MAGIC Simple ingestion pipeline from Hub'eau API to Bronze Delta Lake layer.
# MAGIC
# MAGIC **Source**: https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration & Imports

# COMMAND ----------

import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
from pyspark.sql.functions import lit

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"

# Azure Data Lake Configuration
STORAGE_ACCOUNT = dbutils.secrets.get(scope="azure-credentials", key="storage-account-name")
BRONZE_PATH = f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality/hubeau"

# Spark configuration for Azure authentication
ACCESS_KEY = dbutils.secrets.get(scope="azure-credentials", key="datalake-access-key")
spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net", ACCESS_KEY)

logger.info(f"Configuration loaded - Bronze Path: {BRONZE_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingestion Parameters

# COMMAND ----------

# Date range configuration
START_DATE = datetime(2021, 1, 1)
END_DATE = datetime.now()

logger.info(f"Ingestion range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Ingestion

# COMMAND ----------

# Initialize
parsing_date = START_DATE
day_after = parsing_date + timedelta(days=1)
total_records = 0

logger.info("Starting ingestion...")

while parsing_date <= END_DATE:
    date_str = parsing_date.strftime("%Y-%m-%d")
    day_after_str = day_after.strftime("%Y-%m-%d")

    # Pagination loop for each day
    page = 1
    day_records = []

    while True:
        # API parameters - KEY: date_min and date_max must be DIFFERENT
        params = {
            "date_min_prelevement": date_str,
            "date_max_prelevement": day_after_str,
            "size": 20000,
            "page": page
        }

        try:
            # Call API
            response = requests.get(f"{BASE_URL}/resultats_dis", params=params, timeout=60)
            response.raise_for_status()

            # Get data
            data = response.json()
            results = data.get('data', [])

            if not results:
                # No more data for this day
                break

            day_records.extend(results)
            logger.info(f"{date_str} page {page}: {len(results)} records")

            # If less than 20K, it's the last page
            if len(results) < 20000:
                break

            page += 1

        except Exception as e:
            logger.error(f"Error on {date_str} page {page}: {e}")
            break

    # Write all records for the day to Delta Lake
    if day_records:
        # Convert to Spark DataFrame
        df_pandas = pd.DataFrame(day_records)
        df_spark = spark.createDataFrame(df_pandas)

        # Add metadata
        df_spark = df_spark.withColumn("ingestion_timestamp", lit(datetime.now()))
        df_spark = df_spark.withColumn("source", lit("hubeau_api"))
        df_spark = df_spark.withColumn("year", lit(parsing_date.year))

        # Write to Delta Lake
        df_spark.write \
            .format("delta") \
            .mode("append") \
            .partitionBy("year") \
            .save(BRONZE_PATH)

        total_records += len(day_records)
        logger.info(f"{date_str}: TOTAL {len(day_records)} records ingested ({page} pages)")
    else:
        logger.info(f"{date_str}: 0 records")

    # Move to next day
    parsing_date += timedelta(days=1)
    day_after += timedelta(days=1)

logger.info(f"Ingestion complete: {total_records:,} total records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

# Read Bronze table
df_bronze = spark.read.format("delta").load(BRONZE_PATH)

total_count = df_bronze.count()
date_range = df_bronze.selectExpr("min(date_prelevement)", "max(date_prelevement)").collect()[0]

logger.info(f"Total records in Bronze: {total_count:,}")
logger.info(f"Date range: {date_range[0]} to {date_range[1]}")

# COMMAND ----------

# Records by year
logger.info("Records by year:")
df_bronze.groupBy("year").count().orderBy("year").show()

# COMMAND ----------

# Preview data
logger.info("Recent data sample:")
display(
    df_bronze.select(
        "date_prelevement",
        "nom_commune",
        "libelle_parametre",
        "resultat_numerique",
        "unite_mesure"
    )
    .orderBy("date_prelevement", ascending=False)
    .limit(10)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optimization

# COMMAND ----------

logger.info("Optimizing Delta table...")
spark.sql(f"OPTIMIZE delta.`{BRONZE_PATH}` ZORDER BY (date_prelevement)")
logger.info("Optimization complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete
# MAGIC
# MAGIC Bronze ingestion finished. Next: Silver transformation.
