# Water Quality Pipeline — France

Pipeline de données Azure pour analyser la qualité de l'eau potable en France à partir de l'[API Hub'Eau](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable) (data.gouv.fr).

Les données brutes (prélèvements, paramètres physico-chimiques, conformité réglementaire) transitent par une architecture **Medallion** Bronze → Silver → Gold sur Azure Data Lake Storage Gen2 + Databricks, et sont exposées via une API REST FastAPI.

## Architecture

```mermaid
flowchart TD
    API_HUBEAU["🌊 Hub'Eau API<br/>qualite_eau_potable"] --> NB01

    subgraph DATABRICKS["⚡ Databricks"]
        NB01["📓 01_DLT_Ingestion<br/>qualite_eau"] --> BRONZE
        BRONZE["🥉 Bronze<br/>bronze_communes<br/>bronze_analyses"] --> NB02
        NB02["📓 02_Silver<br/>Transformation"] --> SILVER
        SILVER["🥈 Silver<br/>silver_communes<br/>silver_mesures<br/>silver_conformite"] --> NB03
        NB03["📓 03_Gold<br/>Agrégations"] --> GOLD
        GOLD["🥇 Gold<br/>dim_* · fact_* · agg_*"] --> NB04
        NB04["📓 04_Quality<br/>Checks ✅"]
    end

    subgraph ADLS["☁️ Azure Data Lake Gen2"]
        BRONZE
        SILVER
        GOLD
    end

    GOLD --> API["🔌 api_qualite_eau.py<br/>FastAPI"]
    API --> CLIENT["📊 Client / Dashboard"]

    subgraph INFRA["🏗️ Infrastructure"]
        TF["Terraform (.cloud/)"] --> ADLS
        TF --> DATABRICKS
        WF["create_workflow.py<br/>→ Databricks Workflows"] --> DATABRICKS
    end
```

## Reproduire le projet

### Prérequis

- Python 3.13+ avec [uv](https://github.com/astral-sh/uv)
- Azure CLI (`az login`)
- Terraform
- Workspace Databricks avec secret scope `azure-credentials` :
  - `storage-account-name`
  - `datalake-access-key`

### 1. Dépendances

```bash
uv sync
cp .env.example .env
```

### 2. Infrastructure Azure

```bash
invoke get-subscription   # Récupère l'ID de subscription → .env
invoke tf-init            # Initialise Terraform
invoke tf-plan            # Crée le plan
invoke tf-apply           # Déploie ADLS Gen2 + Databricks workspace
invoke env-save           # Sauvegarde tous les outputs dans .env
```

> `invoke env-save` remplit automatiquement `DATALAKE_NAME`, `DATALAKE_ACCESS_KEY`, `DATABRICKS_WORKSPACE_URL` et `RESOURCE_GROUP_NAME`.
> Seul `DATABRICKS_TOKEN` est à renseigner manuellement (Databricks > User Settings > Access Tokens).

Autres commandes disponibles :

```bash
invoke infra-status       # État de l'infrastructure locale
invoke tf-output          # Outputs Terraform (URLs, noms)
invoke clean-files        # Nettoie les fichiers temporaires
invoke azure-destroy      # Détruit toutes les ressources Azure ⚠️
```

### 3. Notebooks Databricks

Copier les notebooks dans le workspace Databricks et les exécuter dans l'ordre :

| # | Notebook | Rôle |
|---|----------|------|
| 1 | `01_DLT_Ingestion_Qualite_Eau.py` | Ingestion incrémentale depuis Hub'Eau API → Bronze |
| 2 | `02_Silver_Transformation.py` | Nettoyage, standardisation, partitionnement → Silver |
| 3 | `03_Gold_Agregations.py` | Star schema + KPIs par département → Gold |
| 4 | `04_Quality_Checks.py` | Contrôles qualité Spark natif |

### 4. Orchestration (optionnel)

Créer le workflow Databricks `Pipeline_Qualite_Eau_Complet` (schedule quotidien 2h00 Paris) :

```bash
# DATABRICKS_TOKEN et DATABRICKS_NOTEBOOKS_PATH doivent être dans .env
python scripts/create_workflow.py            # Crée le job (pausé par défaut)
python scripts/create_workflow.py --dry-run  # Affiche la config sans créer
```

### 5. API REST (optionnel)

Expose les tables Gold directement depuis ADLS, sans compute Databricks :

```bash
python scripts/api_qualite_eau.py
# Documentation interactive : http://localhost:8000/docs
```

| Endpoint | Description |
|----------|-------------|
| `GET /conformite/departements` | Taux de conformité par département |
| `GET /conformite/departements/{code}` | Détail d'un département |
| `GET /departements/top?order=best\|worst` | Top 10 meilleurs/pires départements |
| `GET /communes?department_code={code}` | Communes filtrables par département |
| `GET /parametres` | Paramètres analysés (nitrates, pH, bactéries…) |
| `GET /mesures/stats` | Statistiques globales des mesures |
| `GET /conformite/stats` | Taux de conformité global PC + bactériologique |

---

## Schéma des données

### 🥉 Bronze — données brutes Hub'Eau

```mermaid
erDiagram
    bronze_communes {
        string code_commune PK
        string nom_commune
        string code_reseau
        string nom_reseau
        string code_departement
    }
    bronze_analyses {
        string code_prelevement PK
        string code_commune FK
        string code_departement
        string date_prelevement
        string code_parametre
        string libelle_parametre
        double resultat_numerique
        string libelle_unite
        string conformite_limites_pc_prelevement
        string conformite_limites_bact_prelevement
        string conclusion_conformite_prelevement
        timestamp ingestion_timestamp
        string source
        int year
    }
    bronze_communes ||--o{ bronze_analyses : "code_commune"
```

### 🥈 Silver — données nettoyées et standardisées

```mermaid
erDiagram
    silver_communes {
        string commune_code PK
        string commune_name
        string department_code
    }
    silver_mesures {
        string sampling_id PK
        string commune_code FK
        string department_code
        timestamp sampling_date
        int sampling_year
        string parameter_code
        string parameter_name
        double numeric_result
        string unit
    }
    silver_conformite {
        string sampling_id PK
        timestamp sampling_date
        int sampling_year
        string department_code
        string parameter_code
        boolean is_compliant_pc
        boolean is_compliant_bact
        string global_conclusion
    }
    silver_communes ||--o{ silver_mesures : "commune_code"
    silver_mesures ||--|| silver_conformite : "sampling_id"
```

> Partitionnement Delta : `silver_mesures` et `silver_conformite` sont partitionnées par `sampling_year` / `department_code`.

### 🥇 Gold — star schema analytique

```mermaid
erDiagram
    dim_communes {
        string commune_code PK
        string commune_name
        string department_code
    }
    dim_parametres {
        string parameter_code PK
        string parameter_name
        string unit
    }
    dim_temps {
        int date_key PK
        date sampling_date
        int year
        int month
        int quarter
        int day_of_week
    }
    factmesuresqualite {
        string sampling_id PK
        string commune_code FK
        string parameter_code FK
        int date_key FK
        double numeric_result
    }
    factconformite {
        string sampling_id PK
        string parameter_code FK
        int date_key FK
        boolean is_compliant_pc
        boolean is_compliant_bact
    }
    agg_conformite_departement {
        string department_code PK
        int total_tests
        int compliant_tests
        double compliance_rate
    }
    dim_communes ||--o{ factmesuresqualite : "commune_code"
    dim_parametres ||--o{ factmesuresqualite : "parameter_code"
    dim_temps ||--o{ factmesuresqualite : "date_key"
    dim_parametres ||--o{ factconformite : "parameter_code"
    dim_temps ||--o{ factconformite : "date_key"
```
