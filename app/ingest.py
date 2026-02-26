"""
Ingest Hub'Eau water quality data for Île-de-France — full year 2025, month by month.

Outputs:
  app/data/prelevements_2025.parquet  — raw deduped prélèvements avec date + mois
  app/data/agg_commune_mois.parquet   — taux de conformité par (commune × mois)
  app/data/communes.geojson           — polygones communes (sans conformité)
"""

import calendar
import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HUBEAU_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/resultats_dis"
GEO_URL = "https://geo.api.gouv.fr/communes"

IDF_DEPARTMENTS = ["75", "77", "78", "91", "92", "93", "94", "95"]
YEAR = 2024
PAGES_PER_MONTH_DEPT = 3
   # 3 × 5000 = 15K rows → ~150-300 uniques/mois/dept
PAGE_SIZE = 5000
MAX_RETRIES = 5
RETRY_DELAY = 3


def fetch_paginated(params: dict) -> list[dict]:
    records = []
    for page in range(1, PAGES_PER_MONTH_DEPT + 1):
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(
                    HUBEAU_URL,
                    params={**params, "page": page, "size": PAGE_SIZE},
                    timeout=60,
                )
                resp.raise_for_status()
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (attempt + 1)
                    logger.warning(f"  réseau instable, retry {attempt + 1}/{MAX_RETRIES} dans {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"  échec après {MAX_RETRIES} tentatives : {e}")
                    return records
        data = resp.json().get("data", [])
        if not data:
            break
        records.extend(data)
        if len(data) < PAGE_SIZE:
            break
    return records


def fetch_all_months() -> pd.DataFrame:
    all_records = []
    for month in range(1, 13):
        last_day = calendar.monthrange(YEAR, month)[1]
        date_debut = f"{YEAR}-{month:02d}-01"
        date_fin = f"{YEAR}-{month:02d}-{last_day}"

        logger.info(f"── Mois {month:02d}/{YEAR} ({date_debut} → {date_fin})")
        month_records = []

        for dept in IDF_DEPARTMENTS:
            records = fetch_paginated({
                "code_departement": dept,
                "date_min_prelevement": date_debut,
                "date_max_prelevement": date_fin,
                "fields": "code_prelevement,code_commune,code_departement,date_prelevement,conformite_limites_pc_prelevement,conformite_limites_bact_prelevement",
            })
            for r in records:
                r["mois"] = month
            month_records.extend(records)

        df_month = pd.DataFrame(month_records)
        if not df_month.empty:
            df_month = df_month.drop_duplicates(subset=["code_prelevement"])
            logger.info(f"   {len(df_month):,} prélèvements uniques")
            all_records.append(df_month)
        else:
            logger.warning(f"   aucune donnée pour le mois {month}")

        time.sleep(0.5)

    return pd.concat(all_records, ignore_index=True) if all_records else pd.DataFrame()


def compute_monthly_agg(df: pd.DataFrame) -> pd.DataFrame:
    df["is_compliant"] = (
        (df["conformite_limites_pc_prelevement"] == "C")
        & (df["conformite_limites_bact_prelevement"] == "C")
    )
    agg = (
        df.groupby(["code_commune", "code_departement", "mois"])
        .agg(total_tests=("is_compliant", "count"), compliant_tests=("is_compliant", "sum"))
        .reset_index()
    )
    agg["compliance_rate"] = (agg["compliant_tests"] / agg["total_tests"] * 100).round(2)
    return agg


def fetch_geojson() -> dict:
    features = []
    for dept in IDF_DEPARTMENTS:
        logger.info(f"GeoJSON contours — dept {dept}...")
        resp = requests.get(
            GEO_URL,
            params={"codeDepartement": dept, "format": "geojson", "geometry": "contour"},
            timeout=60,
        )
        resp.raise_for_status()
        for feat in resp.json().get("features", []):
            feat["properties"] = {
                "code_commune": feat["properties"].get("code", ""),
                "nom_commune": feat["properties"].get("nom", ""),
                "code_departement": dept,
            }
            features.append(feat)
    return {"type": "FeatureCollection", "features": features}


def main():
    logger.info("=== Ingestion Hub'Eau IDF 2024 — mois par mois ===")

    df_raw = fetch_all_months()
    if df_raw.empty:
        logger.error("Aucune donnée récupérée.")
        return

    logger.info(f"Total prélèvements: {len(df_raw):,}")

    raw_out = DATA_DIR / "prelevements_2024.parquet"
    df_raw.to_parquet(raw_out, index=False)
    logger.info(f"Saved → {raw_out}")

    df_agg = compute_monthly_agg(df_raw)
    agg_out = DATA_DIR / "agg_commune_mois.parquet"
    df_agg.to_parquet(agg_out, index=False)
    logger.info(f"Saved → {agg_out} ({len(df_agg):,} lignes)")

    geojson = fetch_geojson()
    geojson_out = DATA_DIR / "communes.geojson"
    with open(geojson_out, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    logger.info(f"Saved → {geojson_out} ({len(geojson['features'])} communes)")

    logger.info("=== Ingestion terminée ===")


if __name__ == "__main__":
    main()
