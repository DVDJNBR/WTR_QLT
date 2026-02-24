# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer - Analytical Modeling (Eau Potable)
# MAGIC 
# MAGIC Create analytical tables following the Star Schema pattern for the Water Quality data.
# MAGIC 
# MAGIC **Dimensions**:
# MAGIC - `dim_communes`
# MAGIC - `dim_parametres`
# MAGIC - `dim_temps`
# MAGIC 
# MAGIC **Facts**:
# MAGIC - `factmesuresqualite`
# MAGIC - `factconformite`
# MAGIC 
# MAGIC **Aggregations (KPIs)**:
# MAGIC - `agg_conformite_departement`
# MAGIC - `agg_evolution_parametres`
# MAGIC - `agg_alertes_critiques`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration & Imports

# COMMAND ----------

import logging
from pyspark.sql import functions as F
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

SILVER_BASE_PATH = f"abfss://silver@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality"
GOLD_BASE_PATH = f"abfss://gold@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality"

def read_silver_table(table_name):
    try:
        return spark.read.format("delta").load(f"{SILVER_BASE_PATH}/{table_name}")
    except AnalysisException:
        logger.error(f"Silver table {table_name} not found. Ensure Silver pipeline ran successfully.")
        return None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Data

# COMMAND ----------

df_communes = read_silver_table("silver_communes")
df_mesures = read_silver_table("silver_mesures")
df_conformite = read_silver_table("silver_conformite")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Dimensions

# COMMAND ----------

if df_communes:
    logger.info("Building dim_communes...")
    dim_communes = df_communes.select(
        "commune_code",
        "commune_name",
        "department_code"
    ).dropDuplicates(["commune_code"])
    dim_communes.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/dim_communes")

if df_mesures:
    logger.info("Building dim_parametres...")
    dim_parametres = df_mesures.select(
        "parameter_code", 
        "parameter_name", 
        "unit"
    ).dropDuplicates(["parameter_code"])
    dim_parametres.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/dim_parametres")
    
    logger.info("Building dim_temps...")
    dim_temps = df_mesures.select("sampling_date").dropDuplicates(["sampling_date"]).filter(F.col("sampling_date").isNotNull())
    dim_temps = dim_temps \
        .withColumn("date_key", F.date_format("sampling_date", "yyyyMMdd").cast("integer")) \
        .withColumn("year", F.year("sampling_date")) \
        .withColumn("month", F.month("sampling_date")) \
        .withColumn("quarter", F.quarter("sampling_date")) \
        .withColumn("day_of_week", F.dayofweek("sampling_date"))
    dim_temps.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/dim_temps")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Facts

# COMMAND ----------

if df_mesures:
    logger.info("Building factmesuresqualite...")
    fact_mesures = df_mesures \
        .withColumn("date_key", F.date_format("sampling_date", "yyyyMMdd").cast("integer")) \
        .select("sampling_id", "commune_code", "parameter_code", "date_key", "numeric_result")
    
    fact_mesures.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/factmesuresqualite")

if df_conformite:
    logger.info("Building factconformite...")
    fact_conformite = df_conformite \
        .withColumn("date_key", F.date_format("sampling_date", "yyyyMMdd").cast("integer")) \
        .select("sampling_id", "parameter_code", "date_key", "is_compliant_pc", "is_compliant_bact")
        
    fact_conformite.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/factconformite")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Aggregations (KPIs)

# COMMAND ----------

# agg_conformite_departement : KPIs de conformité globale
if df_communes and df_conformite:
    logger.info("Building agg_conformite_departement...")
    # Get commune details for each conformite record
    # Note: We need to join with silver_mesures first to get the commune_code for each sampling_id
    if df_mesures is None:
        logger.warning("df_mesures is None, skipping agg_conformite_departement")
        df_mesures_lite = None
    else:
        df_mesures_lite = df_mesures.select("sampling_id", "commune_code").dropDuplicates()
    
    if df_mesures_lite:
        df_join = df_conformite.drop("department_code").join(df_mesures_lite, on="sampling_id") \
                               .join(df_communes, on="commune_code")
        
        agg_dept = df_join.groupBy("department_code") \
            .agg(
                F.count("*").alias("total_tests"),
                F.sum(F.when(F.col("is_compliant_pc") & F.col("is_compliant_bact"), 1).otherwise(0)).alias("compliant_tests")
            ) \
            .withColumn("compliance_rate", F.round((F.col("compliant_tests") / F.col("total_tests")) * 100, 2))
            
        agg_dept.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/agg_conformite_departement")

# agg_evolution_parametres : Tendances par paramètre
if df_mesures:
    logger.info("Building agg_evolution_parametres...")
    agg_temp = df_mesures \
        .withColumn("year", F.year("sampling_date")) \
        .withColumn("month", F.month("sampling_date")) \
        .groupBy("parameter_name", "year", "month") \
        .agg(
            F.avg("numeric_result").alias("avg_result"),
            F.max("numeric_result").alias("max_result")
        )
        
    agg_temp.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/agg_evolution_parametres")

# agg_alertes_critiques : Focus sur les non-conformités
if df_conformite:
    logger.info("Building agg_alertes_critiques...")
    df_mesures_lite = None
    if df_mesures:
        df_mesures_lite = df_mesures.select("sampling_id", "parameter_name", "commune_code").dropDuplicates()
    
    if df_mesures_lite:
        agg_alertes = df_conformite.filter(
            (~F.col("is_compliant_pc")) | (~F.col("is_compliant_bact"))
        ).join(df_mesures_lite, on="sampling_id") \
         .groupBy("parameter_name") \
         .agg(F.count("*").alias("nb_alertes")) \
         .orderBy(F.col("nb_alertes").desc())
         
        agg_alertes.write.format("delta").mode("overwrite").save(f"{GOLD_BASE_PATH}/agg_alertes_critiques")

# COMMAND ----------

logger.info("Gold Modeling complete!")
