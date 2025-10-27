# 🌊 Water Quality Pipeline - France

Pipeline de données Azure pour l'analyse de la qualité de l'eau potable en France basé sur les données de data.gouv.fr.

## 🚀 Quick Start

### 1. Configuration des variables

Les variables sont définies dans `.cloud/variables.tf` et `.cloud/terraform.tfvars`.

Principales variables à personnaliser dans `terraform.tfvars` :
- `project_name` : Nom de votre projet
- `resource_group_name` : Nom du resource group Azure
- `location` : Région Azure (westeurope, francecentral...)
- `lake_name` : Nom unique du Data Lake Storage
- `subscription_id` : Votre ID de souscription Azure

### 2. Déploiement avec Invoke

```bash
# Installation des dépendances
uv sync

# Déploiement complet (init + plan + apply + save .env)
invoke full-setup

# Ou étape par étape :
invoke init      # Initialiser Terraform
invoke plan      # Créer le plan
invoke apply     # Appliquer les changements
invoke save-env  # Sauvegarder les outputs dans .env
```

### 3. Gestion de l'infrastructure

```bash
# Voir le statut
invoke status

# Voir les outputs Terraform
invoke output

# Nettoyer les fichiers temporaires
invoke clean

# Détruire l'infrastructure (attention !)
invoke destroy
```

## 📁 Structure du projet

```
.
├── .cloud/                 # Configuration Terraform
│   ├── main.tf            # Ressources principales
│   ├── variables.tf       # Définition des variables
│   ├── terraform.tfvars   # Valeurs des variables
│   └── outputs.tf         # Outputs Terraform
├── tasks.py               # Scripts Invoke pour l'infrastructure
├── .env.example          # Exemple de variables d'environnement
└── README.md
```

## 🔧 Variables disponibles

### Infrastructure de base
- `project_name` : Nom du projet
- `resource_group_name` : Resource group Azure
- `location` : Région Azure

### Data Lake Storage Gen2
- `lake_name` : Nom du storage account
- `containers` : Liste des conteneurs (bronze, silver, gold, raw-data)

### Databricks
- `databricks_workspace_name` : Nom du workspace
- `databricks_sku` : SKU (standard, premium, trial)

### Service Principals
- `sp_datalake_name` : SP pour l'accès au Data Lake
- `sp_databricks_name` : SP pour Databricks

### Key Vault
- `keyvault_name` : Nom du Key Vault
- `keyvault_secrets` : Liste des secrets à créer

### Source de données
- `data_source_url` : URL de l'API data.gouv.fr
- `data_refresh_schedule` : Planning de rafraîchissement (cron)

## 🔐 Variables d'environnement (.env)

Après `invoke save-env`, le fichier `.env` contiendra :
- `DATALAKE_CLIENT_ID` / `DATALAKE_CLIENT_SECRET`
- `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`
- `KEYVAULT_NAME`
- `DATALAKE_NAME`
- `DATABRICKS_WORKSPACE_URL`
- `RESOURCE_GROUP_NAME`
- `SUBSCRIPTION_ID`

## 📊 Architecture Medallion

```
data.gouv.fr → Bronze (raw) → Silver (cleaned) → Gold (aggregated)
```

## 🛠️ Prérequis

- Python 3.13+
- Azure CLI configuré
- Terraform installé
- Permissions Azure appropriées

## 📝 Basé sur le brief

Ce projet implémente le brief détaillé dans `RESSOURCES/BRIEF_QUALITE_EAU_FRANCE.md` avec une approche simplifiée utilisant Invoke au lieu d'une classe manager complexe.