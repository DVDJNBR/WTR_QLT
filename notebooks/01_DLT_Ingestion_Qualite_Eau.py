# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Hub'Eau API Ingestion (Eau Potable)
# MAGIC 
# MAGIC Ingestion of Potable Water quality data:
# MAGIC 1. Analyses (`bronze_analyses`) - from `/resultats_dis`
# MAGIC 2. Communes (`bronze_communes`) - from `/communes_udi`
# MAGIC
# MAGIC **Source V1**: https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration & Imports

# COMMAND ----------

import requests
import pandas as pd
import logging

from pyspark.sql.functions import lit, current_timestamp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"

# Azure Data Lake Configuration
try:
    STORAGE_ACCOUNT = dbutils.secrets.get(scope="azure-credentials", key="storage-account-name")
    ACCESS_KEY = dbutils.secrets.get(scope="azure-credentials", key="datalake-access-key")
    spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net", ACCESS_KEY)
except Exception:
    logger.warning("Could not load Databricks secrets. If running locally, this is expected.")
    STORAGE_ACCOUNT = "wtrqltadls" # Fallback from .env

BRONZE_BASE_PATH = f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality"

logger.info(f"Configuration loaded - Bronze Base Path: {BRONZE_BASE_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingestion Helper

# COMMAND ----------

def fetch_and_save_to_bronze(endpoint_name, url_path, target_table_name, extra_params=None):
    """
    Fetch data from Hub'Eau API with pagination and append to a Delta table.
    """
    logger.info(f"Starting ingestion for {endpoint_name}...")
    target_path = f"{BRONZE_BASE_PATH}/{target_table_name}"
    
    page = 1
    params = {"size": 5000} 
    if extra_params:
        params.update(extra_params)
        
    total_records = 0
    
    while True:
        params["page"] = page
        try:
            logger.info(f"Fetching {endpoint_name} - Page {page}...")
            response = requests.get(f"{BASE_URL}{url_path}", params=params, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('data', [])
            
            if not results:
                logger.info("No more data found.")
                break
                
            # Convert to Pandas then Spark
            df_pandas = pd.DataFrame(results)
            
            # Cast all columns to string to avoid schema evolution conflicts in Bronze Layer
            df_pandas = df_pandas.astype(str)
            df_spark = spark.createDataFrame(df_pandas)
            
            # Add Bronze metadata
            df_spark = df_spark.withColumn("ingestion_timestamp", current_timestamp()) \
                               .withColumn("source_api", lit(url_path))
            
            # Write to Delta
            df_spark.write \
                .format("delta") \
                .mode("append") \
                .option("mergeSchema", "true") \
                .save(target_path)
                
            total_records += len(results)
            logger.info(f"{endpoint_name} - Page {page} : {len(results)} records written. Total: {total_records}")
            
            # Pagination logic
            if len(results) < params["size"]:
                logger.info("Last page reached.")
                break
                
            page += 1
            
        except Exception as e:
            logger.error(f"Error on {endpoint_name} page {page}: {e}")
            break
            
    logger.info(f"Finished {endpoint_name}. Total records ingested: {total_records}")
    return target_path

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paramètres d'Extraction

# COMMAND ----------

YEAR = "2024"
# Code département, ex: "75" pour Paris.
DEPARTEMENT = "75" 

logger.info(f"Parameters => Year: {YEAR}, Departement: {DEPARTEMENT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ingestion Analyses (Eau Potable)

# COMMAND ----------

analyses_params = {
    "date_prelevement_debut": f"{YEAR}-01-01",
    "date_prelevement_fin": f"{YEAR}-12-31"
}
if DEPARTEMENT:
    analyses_params["code_departement"] = DEPARTEMENT

fetch_and_save_to_bronze(
    endpoint_name="Analyses", 
    url_path="/resultats_dis", 
    target_table_name="bronze_analyses",
    extra_params=analyses_params
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ingestion Communes

# COMMAND ----------

communes_params = {}
if DEPARTEMENT:
    communes_params["code_departement"] = DEPARTEMENT

fetch_and_save_to_bronze(
    endpoint_name="Communes", 
    url_path="/communes_udi", 
    target_table_name="bronze_communes",
    extra_params=communes_params
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation & Optimisation

# COMMAND ----------

for table_name in ["bronze_analyses", "bronze_communes"]:
    try:
        table_path = f"{BRONZE_BASE_PATH}/{table_name}"
        df = spark.read.format("delta").load(table_path)
        count = df.count()
        logger.info(f"Table {table_name}: {count:,} records.")
        
        # Optimize
        logger.info(f"Optimizing {table_name}...")
        spark.sql(f"OPTIMIZE delta.`{table_path}`")
        
    except Exception as e:
        logger.error(f"Could not load or optimize {table_name}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete
# MAGIC
# MAGIC Bronze ingestion finished for Potable Water. Next: Silver transformation.
