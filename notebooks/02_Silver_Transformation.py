# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Water Quality Data Transformation
# MAGIC
# MAGIC Clean and standardize data from Bronze layer.
# MAGIC
# MAGIC **Transformations**:
# MAGIC - Fix data types (dates, numbers)
# MAGIC - Remove duplicates
# MAGIC - Standardize column names
# MAGIC - Add quality categories
# MAGIC - Partition by year and department

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration & Imports

# COMMAND ----------

import logging
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
STORAGE_ACCOUNT = dbutils.secrets.get(scope="azure-credentials", key="storage-account-name")
ACCESS_KEY = dbutils.secrets.get(scope="azure-credentials", key="datalake-access-key")

BRONZE_PATH = f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality/hubeau"
SILVER_PATH = f"abfss://silver@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality/cleaned"

# Spark configuration
spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net", ACCESS_KEY)

logger.info(f"Bronze: {BRONZE_PATH}")
logger.info(f"Silver: {SILVER_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read Bronze Data

# COMMAND ----------

df_bronze = spark.read.format("delta").load(BRONZE_PATH)

logger.info(f"Bronze records: {df_bronze.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Cleaning

# COMMAND ----------

# Fix data types
df_clean = df_bronze \
    .withColumn("resultat_numerique", F.col("resultat_numerique").cast(DoubleType())) \
    .withColumn("date_prelevement", F.to_timestamp("date_prelevement")) \
    .withColumn("code_departement", F.col("code_departement").cast(IntegerType())) \
    .withColumn("code_commune", F.col("code_commune").cast(IntegerType()))

logger.info("Data types fixed")

# COMMAND ----------

# Remove duplicates based on key columns
df_clean = df_clean.dropDuplicates([
    "code_prelevement",
    "code_parametre",
    "date_prelevement"
])

logger.info(f"After deduplication: {df_clean.count():,} records")

# COMMAND ----------

# Handle nulls - keep rows with essential data
df_clean = df_clean.filter(
    F.col("date_prelevement").isNotNull() &
    F.col("code_commune").isNotNull() &
    F.col("code_parametre").isNotNull()
)

logger.info(f"After null filtering: {df_clean.count():,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Standardization

# COMMAND ----------

# Standardize column names (snake_case)
df_silver = df_clean \
    .withColumnRenamed("code_departement", "department_code") \
    .withColumnRenamed("nom_departement", "department_name") \
    .withColumnRenamed("code_prelevement", "sampling_code") \
    .withColumnRenamed("code_parametre", "parameter_code") \
    .withColumnRenamed("libelle_parametre", "parameter_name") \
    .withColumnRenamed("resultat_numerique", "numeric_result") \
    .withColumnRenamed("libelle_unite", "unit") \
    .withColumnRenamed("code_commune", "city_code") \
    .withColumnRenamed("nom_commune", "city_name") \
    .withColumnRenamed("date_prelevement", "sampling_date") \
    .withColumnRenamed("conclusion_conformite_prelevement", "compliance_conclusion")

logger.info("Columns standardized")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Enrichment

# COMMAND ----------

# Add quality categories based on compliance
df_silver = df_silver.withColumn(
    "quality_category",
    F.when(F.col("compliance_conclusion").contains("conforme aux exigences"), "compliant")
     .when(F.col("compliance_conclusion").contains("non conforme"), "non_compliant")
     .otherwise("unknown")
)

# Add year and month for easier analysis
df_silver = df_silver \
    .withColumn("sampling_year", F.year("sampling_date")) \
    .withColumn("sampling_month", F.month("sampling_date"))

# Add data quality flag
df_silver = df_silver.withColumn(
    "data_quality",
    F.when(F.col("numeric_result").isNotNull(), "valid")
     .otherwise("missing_value")
)

logger.info("Enrichment complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Silver Layer

# COMMAND ----------

# Write partitioned by year and department
df_silver.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("sampling_year", "department_code") \
    .save(SILVER_PATH)

logger.info(f"Silver layer written: {df_silver.count():,} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

# Read back and validate
df_silver_check = spark.read.format("delta").load(SILVER_PATH)

logger.info("=== Silver Layer Statistics ===")
logger.info(f"Total records: {df_silver_check.count():,}")

# COMMAND ----------

# Records by year
logger.info("Records by year:")
df_silver_check.groupBy("sampling_year").count().orderBy("sampling_year").show()

# COMMAND ----------

# Quality categories distribution
logger.info("Quality categories:")
df_silver_check.groupBy("quality_category").count().show()

# COMMAND ----------

# Sample data
logger.info("Sample data:")
display(
    df_silver_check.select(
        "sampling_date",
        "city_name",
        "parameter_name",
        "numeric_result",
        "unit",
        "quality_category"
    )
    .orderBy("sampling_date", ascending=False)
    .limit(10)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optimization

# COMMAND ----------

logger.info("Optimizing Delta table...")
spark.sql(f"OPTIMIZE delta.`{SILVER_PATH}` ZORDER BY (sampling_date, city_code)")
logger.info("Optimization complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete
# MAGIC
# MAGIC Silver transformation finished. Next: Gold aggregations.
