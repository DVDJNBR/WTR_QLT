"""
Ingest Hub'Eau water quality data for all France — full year 2024.
Supporting Drill-down: National (Dept) -> Local (Commune)
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
GEO_API = "https://geo.api.gouv.fr"

YEAR = 2024
PAGE_SIZE = 5000
MAX_RETRIES = 5
RETRY_DELAY = 2

def get_all_departments():
    resp = requests.get(f"{GEO_API}/departements")
    resp.raise_for_status()
    return [d["code"] for d in resp.json()]

def fetch_paginated(params: dict, max_pages=2) -> list[dict]:
    records = []
    for page in range(1, max_pages + 1):
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(HUBEAU_URL, params={**params, "page": page, "size": PAGE_SIZE}, timeout=60)
                resp.raise_for_status()
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else: return records
        data = resp.json().get("data", [])
        if not data: break
        records.extend(data)
        if len(data) < PAGE_SIZE: break
    return records

def fetch_france_2024():
    depts = get_all_departments()
    all_records = []
    
    # Pour ne pas que ça dure 4 heures, on limite à 1 page par mois par département 
    # pour le prototype national (déjà ~600 000 lignes)
    for month in range(1, 13):
        last_day = calendar.monthrange(YEAR, month)[1]
        date_debut = f"{YEAR}-{month:02d}-01"
        date_fin = f"{YEAR}-{month:02d}-{last_day}"
        logger.info(f"── Mois {month:02d}/{YEAR}")
        
        for dept in depts:
            records = fetch_paginated({
                "code_departement": dept,
                "date_min_prelevement": date_debut,
                "date_max_prelevement": date_fin,
                "fields": "code_prelevement,code_commune,code_departement,conformite_limites_pc_prelevement,conformite_limites_bact_prelevement",
            }, max_pages=1)
            for r in records: r["mois"] = month
            all_records.extend(records)
            
    return pd.DataFrame(all_records)

def compute_aggregations(df: pd.DataFrame):
    df["is_compliant"] = (df["conformite_limites_pc_prelevement"] == "C") & (df["conformite_limites_bact_prelevement"] == "C")
    
    # Agg commune
    agg_commune = df.groupby(["code_commune", "code_departement", "mois"]).agg(
        total_tests=("is_compliant", "count"),
        compliant_tests=("is_compliant", "sum")
    ).reset_index()
    agg_commune["compliance_rate"] = (agg_commune["compliant_tests"] / agg_commune["total_tests"] * 100).round(2)
    
    # Agg département (pour la carte nationale)
    agg_dept = df.groupby(["code_departement", "mois"]).agg(
        total_tests=("is_compliant", "count"),
        compliant_tests=("is_compliant", "sum")
    ).reset_index()
    agg_dept["compliance_rate"] = (agg_dept["compliant_tests"] / agg_dept["total_tests"] * 100).round(2)
    
    return agg_commune, agg_dept

def fetch_geo_data():
    # Depts
    logger.info("Fetching Dept GeoJSON with contours...")
    # L'API geo.api.gouv.fr/departements?format=geojson renvoie un FeatureCollection
    resp = requests.get(f"{GEO_API}/departements?format=geojson&geometry=contour")
    resp.raise_for_status()
    with open(DATA_DIR / "departements.geojson", "w") as f:
        json.dump(resp.json(), f)
        
    # Communes (On garde l'IDF complet + un échantillon national pour le prototype)
    # Dans une version prod, on chargerait le GeoJSON du département sélectionné à la volée.
    logger.info("Fetching Commune GeoJSON (simplified)...")
    # Pour le moment on garde notre fichier communes.geojson existant ou on en télécharge un léger
    # On va se concentrer sur l'agrégation des données d'abord.

def main():
    logger.info("=== Ingestion NATIONALE Hub'Eau 2024 ===")
    df_raw = fetch_france_2024()
    if df_raw.empty: return
    
    df_raw.to_parquet(DATA_DIR / "prelevements_france_2024.parquet", index=False)
    
    agg_commune, agg_dept = compute_aggregations(df_raw)
    agg_commune.to_parquet(DATA_DIR / "agg_commune_mois.parquet", index=False)
    agg_dept.to_parquet(DATA_DIR / "agg_dept_mois.parquet", index=False)
    
    fetch_geo_data()
    logger.info("=== Ingestion Nationale terminée ===")

if __name__ == "__main__":
    main()
