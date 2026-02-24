# Databricks notebook source
# MAGIC %md
# MAGIC # Quality Checks Layer - Spark Native (Eau Potable)
# MAGIC
# MAGIC Validate data quality at the end of the pipeline for the Potable Water project.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import logging
from pyspark.sql import functions as F
from pyspark.errors.exceptions.base import AnalysisException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    STORAGE_ACCOUNT = dbutils.secrets.get(scope="azure-credentials", key="storage-account-name")
    ACCESS_KEY = dbutils.secrets.get(scope="azure-credentials", key="datalake-access-key")
    spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net", ACCESS_KEY)
except Exception:
    logger.warning("Could not load Databricks secrets. Using fallback wtrqltadls.")
    STORAGE_ACCOUNT = "wtrqltadls"

GOLD_BASE_PATH = f"abfss://gold@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Gold Data

# COMMAND ----------

try:
    df_communes = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/dim_communes")
    df_mesures = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/factmesuresqualite")
    df_conformite = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/factconformite")
    df_agg_dept = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/agg_conformite_departement")
    logger.info("Gold tables loaded successfully.")
except AnalysisException as e:
    logger.error(f"Failed to load Gold tables. Ensure previous notebooks ran successfully. Error: {e}")
    dbutils.notebook.exit("Data Load Error")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quality Checks

# COMMAND ----------

failures = []

def check(condition, message):
    if not condition:
        failures.append(message)
        logger.error(f"FAIL: {message}")
    else:
        logger.info(f"OK:   {message}")

# --- dim_communes ---
logger.info("Validating dim_communes...")
check("commune_code" in df_communes.columns, "dim_communes: column commune_code exists")
check(df_communes.filter(F.col("commune_code").isNull()).count() == 0, "dim_communes: commune_code has no nulls")
total = df_communes.count()
distinct = df_communes.dropDuplicates(["commune_code"]).count()
check(total == distinct, f"dim_communes: commune_code is unique ({total} rows, {distinct} distinct)")

# --- factmesuresqualite ---
logger.info("Validating factmesuresqualite...")
check("numeric_result" in df_mesures.columns, "factmesuresqualite: column numeric_result exists")
check(df_mesures.filter(F.col("sampling_id").isNull()).count() == 0, "factmesuresqualite: sampling_id has no nulls")
nan_count = df_mesures.filter(F.isnan(F.col("numeric_result"))).count()
check(True, f"factmesuresqualite: {nan_count} NaN numeric_result (paramètres qualitatifs, attendu)")
out_of_range = df_mesures.filter(
    F.col("numeric_result").isNotNull() &
    ~F.isnan(F.col("numeric_result")) &
    ((F.col("numeric_result") < 0) | (F.col("numeric_result") > 1_000_000))
).count()
check(out_of_range == 0, f"factmesuresqualite: numeric_result in [0, 1000000] ({out_of_range} violations)")

# --- factconformite ---
logger.info("Validating factconformite...")
check("is_compliant_pc" in df_conformite.columns, "factconformite: column is_compliant_pc exists")
check("is_compliant_bact" in df_conformite.columns, "factconformite: column is_compliant_bact exists")
invalid_pc = df_conformite.filter(~F.col("is_compliant_pc").isin(True, False)).count()
check(invalid_pc == 0, f"factconformite: is_compliant_pc only contains True/False ({invalid_pc} violations)")

# --- agg_conformite_departement ---
logger.info("Validating agg_conformite_departement...")
check("compliance_rate" in df_agg_dept.columns, "agg_conformite_departement: column compliance_rate exists")
out_of_range_rate = df_agg_dept.filter(
    (F.col("compliance_rate") < 0) | (F.col("compliance_rate") > 100)
).count()
check(out_of_range_rate == 0, f"agg_conformite_departement: compliance_rate in [0, 100] ({out_of_range_rate} violations)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Results

# COMMAND ----------

if not failures:
    logger.info("✅ All Data Quality Checks Passed for Potable Water Pipeline!")
else:
    logger.error(f"❌ {len(failures)} check(s) failed:")
    for f in failures:
        logger.error(f"  - {f}")
    raise ValueError(f"Quality Check Failure: {len(failures)} check(s) failed")

logger.info("Quality check process completed.")
