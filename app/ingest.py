"""
Ingest Hub'Eau water quality data for all France — full year 2024.
Supporting Drill-down: National (Dept) -> Local (Commune)
"""

import calendar
import json
import logging
import re
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

# Paramètres cibles pour le graphique de niveaux réels
# type: "pct"  → valeur / limite * 100  (physico-chimiques)
# type: "count"→ nombre de détections >0 dans le mois (bactériologiques)
PARAMETRES_CIBLES = {
    "1340": {"nom": "Nitrates",          "unite": "mg/L",     "limite": 50.0,  "type": "pct"},
    "1339": {"nom": "Nitrites",          "unite": "mg/L",     "limite": 0.1,   "type": "pct"},
    "2036": {"nom": "Trihalométhanes",   "unite": "µg/L",     "limite": 100.0, "type": "pct"},
    "1295": {"nom": "Turbidité",         "unite": "NFU",      "limite": 1.0,   "type": "pct"},
    "7073": {"nom": "Fluorures",         "unite": "mg/L",     "limite": 1.5,   "type": "pct"},
    "1449": {"nom": "E. coli",           "unite": "n/100mL",  "limite": 0,     "type": "count"},
    "6455": {"nom": "Entérocoques",      "unite": "n/100mL",  "limite": 0,     "type": "count"},
}

FIELDS_PARAMETRES = (
    "code_prelevement,code_commune,code_departement,"
    "code_parametre,libelle_parametre,resultat_numerique,"
    "libelle_unite,limite_qualite_parametre,date_prelevement"
)

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

def parse_limite(limite_str: str | None) -> float | None:
    """Extrait la valeur numérique de '<=50 mg/L' → 50.0"""
    if not limite_str:
        return None
    m = re.search(r"(\d+[,.]?\d*)", limite_str.replace(",", "."))
    return float(m.group(1)) if m else None


def fetch_parametres_2024():
    """Fetch les valeurs mesurées pour les paramètres cibles, toute la France 2024."""
    depts = get_all_departments()
    codes = ",".join(PARAMETRES_CIBLES.keys())
    all_records = []

    for month in range(1, 13):
        last_day = calendar.monthrange(YEAR, month)[1]
        logger.info(f"── Paramètres mois {month:02d}/{YEAR}")
        for dept in depts:
            records = fetch_paginated({
                "code_departement": dept,
                "date_min_prelevement": f"{YEAR}-{month:02d}-01",
                "date_max_prelevement": f"{YEAR}-{month:02d}-{last_day}",
                "code_parametre": codes,
                "fields": FIELDS_PARAMETRES,
            }, max_pages=2)
            for r in records:
                r["mois"] = month
            all_records.extend(records)

    df = pd.DataFrame(all_records)
    if df.empty:
        return df

    # Garde uniquement les enregistrements avec une valeur numérique
    df = df[df["resultat_numerique"].notna()].copy()
    df["code_parametre"] = df["code_parametre"].astype(str)

    # Enrichit avec les métadonnées cibles
    df["param_type"]  = df["code_parametre"].map(lambda c: PARAMETRES_CIBLES.get(c, {}).get("type"))
    df["param_limite"] = df["code_parametre"].map(lambda c: PARAMETRES_CIBLES.get(c, {}).get("limite"))
    df["param_nom"]   = df["code_parametre"].map(lambda c: PARAMETRES_CIBLES.get(c, {}).get("nom"))

    return df


def compute_parametres_aggregations(df: pd.DataFrame):
    """
    Agrège les valeurs mesurées par dept/commune × mois × paramètre.

    - type 'pct'   → médiane de (valeur / limite * 100)
    - type 'count' → nombre de détections > 0 dans le mois
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    rows_dept    = []
    rows_commune = []

    for (dept, commune, mois, code), grp in df.groupby(
        ["code_departement", "code_commune", "mois", "code_parametre"]
    ):
        meta = PARAMETRES_CIBLES.get(code, {})
        nom   = meta.get("nom", code)
        unite = meta.get("unite", "")
        ptype = meta.get("type")
        limite = meta.get("limite")

        if ptype == "pct" and limite and limite > 0:
            valeur_mediane = grp["resultat_numerique"].median()
            pct_limite     = round(valeur_mediane / limite * 100, 2)
        elif ptype == "count":
            valeur_mediane = grp["resultat_numerique"].sum()   # total détections
            pct_limite     = None
        else:
            continue

        row = {
            "code_departement": dept,
            "code_commune":     commune,
            "mois":             mois,
            "code_parametre":   code,
            "nom_parametre":    nom,
            "unite":            unite,
            "type":             ptype,
            "valeur_mediane":   round(valeur_mediane, 4),
            "limite":           limite,
            "pct_limite":       pct_limite,
        }
        rows_commune.append(row)

    df_commune = pd.DataFrame(rows_commune)

    if not df_commune.empty:
        # Agrégation département : médiane des médianes communes
        df_dept = df_commune.groupby(
            ["code_departement", "mois", "code_parametre", "nom_parametre", "unite", "type", "limite"]
        ).agg(
            valeur_mediane=("valeur_mediane", "median"),
            pct_limite=("pct_limite",         "median"),
        ).reset_index()
        df_dept["valeur_mediane"] = df_dept["valeur_mediane"].round(4)
        df_dept["pct_limite"]     = df_dept["pct_limite"].round(2)
    else:
        df_dept = pd.DataFrame()

    return df_dept, df_commune


def fetch_geo_data():
    # Depts — geo.api.gouv.fr retourne une liste, pas un FeatureCollection.
    # On utilise gregoiredavid/france-geojson pour avoir le bon format GeoJSON.
    logger.info("Fetching Dept GeoJSON with contours...")
    _GEOJSON_BASE = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master"
    resp = requests.get(f"{_GEOJSON_BASE}/departements.geojson", timeout=30)
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

    # ── Conformité (pipeline existant) ──────────────────────────────────
    df_raw = fetch_france_2024()
    if df_raw.empty:
        logger.error("Aucune donnée conformité récupérée.")
        return

    df_raw.to_parquet(DATA_DIR / "prelevements_france_2024.parquet", index=False)

    agg_commune, agg_dept = compute_aggregations(df_raw)
    agg_commune.to_parquet(DATA_DIR / "agg_commune_mois.parquet", index=False)
    agg_dept.to_parquet(DATA_DIR / "agg_dept_mois.parquet", index=False)
    logger.info("Conformité : OK")

    # ── Paramètres (nitrates, bactéries, etc.) ──────────────────────────
    logger.info("=== Ingestion paramètres mesurés ===")
    df_params = fetch_parametres_2024()
    if not df_params.empty:
        df_params.to_parquet(DATA_DIR / "parametres_brut_2024.parquet", index=False)
        params_dept, params_commune = compute_parametres_aggregations(df_params)
        if not params_dept.empty:
            params_dept.to_parquet(DATA_DIR / "parametres_dept_mois.parquet", index=False)
        if not params_commune.empty:
            params_commune.to_parquet(DATA_DIR / "parametres_commune_mois.parquet", index=False)
        logger.info(f"Paramètres : {len(df_params)} mesures → {len(params_dept)} agg dept, {len(params_commune)} agg commune")
    else:
        logger.warning("Aucune donnée paramètres récupérée.")

    fetch_geo_data()
    logger.info("=== Ingestion Nationale terminée ===")

if __name__ == "__main__":
    main()
