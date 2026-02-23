# 🌊 Contexte du Projet - Pipeline Qualité de l'Eau

## 📋 Vue d'ensemble

L'**Agence Nationale de Sécurité Sanitaire (ANSES)** supervise la qualité de l'eau potable en France. Les résultats de contrôle sanitaire sont publiés sur data.gouv.fr.

**Mission** : Construire un pipeline de données complet pour analyser la qualité de l'eau potable en France.

## 🎯 Objectifs

### Objectif principal
Construire un pipeline de données moderne sur **Azure Databricks** suivant l'architecture **Medallion (Bronze-Silver-Gold)**.

### Objectifs secondaires
1. **Infrastructure Azure** : Data Lake Storage Gen2 + Databricks
2. **Ingestion automatisée** : Récupération des données depuis les APIs
3. **CI/CD** : GitHub Actions avec Semantic Release
4. **Qualité des données** : Validations et contrôles
5. **Orchestration** : Automatisation avec Databricks Workflows
6. **API** : Exposition des données via API

## 🏗️ Architecture Complète

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INFRASTRUCTURE AZURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐      ┌────────────────────────────────────────────┐   │
│  │   data.gouv.fr   │─────▶│   Azure Data Lake Storage Gen2             │   │
│  │   (Source CSV)   │      │                                            │   │
│  └──────────────────┘      └────────────────────────────────────────────┘   │
│                                           │                                 │
│                                           │                                 │
│                                           ▼                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     AZURE DATABRICKS WORKSPACE                        │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    DATA LOAD TOOL (DLT)  https://dlthub.com/ │  │  │
│  │  │  Pipeline d'ingestion automatisee vers Bronze                   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                              ▼                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │              NOTEBOOKS PYSPARK (Databricks Repos)               │  │  │
│  │  │                                                                 │  │  │
│  │  │  01_DLT_Ingestion_Qualite_Eau.py                                │  │  │
│  │  │  02_Silver_Transformation.py                                    │  │  │
│  │  │  03_Gold_Agregations.py                                         │  │  │
│  │  │  04_Quality_Checks.py (Great Expectations)                      │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                              ▼                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                   DATABRICKS WORKFLOWS                          │  │  │
│  │  │  Orchestration automatique du pipeline complet                  │  │  │
│  │  │  Schedule : Quotidien (2h00 Europe/Paris)                       │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                           │                                 │
└───────────────────────────────────────────┼─────────────────────────────────┘
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DEVOPS & CI/CD                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐      ┌────────────────────┐      ┌─────────────────┐  │
│  │  GitHub Repo     │─────▶│  GitHub Actions    │─────▶│   Databricks    │  │
│  │                  │      │                    │      │   Deployment    │  │
│  │  - Notebooks     │      │  - CI : Tests      │      │                 │  │
│  │  - Config        │      │  - CD : Deploy     │      │  (Auto Sync)    │  │
│  │  - Scripts       │      │  - Semantic Release│      │                 │  │
│  └──────────────────┘      └────────────────────┘      └─────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


LEGENDE :
─────────  Flux de donnees
Bronze     Donnees brutes (CSV ingere)
Silver     Donnees nettoyees et enrichies
Gold       Donnees agreges pour l'analyse
DLT        Data Load Tool https://dlthub.com/
```

### Zones de données (Architecture Medallion)

**🥉 Bronze Layer** : Données brutes telles qu'ingérées
- Données brutes depuis data.gouv.fr ou API Hub'Eau
- Partitionnement par année
- Format Delta Lake
- Aucune transformation, données "as-is"

**🥈 Silver Layer** : Données nettoyées et enrichies
- Types corrigés, doublons supprimés
- Colonnes standardisées et renommées
- Enrichissement géographique (régions, départements)
- Partitionnement par année et département
- Validation des données avec Great Expectations

**🥇 Gold Layer** : Tables agrégées par cas d'usage métier
- **Conformité par commune** : Taux de conformité par ville
- **Évolution temporelle des paramètres** : Tendances dans le temps
- **Carte de qualité par région** : Agrégations géographiques
- **Top 10 communes** les plus/moins conformes
- **Analyse des non-conformités** : Focus sur les problèmes
- **Synthèses mensuelles** : KPIs de pilotage

## 🛠️ Technologies

### Cloud et stockage
- **Microsoft Azure** : Cloud provider
- **Azure Data Lake Storage Gen2** : Stockage des données
- **Azure Databricks** : Plateforme de traitement

### Ingestion et transformation
- **API Hub'Eau** : Source de données officielle
- **PySpark** : Transformations de données
- **Delta Lake** : Format de stockage optimisé

### DevOps
- **GitHub** : Versioning du code
- **GitHub Actions** : CI/CD
- **Terraform** : Infrastructure as Code

## 📊 Sources de Données

### API Hub'Eau (Recommandée)
- **URL** : https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable
- **Format** : JSON via API REST
- **Avantages** : Données officielles, filtrage, pagination

### Data.gouv.fr (Alternative)
- **URL** : https://www.data.gouv.fr/datasets/resultats-du-controle-sanitaire-de-leau-distribuee-commune-par-commune/
- **Format** : CSV/ZIP
- **Mise à jour** : Mensuelle

## 🎯 Livrables Attendus

### 📁 Structure du Repository Final
```
water-quality-pipeline/
├── .cloud/                           # Infrastructure Terraform
├── notebooks/                        # Notebooks Databricks
│   ├── 01_DLT_Ingestion_Qualite_Eau.py
│   ├── 02_Silver_Transformation.py
│   ├── 03_Gold_Agregations.py
│   └── 04_Quality_Checks.py (Great Expectations)
├── scripts/                          # Scripts Python utilitaires
├── docs/                            # Documentation
├── .github/workflows/               # GitHub Actions CI/CD
├── .env.example                     # Template variables
└── README.md                        # Guide principal
```

### 🚀 Composants Techniques
1. **Infrastructure Azure** déployée via Terraform
2. **Pipeline DLT** Bronze → Silver → Gold
3. **Notebooks Databricks** avec PySpark
4. **Great Expectations** pour la qualité des données
5. **Databricks Workflows** pour l'orchestration
6. **GitHub Actions** avec Semantic Release
7. **Documentation** complète et API (optionnel)

## 📅 Durée Estimée

**5 jours (30 heures)** répartis en phases logiques :
- Jour 1-2 : Infrastructure + Ingestion
- Jour 3-4 : Transformations + Qualité
- Jour 5 : Orchestration + Documentation