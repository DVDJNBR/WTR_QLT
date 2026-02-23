# 📚 Ressources et Documentation

## 🔗 Documentation Officielle

### Azure et Databricks
- [Azure Databricks](https://learn.microsoft.com/azure/databricks/) - Documentation Microsoft
- [Delta Live Tables](https://docs.databricks.com/delta-live-tables/index.html) - Guide DLT
- [Databricks Workflows](https://docs.databricks.com/workflows/index.html) - Orchestration
- [Azure Data Lake Storage Gen2](https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction) - Stockage

### Delta Lake
- [Delta Lake - Documentation officielle](https://docs.delta.io/) - Guide complet
- [Delta Lake sur Azure Databricks](https://learn.microsoft.com/azure/databricks/delta/) - Intégration Azure

**Fonctionnalités clés Delta Lake** :
- Transactions ACID pour la fiabilité
- Time Travel pour l'audit et rollback
- Schema enforcement et evolution
- OPTIMIZE et Z-ORDER pour les performances
- Upserts avec MERGE
- Change Data Feed (CDC)

### Qualité des Données
- [Great Expectations](https://docs.greatexpectations.io/) - Validation de données
- [Databricks Data Quality](https://docs.databricks.com/lakehouse/data-quality.html) - Outils intégrés

## 🎥 Tutoriels Vidéo

### Databricks et Azure
- [Azure Databricks Tutorial](https://www.youtube.com/watch?v=XHQTfppfaTM) - Introduction complète
- [Delta Lake Tutorial](https://www.youtube.com/watch?v=ydZtja4WXWI) - Fonctionnalités et optimisations
- [Databricks Monitoring](https://www.youtube.com/watch?v=U9ctDgoVDIc) - Surveillance avancée

### DevOps et CI/CD
- [Semantic Release Tutorial](https://www.youtube.com/watch?v=mxPfbwJ0FiU&t=288s) - Automatisation des releases
- [GitHub Actions pour Databricks](https://www.youtube.com/watch?v=mah8PV6ugNY&t=394s) - CI/CD pipeline

## 📖 Guides et Standards

### Conventional Commits
- [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) - Standard de commits
- [Semantic Release](https://semantic-release.gitbook.io/) - Versioning automatique

**Formats de commits recommandés** :
```
feat: ajouter la validation des données avec Great Expectations
fix: corriger l'encodage des noms de colonnes
docs: mettre à jour le README avec les instructions
chore: configurer le workflow GitHub Actions
refactor: réorganiser la structure des notebooks
perf: optimiser la requête SQL pour les agrégations
test: ajouter des tests unitaires pour les transformations
```

### Architecture
- [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture) - Pattern Bronze/Silver/Gold
- [Data Lakehouse](https://databricks.com/glossary/data-lakehouse) - Concept et implémentation

## 🌊 Sources de Données

### API Hub'Eau
- [Hub'Eau - Qualité de l'eau](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable) - Documentation API
- [Hub'Eau - Swagger](https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/api-docs) - Interface interactive

### Data.gouv.fr
- [Dataset Qualité de l'eau](https://www.data.gouv.fr/fr/datasets/resultats-du-controle-sanitaire-de-la-qualite-de-leau-distribuee-commune-par-commune/) - Données CSV
- [ANSES - Qualité de l'eau](https://www.anses.fr/fr/content/la-qualit%C3%A9-de-l%E2%80%99eau-du-robinet-en-france) - Contexte réglementaire

## 🛠️ Outils et Technologies

### Terraform
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs) - Documentation
- [Terraform Best Practices](https://www.terraform-best-practices.com/) - Bonnes pratiques

### Python et Data
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/) - API Spark Python
- [Pandas Documentation](https://pandas.pydata.org/docs/) - Manipulation de données
- [Requests Documentation](https://docs.python-requests.org/) - Requêtes HTTP

### Azure CLI
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/) - Commandes Azure
- [Azure Storage CLI](https://docs.microsoft.com/cli/azure/storage) - Gestion du stockage

## 📊 Exemples de Code

### Configuration Databricks
```python
# Connexion Azure Data Lake
spark.conf.set(
    "fs.azure.account.key.wtrqltadls.dfs.core.windows.net",
    "YOUR_STORAGE_KEY"
)

# Lecture Delta Lake
df = spark.read.format("delta").load("abfss://bronze@wtrqltadls.dfs.core.windows.net/water_quality/")
```

### Pipeline DLT
```python
import dlt
from pyspark.sql.functions import *

@dlt.table(name="water_quality_bronze")
def bronze_table():
    return spark.read.format("json").load("/path/to/raw/data")

@dlt.table(name="water_quality_silver")
@dlt.expect_or_fail("valid_date", "date_prelevement IS NOT NULL")
def silver_table():
    return dlt.read("water_quality_bronze").filter(col("resultat_numerique").isNotNull())
```

### API Hub'Eau
```python
import requests

def get_water_quality_data(commune_code, year="2024"):
    url = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/resultats_dis"
    params = {
        "code_commune": commune_code,
        "annee": year,
        "size": 1000
    }
    response = requests.get(url, params=params)
    return response.json()
```

## 🎯 Cas d'Usage et Exemples

### Analyses Métier
- **Conformité par commune** : Pourcentage de conformité par ville
- **Évolution temporelle** : Tendances des paramètres dans le temps
- **Cartographie** : Visualisation géographique de la qualité
- **Alertes** : Détection des non-conformités

### Requêtes SQL Utiles
```sql
-- Top 10 communes les plus conformes
SELECT nom_commune, 
       COUNT(*) as nb_analyses,
       SUM(CASE WHEN conforme = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as taux_conformite
FROM water_quality.silver
GROUP BY nom_commune
HAVING COUNT(*) >= 10
ORDER BY taux_conformite DESC
LIMIT 10;

-- Évolution mensuelle des nitrates
SELECT DATE_TRUNC('month', date_prelevement) as mois,
       AVG(resultat_numerique) as nitrates_moyen
FROM water_quality.silver
WHERE libelle_parametre LIKE '%Nitrates%'
GROUP BY DATE_TRUNC('month', date_prelevement)
ORDER BY mois;
```

## 🔧 Troubleshooting

### Problèmes Courants

#### Databricks
- **Cluster timeout** : Configurer auto-termination
- **Out of memory** : Optimiser les requêtes, augmenter la taille du cluster
- **Permissions Data Lake** : Vérifier les clés d'accès

#### Terraform
- **State lock** : `terraform force-unlock LOCK_ID`
- **Ressources existantes** : Utiliser `terraform import`
- **Permissions Azure** : Vérifier les rôles assignés

#### API Hub'Eau
- **Rate limiting** : Ajouter des délais entre requêtes
- **Timeout** : Augmenter les timeouts, gérer les retry
- **Pagination** : Implémenter la pagination correctement

### Commandes Utiles
```bash
# Terraform
terraform state list
terraform state show azurerm_databricks_workspace.main
terraform refresh

# Azure CLI
az account show
az storage account list
az databricks workspace list

# Databricks CLI
databricks clusters list
databricks jobs list
databricks fs ls dbfs:/
```

## 📈 Monitoring et Métriques

### Métriques Clés
- **Volumétrie** : Nombre d'enregistrements par couche
- **Qualité** : Pourcentage de données valides
- **Performance** : Temps d'exécution des pipelines
- **Coûts** : Consommation DBU et stockage

### Alertes Recommandées
- **Pipeline failure** : Échec d'exécution
- **Data quality** : Baisse de qualité des données
- **Cost spike** : Augmentation anormale des coûts
- **Storage growth** : Croissance rapide du stockage

## 🎓 Formation et Certification

### Certifications Azure
- [Azure Data Engineer Associate](https://docs.microsoft.com/learn/certifications/azure-data-engineer/) - DP-203
- [Azure Databricks Developer](https://academy.databricks.com/category/certifications) - Certification Databricks

### Formations Recommandées
- [Microsoft Learn - Azure Data](https://docs.microsoft.com/learn/browse/?products=azure&roles=data-engineer)
- [Databricks Academy](https://academy.databricks.com/) - Formations gratuites
- [Delta Lake Training](https://delta.io/learn/) - Spécialisation Delta Lake

## 🤝 Communauté et Support

### Forums et Communautés
- [Databricks Community](https://community.databricks.com/) - Forum officiel
- [Stack Overflow - Databricks](https://stackoverflow.com/questions/tagged/databricks) - Q&A
- [Azure Community](https://techcommunity.microsoft.com/t5/azure/ct-p/Azure) - Support Microsoft

### Blogs et Articles
- [Databricks Blog](https://databricks.com/blog) - Actualités et tutoriels
- [Azure Data Blog](https://techcommunity.microsoft.com/t5/azure-data-blog/bg-p/AzureDataBlog) - Articles techniques
- [Delta Lake Blog](https://delta.io/blog/) - Nouveautés Delta Lake