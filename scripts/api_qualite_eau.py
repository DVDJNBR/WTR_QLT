#!/usr/bin/env python3
"""
API REST — Qualité de l'eau potable en France

Expose les tables Gold du pipeline via FastAPI.
Lit directement les tables Delta depuis Azure Data Lake (aucun compute Databricks requis).

Prérequis (.env):
  DATALAKE_NAME       = nom du storage account (ex: wtrqltadls)
  DATALAKE_ACCESS_KEY = clé d'accès du storage account

Usage:
    uv run python scripts/api_qualite_eau.py
    # ou
    uvicorn scripts.api_qualite_eau:app --reload --port 8000
"""

import os

import pandas as pd
import uvicorn
from deltalake import DeltaTable
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

STORAGE_ACCOUNT = os.environ.get("DATALAKE_NAME", "wtrqltadls")
ACCESS_KEY = os.environ.get("DATALAKE_ACCESS_KEY", "")

GOLD_BASE = f"abfss://gold@{STORAGE_ACCOUNT}.dfs.core.windows.net/water_quality"

STORAGE_OPTIONS = {
    "account_name": STORAGE_ACCOUNT,
    "account_key": ACCESS_KEY,
}

app = FastAPI(
    title="Water Quality API — France",
    description="Données de qualité de l'eau potable issues du pipeline Hub'Eau (Bronze → Silver → Gold).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def read_delta(table_name: str) -> pd.DataFrame:
    """Read a Gold Delta table into a Pandas DataFrame."""
    try:
        dt = DeltaTable(f"{GOLD_BASE}/{table_name}", storage_options=STORAGE_OPTIONS)
        return dt.to_pandas()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot read table '{table_name}': {e}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def health():
    """Health check."""
    return {"status": "ok", "storage_account": STORAGE_ACCOUNT}


@app.get("/conformite/departements", tags=["Conformité"])
def conformite_departements():
    """
    Taux de conformité global par département.
    Source: agg_conformite_departement
    """
    df = read_delta("agg_conformite_departement")
    return df.sort_values("compliance_rate", ascending=False).to_dict(orient="records")


@app.get("/conformite/departements/{department_code}", tags=["Conformité"])
def conformite_departement(department_code: str):
    """
    Taux de conformité pour un département spécifique.
    Ex: /conformite/departements/75
    """
    df = read_delta("agg_conformite_departement")
    row = df[df["department_code"] == department_code]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Department '{department_code}' not found")
    return row.iloc[0].to_dict()


@app.get("/departements/top", tags=["Conformité"])
def top_departements(limit: int = 10, order: str = "best"):
    """
    Top départements par taux de conformité.
    - order=best  : les plus conformes (défaut)
    - order=worst : les moins conformes
    """
    df = read_delta("agg_conformite_departement")
    ascending = order == "worst"
    return (
        df.sort_values("compliance_rate", ascending=ascending)
        .head(limit)
        .to_dict(orient="records")
    )


@app.get("/communes", tags=["Géographie"])
def communes(department_code: str | None = None):
    """
    Liste des communes. Filtrable par département.
    Ex: /communes?department_code=69
    """
    df = read_delta("dim_communes")
    if department_code:
        df = df[df["department_code"] == department_code]
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No communes found for department '{department_code}'")
    return df.sort_values("commune_name").to_dict(orient="records")


@app.get("/parametres", tags=["Paramètres"])
def parametres():
    """
    Liste des paramètres analysés (nitrates, pH, bactéries...).
    Source: dim_parametres
    """
    df = read_delta("dim_parametres")
    return df.sort_values("parameter_name").to_dict(orient="records")


@app.get("/mesures/stats", tags=["Mesures"])
def mesures_stats():
    """
    Statistiques globales sur les mesures (count, nulls, plages).
    """
    df = read_delta("factmesuresqualite")
    total = len(df)
    non_null = df["numeric_result"].notna().sum()
    nan_count = df["numeric_result"].isna().sum()
    return {
        "total_mesures": int(total),
        "avec_valeur_numerique": int(non_null),
        "sans_valeur_numerique": int(nan_count),
        "min_result": float(df["numeric_result"].min()) if non_null > 0 else None,
        "max_result": float(df["numeric_result"].max()) if non_null > 0 else None,
        "communes_distinctes": int(df["commune_code"].nunique()),
        "parametres_distincts": int(df["parameter_code"].nunique()),
    }


@app.get("/conformite/stats", tags=["Conformité"])
def conformite_stats():
    """
    Statistiques globales de conformité (taux PC et bactériologique).
    """
    df = read_delta("factconformite")
    total = len(df)
    compliant_pc = df["is_compliant_pc"].sum()
    compliant_bact = df["is_compliant_bact"].sum()
    both_compliant = (df["is_compliant_pc"] & df["is_compliant_bact"]).sum()
    return {
        "total_prelevements": int(total),
        "conformes_pc": int(compliant_pc),
        "taux_conformite_pc_pct": round(compliant_pc / total * 100, 2) if total > 0 else 0,
        "conformes_bact": int(compliant_bact),
        "taux_conformite_bact_pct": round(compliant_bact / total * 100, 2) if total > 0 else 0,
        "conformes_global": int(both_compliant),
        "taux_conformite_global_pct": round(both_compliant / total * 100, 2) if total > 0 else 0,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
