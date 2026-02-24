#!/usr/bin/env python3
"""
Create Databricks Workflow: Pipeline_Qualite_Eau_Complet

Orchestrates the 4 water quality notebooks in sequence.
Requires environment variables (set via `invoke env-save` or .env):
  - DATABRICKS_WORKSPACE_URL
  - DATABRICKS_TOKEN        (personal access token — create in Databricks > User Settings > Access Tokens)
  - DATABRICKS_NOTEBOOKS_PATH (optional, default: /Repos/main/WTR_QLT/notebooks)

Usage:
    python scripts/create_workflow.py
    python scripts/create_workflow.py --dry-run
"""

import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_URL = os.environ.get("DATABRICKS_WORKSPACE_URL", "").rstrip("/")
TOKEN = os.environ.get("DATABRICKS_TOKEN", "")
NOTEBOOKS_PATH = os.environ.get(
    "DATABRICKS_NOTEBOOKS_PATH", "/Repos/main/WTR_QLT/notebooks"
)
STORAGE_ACCOUNT = os.environ.get("DATALAKE_NAME", "wtrqltadls")
ACCESS_KEY = os.environ.get("DATALAKE_ACCESS_KEY", "")

JOB_NAME = "Pipeline_Qualite_Eau_Complet"


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }


def check_env() -> None:
    missing = [k for k in ("DATABRICKS_WORKSPACE_URL", "DATABRICKS_TOKEN") if not os.environ.get(k)]
    if missing:
        print(f"[ERROR] Missing env variables: {', '.join(missing)}")
        print("  - Set DATABRICKS_TOKEN in your .env (Databricks > User Settings > Access Tokens)")
        sys.exit(1)


def delete_existing_job(job_name: str) -> None:
    """Delete existing job with the same name if it exists."""
    resp = requests.get(
        f"{WORKSPACE_URL}/api/2.1/jobs/list",
        headers=get_headers(),
        params={"name": job_name},
    )
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    for job in jobs:
        job_id = job["job_id"]
        print(f"  Deleting existing job '{job_name}' (id={job_id})...")
        requests.post(
            f"{WORKSPACE_URL}/api/2.1/jobs/delete",
            headers=get_headers(),
            json={"job_id": job_id},
        ).raise_for_status()


def build_job_config() -> dict:
    spark_conf = {}
    if ACCESS_KEY:
        spark_conf[f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net"] = ACCESS_KEY

    cluster_def = {
        "spark_version": "15.4.x-scala2.12",
        "node_type_id": "Standard_DS3_v2",
        "num_workers": 1,
        "autotermination_minutes": 30,
        "spark_conf": spark_conf,
    }

    def notebook_task(notebook: str) -> dict:
        return {
            "notebook_path": f"{NOTEBOOKS_PATH}/{notebook}",
            "source": "WORKSPACE",
        }

    return {
        "name": JOB_NAME,
        "job_clusters": [
            {"job_cluster_key": "wtr_qlt_cluster", "new_cluster": cluster_def}
        ],
        "tasks": [
            {
                "task_key": "01_ingestion_bronze",
                "description": "Ingestion Bronze — Hub'Eau API",
                "job_cluster_key": "wtr_qlt_cluster",
                "notebook_task": notebook_task("01_DLT_Ingestion_Qualite_Eau"),
            },
            {
                "task_key": "02_silver_transformation",
                "description": "Silver — Nettoyage et standardisation",
                "depends_on": [{"task_key": "01_ingestion_bronze"}],
                "job_cluster_key": "wtr_qlt_cluster",
                "notebook_task": notebook_task("02_Silver_Transformation"),
            },
            {
                "task_key": "03_gold_agregations",
                "description": "Gold — Star schema et KPIs",
                "depends_on": [{"task_key": "02_silver_transformation"}],
                "job_cluster_key": "wtr_qlt_cluster",
                "notebook_task": notebook_task("03_Gold_Agregations"),
            },
            {
                "task_key": "04_quality_checks",
                "description": "Quality Checks — Validation Spark natif",
                "depends_on": [{"task_key": "03_gold_agregations"}],
                "job_cluster_key": "wtr_qlt_cluster",
                "notebook_task": notebook_task("04_Quality_Checks"),
            },
        ],
        "schedule": {
            "quartz_cron_expression": "0 0 2 * * ?",
            "timezone_id": "Europe/Paris",
            "pause_status": "PAUSED",  # Enable manually when ready
        },
        "max_concurrent_runs": 1,
        "tags": {"project": "water-quality-france"},
        "email_notifications": {"no_alert_for_skipped_runs": True},
    }


def create_workflow(dry_run: bool = False) -> None:
    check_env()
    config = build_job_config()

    if dry_run:
        print("[DRY RUN] Job config:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return

    print(f"Connecting to: {WORKSPACE_URL}")
    delete_existing_job(JOB_NAME)

    resp = requests.post(
        f"{WORKSPACE_URL}/api/2.1/jobs/create",
        headers=get_headers(),
        json=config,
    )
    resp.raise_for_status()
    job_id = resp.json()["job_id"]

    print(f"[OK] Workflow '{JOB_NAME}' created (job_id={job_id})")
    print(f"     {WORKSPACE_URL}/#job/{job_id}")
    print()
    print("Note: schedule is PAUSED by default.")
    print("      Enable it in Databricks > Workflows > your job > Schedule.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Databricks workflow for water quality pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Print config without creating the job")
    args = parser.parse_args()
    create_workflow(dry_run=args.dry_run)
