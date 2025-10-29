# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - Hub'eau Water Quality API Ingestion
# MAGIC
# MAGIC Automated ingestion pipeline from Hub'eau API to Bronze Delta Lake layer.
# MAGIC
# MAGIC **Source**: https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable
# MAGIC
# MAGIC **Architecture**:
# MAGIC - Detects last ingested date (or starts from 2021-01-01)
# MAGIC - Day-by-day loop until today
# MAGIC - Writes to Delta Lake format, partitioned by year
# MAGIC - Automatic pagination handling (20K records per page)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📦 Install Dependencies

# COMMAND ----------

# MAGIC %pip install rich requests --quiet

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔧 Configuration & Imports

# COMMAND ----------

import requests
import pandas as pd
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, to_date
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
import json

console = Console()

# API Configuration
BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"

# Azure Data Lake Configuration
STORAGE_ACCOUNT = dbutils.secrets.get(scope="azure-credentials", key="storage-account-name")
BRONZE_PATH = f"abfss://bronze@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality/hubeau"

# Date range
START_DATE = datetime(2021, 1, 1)

# Spark configuration for Azure authentication
ACCESS_KEY = dbutils.secrets.get(scope="azure-credentials", key="datalake-access-key")
spark.conf.set(
    f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net",
    ACCESS_KEY
)

console.print(Panel.fit(
    f"[bold cyan]Configuration Loaded[/bold cyan]\n"
    f"Storage: [yellow]{STORAGE_ACCOUNT}[/yellow]\n"
    f"Bronze Path: [green]{BRONZE_PATH}[/green]",
    border_style="cyan"
))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔍 Helper Functions

# COMMAND ----------

def get_last_ingested_date(bronze_path):
    """
    Retrieve the last ingested date from Bronze layer.
    Returns START_DATE if no data exists.

    Args:
        bronze_path (str): Path to Bronze Delta table

    Returns:
        datetime: Last ingested date + 1 day, or START_DATE
    """
    try:
        df = spark.read.format("delta").load(bronze_path)
        max_date = df.selectExpr("max(to_date(date_prelevement))").collect()[0][0]

        if max_date:
            last_date = datetime.strptime(str(max_date), "%Y-%m-%d")
            console.print(f"✓ Last ingested date: [bold green]{last_date.strftime('%Y-%m-%d')}[/bold green]")
            return last_date + timedelta(days=1)
        else:
            console.print(f"ℹ No data found, starting from [bold yellow]{START_DATE.strftime('%Y-%m-%d')}[/bold yellow]")
            return START_DATE

    except Exception as e:
        console.print(f"ℹ Bronze table not found, starting from [bold yellow]{START_DATE.strftime('%Y-%m-%d')}[/bold yellow]")
        return START_DATE

# COMMAND ----------

def fetch_day_data(date_str, max_retries=3):
    """
    Fetch all data for a single day from Hub'eau API.
    Handles automatic pagination up to API limits.

    Args:
        date_str (str): Date in format YYYY-MM-DD
        max_retries (int): Maximum retry attempts on failure

    Returns:
        list: All records for the specified date
    """
    all_data = []
    page = 1

    while True:
        params = {
            "date_min_prelevement": date_str,
            "date_max_prelevement": date_str,
            "size": 20000,  # API maximum
            "page": page
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{BASE_URL}/resultats_dis",
                    params=params,
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()

                results = data.get('data', [])

                if not results:
                    return all_data

                all_data.extend(results)

                # If less than 20K results, it's the last page
                if len(results) < 20000:
                    return all_data

                page += 1
                break

            except Exception as e:
                if attempt == max_retries - 1:
                    console.print(f"[bold red]✗[/bold red] Failed after {max_retries} attempts for {date_str}: {e}")
                    return all_data
                else:
                    console.print(f"[yellow]⚠[/yellow] Retry {attempt + 1}/{max_retries} for {date_str}")

    return all_data

# COMMAND ----------

def ingest_date_range(start_date, end_date):
    """
    Ingest data for a date range from Hub'eau API to Bronze Delta Lake.

    Args:
        start_date (datetime): Start date
        end_date (datetime): End date

    Returns:
        int: Total number of records ingested
    """
    current_date = start_date
    total_records = 0
    total_days = (end_date - start_date).days + 1

    # Create summary table
    summary_table = Table(
        title="🌊 Ingestion Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    summary_table.add_column("Date", style="cyan", width=12)
    summary_table.add_column("Records", justify="right", style="green")
    summary_table.add_column("Status", justify="center")

    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        task = progress.add_task(
            f"[cyan]Ingesting from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            total=total_days
        )

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")

            # Fetch data for the day
            day_data = fetch_day_data(date_str)

            if day_data:
                # Convert to Spark DataFrame
                df_pandas = pd.DataFrame(day_data)
                df_spark = spark.createDataFrame(df_pandas)

                # Add metadata columns
                df_spark = df_spark.withColumn("ingestion_timestamp", lit(datetime.now()))
                df_spark = df_spark.withColumn("source", lit("hubeau_api"))
                df_spark = df_spark.withColumn("year", lit(current_date.year))

                # Write to Delta Lake (append mode)
                df_spark.write \
                    .format("delta") \
                    .mode("append") \
                    .partitionBy("year") \
                    .save(BRONZE_PATH)

                total_records += len(day_data)
                summary_table.add_row(date_str, str(len(day_data)), "✓")
            else:
                summary_table.add_row(date_str, "0", "○")

            progress.update(task, advance=1)
            current_date += timedelta(days=1)

    console.print("\n")
    console.print(summary_table)

    return total_records

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🚀 Execute Pipeline

# COMMAND ----------

# Determine date range to ingest
last_date = get_last_ingested_date(BRONZE_PATH)
today = datetime.now()

console.print(Panel.fit(
    f"[bold]Ingestion Range[/bold]\n"
    f"From: [cyan]{last_date.strftime('%Y-%m-%d')}[/cyan]\n"
    f"To: [cyan]{today.strftime('%Y-%m-%d')}[/cyan]\n"
    f"Days: [yellow]{(today - last_date).days + 1}[/yellow]",
    border_style="blue"
))

# COMMAND ----------

# Start ingestion
console.print("\n[bold cyan]🌊 Starting Bronze Ingestion...[/bold cyan]\n")

total_records = ingest_date_range(last_date, today)

console.print(Panel.fit(
    f"[bold green]✓ Ingestion Complete![/bold green]\n"
    f"Total Records: [yellow]{total_records:,}[/yellow]",
    border_style="green"
))

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Validation & Statistics

# COMMAND ----------

# Read Bronze table
df_bronze = spark.read.format("delta").load(BRONZE_PATH)

# Count statistics
total_count = df_bronze.count()
date_range = df_bronze.selectExpr(
    "min(date_prelevement) as min_date",
    "max(date_prelevement) as max_date"
).collect()[0]

# Create stats table
stats_table = Table(
    title="📊 Bronze Layer Statistics",
    box=box.DOUBLE_EDGE,
    show_header=True,
    header_style="bold magenta"
)
stats_table.add_column("Metric", style="cyan")
stats_table.add_column("Value", style="green", justify="right")

stats_table.add_row("Total Records", f"{total_count:,}")
stats_table.add_row("Date Range", f"{date_range['min_date']} → {date_range['max_date']}")
stats_table.add_row("Storage Path", BRONZE_PATH)

console.print("\n")
console.print(stats_table)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📈 Data Preview

# COMMAND ----------

# Display schema
console.print("\n[bold cyan]Schema:[/bold cyan]")
df_bronze.printSchema()

# COMMAND ----------

# Records by year
console.print("\n[bold cyan]Records by Year:[/bold cyan]")
year_stats = df_bronze.groupBy("year").count().orderBy("year")

year_table = Table(box=box.SIMPLE)
year_table.add_column("Year", style="cyan", justify="center")
year_table.add_column("Records", style="green", justify="right")

for row in year_stats.collect():
    year_table.add_row(str(row['year']), f"{row['count']:,}")

console.print(year_table)

# COMMAND ----------

# Preview recent data
console.print("\n[bold cyan]Recent Data Sample:[/bold cyan]")
display(
    df_bronze.select(
        "date_prelevement",
        "nom_commune",
        "libelle_parametre",
        "resultat_numerique",
        "unite_mesure",
        "conclusion_conformite_prelevement"
    )
    .orderBy(col("date_prelevement").desc())
    .limit(10)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⚡ Delta Lake Optimization

# COMMAND ----------

# Optimize Delta table for better query performance
console.print("\n[bold cyan]🔧 Optimizing Delta Lake table...[/bold cyan]")

spark.sql(f"OPTIMIZE delta.`{BRONZE_PATH}` ZORDER BY (date_prelevement)")

console.print("[bold green]✓ Optimization complete![/bold green]")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎉 Pipeline Complete
# MAGIC
# MAGIC Bronze layer ingestion finished successfully!
# MAGIC
# MAGIC **Next steps**:
# MAGIC 1. Run `02_Silver_Transformation.py` for data cleaning
# MAGIC 2. Check data quality in Bronze layer
# MAGIC 3. Monitor ingestion logs for errors
