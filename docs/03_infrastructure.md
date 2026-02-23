# 🏗️ Infrastructure Azure - Pipeline Qualité de l'Eau

## 🎯 Vue d'ensemble

Infrastructure Azure déployée via **Terraform** pour supporter le pipeline de données.

## 📦 Ressources Azure

### 1. Resource Group
- **Nom** : `RG_DBREAU`
- **Région** : `francecentral`
- **Rôle** : Conteneur logique pour toutes les ressources

### 2. Azure Data Lake Storage Gen2
- **Nom** : `wtrqltadls` (doit être unique globalement)
- **Type** : Storage Account avec namespace hiérarchique
- **Réplication** : LRS (Local Redundant Storage)
- **Performance** : Standard

#### Conteneurs
- **bronze** : Données brutes ingérées
- **silver** : Données nettoyées et enrichies
- **gold** : Données agrégées pour l'analyse
- **raw-data** : Fichiers temporaires et de sauvegarde

### 3. Azure Databricks Workspace
- **Nom** : `wtr-qlt-dbw-v2`
- **SKU** : Standard (optimisé coût)
- **Région** : `francecentral`
- **Accès** : Public (pour simplifier)

## 🛠️ Déploiement avec Terraform

### Structure des fichiers
```
.cloud/
├── main.tf          # Ressources principales
├── variables.tf     # Définition des variables
├── terraform.tfvars # Valeurs des variables
└── outputs.tf       # Outputs (URLs, noms, etc.)
```

### Variables principales
```hcl
# Projet
project_name = "water_quality"
resource_group_name = "RG_DBREAU"
location = "francecentral"

# Data Lake
lake_name = "wtrqltadls"

# Databricks
databricks_workspace_name = "wtr-qlt-dbw-v2"
databricks_sku = "standard"
```

### Commandes de déploiement
```bash
# Déploiement complet
invoke pipeline-setup

# Ou étape par étape
invoke tf-init      # Initialiser Terraform
invoke tf-plan      # Créer le plan
invoke tf-apply     # Déployer (+ sauvegarde .env automatique)
```

## 🔐 Sécurité et Accès

### Authentification
- **Azure CLI** : Authentification via `az login`
- **Terraform** : Utilise le contexte Azure CLI
- **Databricks** : Accès via Azure AD

### Permissions
- **Data Lake** : Databricks a accès via l'identité managée
- **Resource Group** : Permissions Contributor nécessaires
- **Subscription** : Accès en lecture/écriture requis

### Variables d'environnement (.env)
```bash
# Généré automatiquement après déploiement
AZURE_SUBSCRIPTION_ID=029b3537-0f24-400b-b624-6058a145efe1
DATALAKE_NAME=wtrqltadls
DATALAKE_ACCESS_KEY=xxx
DATALAKE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
DATABRICKS_WORKSPACE_URL=https://adb-xxx.azuredatabricks.net
RESOURCE_GROUP_NAME=RG_DBREAU
```

## 💰 Optimisation des Coûts

### Data Lake Storage Gen2
- **Coût** : ~2-5€/mois pour le projet
- **Optimisations** :
  - Tier Standard (pas Premium)
  - LRS (pas GRS)
  - Lifecycle policies pour archivage

### Databricks
- **Workspace** : ~5€/mois (fixe)
- **Clusters** : Variable selon usage
- **Optimisations** :
  - SKU Standard (pas Premium)
  - Auto-termination 2h
  - Single node pour dev/test
  - Spot instances si disponible

#### Configuration cluster recommandée
```python
{
    "cluster_name": "water-quality-cluster",
    "spark_version": "13.3.x-scala2.12",
    "node_type_id": "Standard_DS3_v2",  # 2 cores, 14GB RAM
    "num_workers": 0,  # Single node
    "autotermination_minutes": 120,
    "enable_elastic_disk": False
}
```

## 🔧 Configuration Post-Déploiement

### 1. Databricks Workspace
1. **Se connecter** : Utiliser l'URL depuis `.env`
2. **Créer un cluster** : Configuration optimisée coût
3. **Configurer l'accès Data Lake** :
   ```python
   spark.conf.set(
       "fs.azure.account.key.wtrqltadls.dfs.core.windows.net",
       dbutils.secrets.get("scope", "storage-key")
   )
   ```

### 2. Secrets Databricks (Optionnel)
```bash
# Créer un secret scope
databricks secrets create-scope --scope water-quality

# Ajouter la clé de storage
databricks secrets put --scope water-quality --key storage-key
```

### 3. Notebooks
- **Importer** les notebooks depuis le repository
- **Configurer** les chemins vers les conteneurs
- **Tester** la connexion aux données

## 📊 Monitoring et Maintenance

### Surveillance des coûts
- **Azure Cost Management** : Alertes à 20€/mois
- **Databricks Usage** : Monitoring des DBU consommées
- **Storage** : Surveillance de la croissance des données

### Maintenance
- **Terraform State** : Sauvegardé localement (attention aux conflits)
- **Backups** : Data Lake avec versioning Delta Lake
- **Updates** : Terraform et providers à jour

### Commandes utiles
```bash
# Voir les coûts
az consumption usage list --start-date 2024-10-01

# État de l'infrastructure
invoke infra-status

# Outputs Terraform
invoke tf-output

# Nettoyage (garde les ressources Azure)
invoke clean-files

# Destruction complète (ATTENTION!)
invoke azure-destroy
```

## 🚨 Troubleshooting

### Problèmes courants

#### Terraform Lock
```bash
# Si terraform est bloqué
invoke tf-unlock --lock-id=LOCK_ID
```

#### Ressources existantes
```bash
# Si des ressources existent déjà
invoke tf-import  # Importer dans le state
# Ou changer les noms dans terraform.tfvars
```

#### Permissions insuffisantes
```bash
# Vérifier les permissions Azure
az account show
az role assignment list --assignee $(az account show --query user.name -o tsv)
```

#### Databricks inaccessible
- Vérifier l'URL dans `.env`
- Confirmer que le workspace est déployé
- Tester l'accès via le portail Azure

## 🎯 Prochaines Étapes

1. **✅ Infrastructure déployée** → Passer à l'ingestion des données
2. **📊 Tester Databricks** → Notebook de base pour comprendre
3. **🌊 Ingestion Bronze** → Récupérer les données API Hub'Eau
4. **🔧 Transformations** → Silver et Gold layers