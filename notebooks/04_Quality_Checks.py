# Databricks notebook source
# MAGIC %md
# MAGIC # Quality Checks Layer - Great Expectations (Eau Potable)
# MAGIC 
# MAGIC Validate data quality at the end of the pipeline for the Potable Water project.
# MAGIC NOTE: You may need to run `%pip install great-expectations` on your cluster before executing this.

# COMMAND ----------

# MAGIC %pip install great-expectations

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import great_expectations as gx
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try loading Azure configs from Databricks secrets, fallback to .env defaults if local
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
# MAGIC ## Setup Context & Load Data

# COMMAND ----------

# Initialize variables to avoid unbound errors
batch_communes = None
batch_mesures = None
batch_conformite = None
batch_agg_dept = None

# Initialize Great Expectations context
context = gx.get_context()

try:
    # Load Gold Data into Spark DataFrames
    df_communes = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/dim_communes")
    df_mesures = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/factmesuresqualite")
    df_conformite = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/factconformite")
    df_agg_dept = spark.read.format("delta").load(f"{GOLD_BASE_PATH}/agg_conformite_departement")
    
    # Create GX datasets
    batch_communes = gx.dataset.SparkDFDataset(df_communes)
    batch_mesures = gx.dataset.SparkDFDataset(df_mesures)
    batch_conformite = gx.dataset.SparkDFDataset(df_conformite)
    batch_agg_dept = gx.dataset.SparkDFDataset(df_agg_dept)
    
except Exception as e:
    logger.error(f"Failed to load Gold tables. Ensure previous notebooks ran successfully. Error: {e}")
    dbutils.notebook.exit("Data Load Error")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define Expectations

# COMMAND ----------

# 1. Expectations on Communes
if batch_communes:
    logger.info("Validating dim_communes...")
    batch_communes.expect_column_to_exist("commune_code")
    batch_communes.expect_column_values_to_not_be_null("commune_code")
    batch_communes.expect_column_values_to_be_unique("commune_code")

# 2. Expectations on Mesures
if batch_mesures:
    logger.info("Validating factmesuresqualite...")
    batch_mesures.expect_column_to_exist("numeric_result")
    batch_mesures.expect_column_values_to_not_be_null("sampling_id")
    # Ensure numeric_result is not drastically negative
    batch_mesures.expect_column_values_to_be_between("numeric_result", min_value=0, max_value=1000000)

# 3. Expectations on Conformite
if batch_conformite:
    logger.info("Validating factconformite...")
    batch_conformite.expect_column_to_exist("is_compliant_pc")
    batch_conformite.expect_column_to_exist("is_compliant_bact")
    batch_conformite.expect_column_values_to_be_in_set("is_compliant_pc", [True, False])

# 4. Expectations on KPIs (Aggregations)
if batch_agg_dept:
    logger.info("Validating agg_conformite_departement...")
    batch_agg_dept.expect_column_to_exist("compliance_rate")
    # Compliance rate must be between 0 and 100%
    batch_agg_dept.expect_column_values_to_be_between("compliance_rate", min_value=0, max_value=100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Validation & Review

# COMMAND ----------

logger.info("Running all validations...")
results = []
if batch_communes:
    results.append(batch_communes.validate())
if batch_mesures:
    results.append(batch_mesures.validate())
if batch_conformite:
    results.append(batch_conformite.validate())
if batch_agg_dept:
    results.append(batch_agg_dept.validate())

all_success = all(r["success"] for r in results)

if all_success:
    logger.info("✅ All Data Quality Checks Passed for Potable Water Pipeline!")
else:
    logger.error("❌ Some Data Quality Checks Failed. Please review the detailed reports below.")
    for i, r in enumerate(results):
        if not r["success"]:
            print(f"Failed Validation {i}:", r)
    raise ValueError("Quality Check Failure")

# COMMAND ----------

logger.info("Quality check process completed.")
