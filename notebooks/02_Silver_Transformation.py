# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Water Quality Data Transformation (Eau Potable)
# MAGIC
# MAGIC Clean and standardize data from the 2 Bronze tables:
# MAGIC 1. `bronze_communes` -> `silver_communes` (Mapping of cities and departments)
# MAGIC 2. `bronze_analyses` -> `silver_mesures` & `silver_conformite`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration & Imports

# COMMAND ----------

import logging
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType
from pyspark.errors.exceptions.base import AnalysisException

# Configure logging
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

BRONZE_BASE_PATH = f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality"
SILVER_BASE_PATH = f"abfss://silver@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality"

def read_bronze_table(table_name):
    try:
        return spark.read.format("delta").load(f"{BRONZE_BASE_PATH}/{table_name}")
    except AnalysisException:
        logger.error(f"Bronze table {table_name} not found. Did you run the Bronze ingestion?")
        return None

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Silver Communes (Géo)

# COMMAND ----------

logger.info("Processing Silver Communes...")
df_bronze_communes = read_bronze_table("bronze_communes")

if df_bronze_communes:
    df_silver_communes = df_bronze_communes \
        .withColumn("commune_code", F.col("code_commune")) \
        .withColumn("commune_name", F.col("nom_commune")) \
        .withColumn("department_code",
            F.when(F.col("code_commune").startswith("97"), F.col("code_commune").substr(1, 3))
            .otherwise(F.col("code_commune").substr(1, 2))
        )

    keep_cols = ["commune_code", "commune_name", "department_code"]
    df_silver_communes = df_silver_communes.select(*keep_cols).dropDuplicates(["commune_code"])
    
    # Write to Silver
    df_silver_communes.write.format("delta").mode("overwrite").save(f"{SILVER_BASE_PATH}/silver_communes")
    logger.info(f"Silver Communes written: {df_silver_communes.count()} records.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Silver Mesures

# COMMAND ----------

logger.info("Processing Silver Mesures (from Analyses)...")
df_bronze_analyses = read_bronze_table("bronze_analyses")

if df_bronze_analyses:
    # Map API V1 (Eau Potable) columns
    df_silver_mesures = df_bronze_analyses \
        .withColumn("commune_code", F.col("code_commune")) \
        .withColumn("department_code", F.col("code_departement")) \
        .withColumn("sampling_date", F.to_timestamp("date_prelevement")) \
        .withColumn("parameter_code", F.col("code_parametre")) \
        .withColumn("parameter_name", F.col("libelle_parametre")) \
        .withColumn("numeric_result", F.col("resultat_numerique").cast(DoubleType())) \
        .withColumn("unit", F.col("libelle_unite")) \
        .withColumn("sampling_id", F.col("code_prelevement"))

    # Deduplicate and basic cleaning
    keep_cols = ["sampling_id", "commune_code", "department_code", "sampling_date", "parameter_code", "parameter_name", "numeric_result", "unit"]
    df_silver_mesures = df_silver_mesures.select(*keep_cols).dropDuplicates()

    # Partition by year AND department (brief requirement)
    df_silver_mesures = df_silver_mesures.withColumn("sampling_year", F.year("sampling_date"))
    df_silver_mesures.write.format("delta").mode("overwrite").partitionBy("sampling_year", "department_code").save(f"{SILVER_BASE_PATH}/silver_mesures")
        
    logger.info(f"Silver Mesures written: {df_silver_mesures.count()} records.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Silver Conformité

# COMMAND ----------

logger.info("Processing Silver Conformite...")

if df_bronze_analyses:
    # Logic: 'C' means Compliant, 'N' means Non-Compliant (standard Hub'Eau codes)
    # The API provides 'conformite_limites_pc_prelevement' and 'conformite_limites_bact_prelevement'

    df_silver_conformite = df_bronze_analyses \
        .withColumn("sampling_id", F.col("code_prelevement")) \
        .withColumn("sampling_date", F.to_timestamp("date_prelevement")) \
        .withColumn("department_code", F.col("code_departement")) \
        .withColumn("parameter_code", F.col("code_parametre")) \
        .withColumn("is_compliant_pc", F.when(F.col("conformite_limites_pc_prelevement") == "C", True).otherwise(False)) \
        .withColumn("is_compliant_bact", F.when(F.col("conformite_limites_bact_prelevement") == "C", True).otherwise(False)) \
        .withColumn("global_conclusion", F.col("conclusion_conformite_prelevement"))

    keep_cols = ["sampling_id", "sampling_date", "department_code", "parameter_code", "is_compliant_pc", "is_compliant_bact", "global_conclusion"]

    df_silver_conformite = df_silver_conformite.select(*keep_cols).dropDuplicates()
    df_silver_conformite = df_silver_conformite.withColumn("sampling_year", F.year("sampling_date"))
    df_silver_conformite.write.format("delta").mode("overwrite").partitionBy("sampling_year", "department_code").save(f"{SILVER_BASE_PATH}/silver_conformite")
    logger.info(f"Silver Conformite written: {df_silver_conformite.count()} records.")

# COMMAND ----------

logger.info("Silver transformation complete!")
