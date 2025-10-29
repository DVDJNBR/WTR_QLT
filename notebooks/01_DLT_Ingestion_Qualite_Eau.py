# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Ingestion API Hub'eau Qualité de l'Eau
# MAGIC
# MAGIC Pipeline d'ingestion des données de qualité de l'eau depuis l'API Hub'eau vers la couche Bronze.
# MAGIC
# MAGIC **Source** : https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable
# MAGIC
# MAGIC **Architecture** :
# MAGIC - Détecte la dernière date ingérée (ou commence à 2021-01-01)
# MAGIC - Boucle jour par jour jusqu'à aujourd'hui
# MAGIC - Écrit en Delta Lake format partitionné par année

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import requests
import pandas as pd
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, to_date
import json

# Configuration API Hub'eau
BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"

# Configuration Delta Lake
BRONZE_PATH = "/mnt/bronze/water_quality/hubeau"
START_DATE = datetime(2021, 1, 1)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fonctions d'ingestion

# COMMAND ----------

def get_last_ingested_date(bronze_path):
    """
    Récupère la dernière date ingérée depuis Bronze
    Retourne START_DATE si aucune donnée
    """
    try:
        df = spark.read.format("delta").load(bronze_path)
        max_date = df.selectExpr("max(to_date(date_prelevement))").collect()[0][0]

        if max_date:
            last_date = datetime.strptime(str(max_date), "%Y-%m-%d")
            print(f"Dernière date ingérée: {last_date.strftime('%Y-%m-%d')}")
            return last_date + timedelta(days=1)
        else:
            print(f"Aucune donnée, démarrage à {START_DATE.strftime('%Y-%m-%d')}")
            return START_DATE

    except Exception as e:
        print(f"Pas de table Bronze existante, démarrage à {START_DATE.strftime('%Y-%m-%d')}")
        return START_DATE

# COMMAND ----------

def fetch_day_data(date_str, max_retries=3):
    """
    Récupère les données pour une journée depuis l'API Hub'eau
    Gère la pagination automatiquement
    """
    all_data = []
    page = 1

    while True:
        params = {
            "date_min_prelevement": date_str,
            "date_max_prelevement": date_str,
            "size": 20000,
            "page": page
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(f"{BASE_URL}/resultats_dis", params=params, timeout=60)
                response.raise_for_status()
                data = response.json()

                results = data.get('data', [])

                if not results:
                    return all_data

                all_data.extend(results)

                # Si moins de 20000 résultats, c'est la dernière page
                if len(results) < 20000:
                    return all_data

                page += 1
                break

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Erreur après {max_retries} tentatives pour {date_str}: {e}")
                    return all_data
                else:
                    print(f"Tentative {attempt + 1} échouée, retry...")

    return all_data

# COMMAND ----------

def ingest_date_range(start_date, end_date):
    """
    Ingère les données pour une plage de dates
    """
    current_date = start_date
    total_records = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")

        print(f"Ingestion {date_str}...", end=" ")

        # Récupérer les données du jour
        day_data = fetch_day_data(date_str)

        if day_data:
            # Convertir en DataFrame Pandas puis Spark
            df_pandas = pd.DataFrame(day_data)
            df_spark = spark.createDataFrame(df_pandas)

            # Ajouter métadonnées
            df_spark = df_spark.withColumn("ingestion_timestamp", lit(datetime.now()))
            df_spark = df_spark.withColumn("source", lit("hubeau_api"))
            df_spark = df_spark.withColumn("year", lit(current_date.year))

            # Écrire en mode append dans Delta Lake
            df_spark.write \
                .format("delta") \
                .mode("append") \
                .partitionBy("year") \
                .save(BRONZE_PATH)

            total_records += len(day_data)
            print(f"{len(day_data)} résultats")
        else:
            print("0 résultats")

        current_date += timedelta(days=1)

    return total_records

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exécution du pipeline

# COMMAND ----------

# Déterminer la plage de dates à ingérer
last_date = get_last_ingested_date(BRONZE_PATH)
today = datetime.now()

print(f"\nIngestion de {last_date.strftime('%Y-%m-%d')} à {today.strftime('%Y-%m-%d')}")
print(f"Nombre de jours: {(today - last_date).days + 1}")

# COMMAND ----------

# Lancer l'ingestion
print("\nDémarrage ingestion...\n")

total_records = ingest_date_range(last_date, today)

print(f"\nIngestion terminée: {total_records} enregistrements")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

# Lire la table Bronze
df_bronze = spark.read.format("delta").load(BRONZE_PATH)

print(f"Total enregistrements Bronze: {df_bronze.count()}")
print(f"Période: {df_bronze.selectExpr('min(date_prelevement)', 'max(date_prelevement)').collect()[0]}")
print(f"\nSchéma:")
df_bronze.printSchema()

# COMMAND ----------

# Statistiques par année
df_bronze.groupBy("year").count().orderBy("year").show()

# COMMAND ----------

# Aperçu des données
df_bronze.select("date_prelevement", "nom_commune", "libelle_parametre", "resultat_numerique", "unite_mesure") \
    .orderBy(col("date_prelevement").desc()) \
    .show(10, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optimisation Delta Lake

# COMMAND ----------

# Optimiser la table Bronze
spark.sql(f"OPTIMIZE delta.`{BRONZE_PATH}` ZORDER BY (date_prelevement)")

print("Table Bronze optimisée")