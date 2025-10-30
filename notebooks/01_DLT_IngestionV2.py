# Databricks notebook source
# MAGIC %md
# MAGIC # Hub'eau Water Quality Data Ingestion (DLT Version)
# MAGIC
# MAGIC Ingests water quality data from Hub'eau API to Bronze2 layer using dlthub.

# COMMAND ----------

# MAGIC %pip install dlt[filesystem]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import dlt
from dlt.sources.helpers import requests
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"
START_DATE = datetime(2021, 1, 1)
END_DATE = datetime(2021, 1, 31)

STORAGE_ACCOUNT = dbutils.secrets.get(scope="azure-credentials", key="storage-account-name")
BRONZE2_PATH = f"abfss://bronze2@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality/hubeau"

ACCESS_KEY = dbutils.secrets.get(scope="azure-credentials", key="datalake-access-key")
spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net", ACCESS_KEY)

logger.info(f"Ingestion period: {START_DATE.date()} to {END_DATE.date()}")
logger.info(f"Destination: {BRONZE2_PATH}")

# COMMAND ----------

@dlt.resource(name="water_quality_hubeau", write_disposition="append")
def fetch_water_quality():
    parsing_date = START_DATE
    total_records = 0

    while parsing_date <= END_DATE:
        date_str = parsing_date.strftime("%Y-%m-%d")
        day_after = parsing_date + timedelta(days=1)
        day_after_str = day_after.strftime("%Y-%m-%d")

        page = 1
        day_total = 0

        while True:
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

                for record in results:
                    record["ingestion_timestamp"] = datetime.now().isoformat()
                    record["source"] = "hubeau_api"
                    record["year"] = parsing_date.year
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
            logger.info(f"{date_str}: TOTAL {day_total} records ({page} pages)")
        else:
            logger.info(f"{date_str}: 0 records")

        parsing_date += timedelta(days=1)

    logger.info(f"Ingestion complete: {total_records} total records")

# COMMAND ----------

pipeline = dlt.pipeline(
    pipeline_name="hubeau_water_quality_v2",
    destination="filesystem",
    dataset_name="bronze2_water_quality",
    export_schema_path=BRONZE2_PATH
)

logger.info("Starting DLT pipeline...")
load_info = pipeline.run(fetch_water_quality())
logger.info("Pipeline completed!")

# COMMAND ----------

df = spark.read.parquet(BRONZE2_PATH)
record_count = df.count()

logger.info(f"Validation: {record_count} records loaded")
logger.info("Sample data:")
df.show(5)
