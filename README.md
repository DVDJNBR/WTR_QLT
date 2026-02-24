# Water Quality Pipeline — France

Pipeline de données Azure pour l'analyse de la qualité de l'eau potable en France, basé sur l'API Hub'Eau (data.gouv.fr).

## Architecture

Architecture Medallion sur Azure Data Lake Storage Gen2 + Databricks :

```
Hub'Eau API
    │
    ▼
Bronze (raw Delta)          ← 01_DLT_Ingestion_Qualite_Eau.py
    │
    ▼
Silver (cleaned Delta)      ← 02_Silver_Transformation.py
    │
    ▼
Gold (star schema + KPIs)   ← 03_Gold_Agregations.py
    │
    ▼
Quality Checks              ← 04_Quality_Checks.py
```

### Tables produites

| Couche | Table | Description |
|--------|-------|-------------|
| Bronze | `bronze_communes` | Communes et réseaux de distribution |
| Bronze | `bronze_analyses` | Analyses brutes de qualité |
| Silver | `silver_communes` | Communes standardisées |
| Silver | `silver_mesures` | Mesures nettoyées, partitionné par année/département |
| Silver | `silver_conformite` | Conformité par prélèvement, partitionné par année/département |
| Gold | `dim_communes` | Dimension géographique |
| Gold | `dim_parametres` | Dimension paramètres analysés |
| Gold | `dim_temps` | Dimension temporelle |
| Gold | `factmesuresqualite` | Fait mesures |
| Gold | `factconformite` | Fait conformité |
| Gold | `agg_conformite_departement` | KPI taux de conformité par département |

## Prérequis

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- Azure CLI (`az login`)
- Terraform
- Workspace Databricks avec accès au Data Lake (secrets configurés)

## Infrastructure

L'infrastructure Azure (ADLS Gen2 + Databricks) est gérée par Terraform dans `.cloud/`.

```bash
# Installation des dépendances
uv sync

# Setup complet (récupère la subscription Azure, init + plan + apply Terraform)
invoke pipeline-setup

# Ou étape par étape
invoke get-subscription   # Récupère l'ID de subscription Azure dans .env
invoke tf-init            # Initialise Terraform
invoke tf-plan            # Crée le plan
invoke tf-apply           # Déploie l'infrastructure
invoke env-save           # Sauvegarde les outputs dans .env
```

### Autres commandes utiles

```bash
invoke infra-status       # Vérifie l'état de l'infrastructure
invoke tf-output          # Affiche les outputs Terraform
invoke clean-files        # Nettoie les fichiers temporaires locaux
invoke azure-destroy      # Détruit toutes les ressources Azure (irréversible)
```

## Notebooks Databricks

Copier les notebooks dans Databricks et les exécuter dans l'ordre :

1. `notebooks/01_DLT_Ingestion_Qualite_Eau.py` — Ingestion Bronze via Hub'Eau API
2. `notebooks/02_Silver_Transformation.py` — Nettoyage et standardisation Silver
3. `notebooks/03_Gold_Agregations.py` — Star schema et agrégations Gold
4. `notebooks/04_Quality_Checks.py` — Contrôles qualité Spark natif

Les notebooks lisent les credentials Databricks depuis un secret scope `azure-credentials` :
- `storage-account-name`
- `datalake-access-key`

## Source des données

[Hub'Eau — Qualité de l'eau potable](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable)
- Endpoint communes/réseaux : `/v1/qualite_eau_potable/communes_udi`
- Endpoint analyses : `/v1/qualite_eau_potable/resultats_dis`
