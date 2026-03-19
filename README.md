# Water Quality Pipeline — France

![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)
![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?logo=terraform&logoColor=white)
![Delta Lake](https://img.shields.io/badge/Delta_Lake-003366?logo=apachespark&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=white)

Projet d'apprentissage data engineering pour se familiariser avec Azure Databricks, Delta Lake et l'écosystème Azure (ADLS Gen2, Terraform). Le pipeline ingère les données publiques de qualité de l'eau potable en France depuis l'[API Hub'Eau](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable), les transforme selon une architecture Medallion **Bronze → Silver → Gold**, et les expose via une API REST FastAPI sans compute Databricks.

---

## Sommaire

- [Reproduire le projet](#reproduire-le-projet)
  - [1. Dépendances](#1-dépendances)
  - [2. Infrastructure Azure](#2-infrastructure-azure)
  - [3. Notebooks Databricks](#3-notebooks-databricks)
  - [4. Orchestration (optionnel)](#4-orchestration-optionnel)
  - [5. API REST (optionnel)](#5-api-rest-optionnel)
- [Architecture](#architecture)
- [Schéma des données](#schéma-des-données)
- [Commandes utiles](#commandes-utiles)

---

<table>
  <tr>
    <td><img src="assets/01_app-carte-france-conformite.png" height="300"/></td>
    <td><img src="assets/02_app-carte-nord-lille.png" height="300"/></td>
    <td><img src="assets/03_app-graphiques-conformite-lille.png" height="300"/></td>
  </tr>
</table>

---

## Reproduire le projet

**Prérequis :** Python 3.13+ ([uv](https://github.com/astral-sh/uv)), Azure CLI, Terraform, Workspace Databricks avec secret scope `azure-credentials` (`storage-account-name`, `datalake-access-key`).

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

### 3. Notebooks Databricks

Copier les notebooks dans le workspace Databricks et les exécuter dans l'ordre :

| # | Notebook | Rôle |
|---|----------|------|
| 1 | `01_DLT_Ingestion_Qualite_Eau.py` | Ingestion incrémentale depuis Hub'Eau API → Bronze |
| 2 | `02_Silver_Transformation.py` | Nettoyage, standardisation, partitionnement → Silver |
| 3 | `03_Gold_Agregations.py` | Star schema + KPIs par département → Gold |
| 4 | `04_Quality_Checks.py` | Contrôles qualité Spark natif |

<table>
  <tr>
    <td><img src="assets/11_databricks-notebook-silver-layer.png" height="280"/></td>
    <td><img src="assets/09_databricks-pipeline-dag.png" height="280"/></td>
    <td><img src="assets/10_databricks-pipeline-tasks.png" height="280"/></td>
    <td><img src="assets/12_azure-storage-gold-tables.png" height="280"/></td>
    <td><img src="assets/13_silver-mesures-donnees-paris.png" height="280"/></td>
  </tr>
</table>

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

<table>
  <tr>
    <td><img src="assets/04_api-swagger-overview.png" height="280"/></td>
    <td><img src="assets/07_api-conformite-stats-reponse.png" height="280"/></td>
    <td><img src="assets/06_api-departements-top-reponse.png" height="280"/></td>
    <td><img src="assets/08_api-parametres-liste.png" height="280"/></td>
    <td><img src="assets/05_api-conformite-stats-erreur-503.png" height="280"/></td>
  </tr>
</table>

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
sequenceDiagram
    participant API as Hub'Eau API
    participant NB01 as 01 · DLT Ingestion
    participant BRONZE as Bronze (ADLS)
    participant NB02 as 02 · Silver Transform
    participant SILVER as Silver (ADLS)
    participant NB03 as 03 · Gold Agregations
    participant GOLD as Gold (ADLS)
    participant NB04 as 04 · Quality Checks
    participant REST as API REST

    rect rgb(245, 230, 211)
        note over API,BRONZE: Ingestion Bronze
        NB01->>API: GET /communes_udi + /resultats_dis (paginé)
        API-->>NB01: données brutes JSON
        NB01->>BRONZE: Delta write (append) — bronze_communes, bronze_analyses
    end

    rect rgb(220, 220, 220)
        note over BRONZE,SILVER: Transformation Silver
        NB02->>BRONZE: Delta read
        NB02->>SILVER: Delta write — silver_communes, silver_mesures, silver_conformite
    end

    rect rgb(255, 250, 205)
        note over SILVER,GOLD: Modélisation Gold
        NB03->>SILVER: Delta read
        NB03->>GOLD: Delta write — dim_*, factmesuresqualite, factconformite, agg_*
    end

    rect rgb(240, 253, 244)
        note over GOLD,NB04: Controle qualité
        NB04->>SILVER: Delta read
        NB04->>GOLD: Delta read
        NB04-->>NB04: assertions Spark natif — counts, nulls, ranges
    end

    rect rgb(240, 249, 255)
        note over GOLD,REST: Exposition
        REST->>GOLD: Delta read (sans compute Databricks)
        REST-->>REST: GET /conformite/departements, /parametres...
    end
```

---

## Schéma des données

### Bronze — données brutes Hub'Eau

```mermaid
%%{init: {'er': {'layoutDirection': 'LR'}}}%%
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
%%{init: {'er': {'layoutDirection': 'LR'}}}%%
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
%%{init: {'er': {'layoutDirection': 'LR'}}}%%
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

---

## Commandes utiles

```bash
invoke infra-status       # État de l'infrastructure locale
invoke tf-output          # Outputs Terraform (URLs, noms)
invoke clean-files        # Nettoie les fichiers temporaires
invoke azure-destroy      # Détruit toutes les ressources Azure ⚠️
```
