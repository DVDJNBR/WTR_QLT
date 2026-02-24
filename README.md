# Water Quality Pipeline — France

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?logo=terraform&logoColor=white)
![Delta Lake](https://img.shields.io/badge/Delta_Lake-003366?logo=apachespark&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=white)

Projet d'apprentissage data engineering pour se familiariser avec Azure Databricks, Delta Lake et l'écosystème Azure (ADLS Gen2, Terraform). Le pipeline ingère les données publiques de qualité de l'eau potable en France depuis l'[API Hub'Eau](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable), les transforme selon une architecture Medallion **Bronze → Silver → Gold**, et les expose via une API REST FastAPI sans compute Databricks.

---

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

Autres commandes :

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

## Architecture

### Pipeline de traitement

```mermaid
flowchart LR
    API([Hub'Eau API]) --> NB01[01 · DLT Ingestion]
    NB01 --> NB02[02 · Silver Transformation]
    NB02 --> NB03[03 · Gold Agregations]
    NB03 --> NB04[04 · Quality Checks]
    NB04 --> REST([API REST])

    style NB01 fill:#cd7f32,color:#fff,stroke:#a0522d
    style NB02 fill:#c0c0c0,color:#333,stroke:#999
    style NB03 fill:#ffd700,color:#333,stroke:#daa520
    style NB04 fill:#4caf50,color:#fff,stroke:#388e3c
```

### Couches de données

```mermaid
flowchart TD
    API([Hub'Eau API]) --> b1 & b2

    subgraph BRONZE["Bronze — données brutes"]
        b1[bronze_communes]
        b2[bronze_analyses]
    end

    subgraph SILVER["Silver — données nettoyées"]
        s1[silver_communes]
        s2[silver_mesures]
        s3[silver_conformite]
    end

    subgraph GOLD["Gold — star schema"]
        g1[dim_communes]
        g2[dim_parametres]
        g3[dim_temps]
        g4[factmesuresqualite]
        g5[factconformite]
        g6[agg_conformite_departement]
    end

    BRONZE --> SILVER --> GOLD
    GOLD --> REST([API REST])

    style BRONZE fill:#f5e6d3,stroke:#cd7f32,color:#5a3000
    style SILVER fill:#f0f0f0,stroke:#999,color:#333
    style GOLD fill:#fffde7,stroke:#daa520,color:#5a4000
```

---

## Schéma des données

### Bronze — données brutes Hub'Eau

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

### Silver — données nettoyées et standardisées

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

### Gold — star schema analytique

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
