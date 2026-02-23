# 📋 Plan de Travail - Pipeline Qualité de l'Eau

## 🎯 Vue d'ensemble (5 jours / 30h)

Découpage logique du projet en phases avec objectifs clairs et livrables.

---

## 📅 Jour 1 : Infrastructure et Connexions (6h)

### 🌅 Matin (3h) : Setup Azure

**Objectif** : Déployer l'infrastructure Azure de base

#### Tâches

1. **Configuration Terraform** (30 min)
   - Vérifier les variables dans `.cloud/terraform.tfvars`
   - Configurer l'authentification Azure (`az login`)

2. **Déploiement infrastructure** (1h30)

   ```bash
   invoke pipeline-setup  # Déploiement complet
   ```

   - Resource Group
   - Data Lake Storage Gen2 avec conteneurs
   - Databricks Workspace

3. **Vérification et tests** (1h)
   - Vérifier les ressources dans le portail Azure
   - Tester l'accès au workspace Databricks
   - Valider le fichier `.env` généré

#### ✅ Livrables Jour 1 Matin

- [x] Infrastructure Azure déployée
- [x] Databricks workspace accessible
- [x] Fichier `.env` avec toutes les credentials
- [x] Conteneurs Data Lake créés (bronze, silver, gold, raw-data)

### 🌆 Après-midi (3h) : Databricks et Données

**Objectif** : Comprendre Databricks et tester l'accès aux données

#### Tâches

1. **Databricks Basics** (1h30)
   - Exécuter le notebook `databricks_basics.ipynb` dans Databricks
   - Comprendre les DataFrames Spark
   - Tester la sauvegarde Delta Lake

2. **Test API Hub'Eau** (1h)
   - Exécuter le notebook `test_hubeau_api.ipynb`
   - Explorer les données disponibles
   - Récupérer un échantillon de données

3. **Configuration cluster** (30 min)
   - Créer un cluster optimisé coût
   - Configurer l'auto-termination (2h)
   - Tester la connexion Data Lake

#### ✅ Livrables Jour 1 Après-midi

- [ ] Notebook Databricks basics fonctionnel
- [ ] API Hub'Eau testée et comprise
- [x] Cluster Databricks configuré (Terraform outputs confirmed)
- [x] Connexion Data Lake validée

---

## 📅 Jour 2 : Ingestion Bronze (6h)

### 🌅 Matin (3h) : Pipeline d'Ingestion

**Objectif** : Créer le pipeline d'ingestion des données brutes

#### Tâches

1. **Script d'ingestion** (2h)
   - Développer le script de récupération API Hub'Eau
   - Gérer la pagination et les erreurs
   - Sauvegarder en format Delta dans bronze

2. **Tests et validation** (1h)
   - Tester avec différentes communes
   - Valider la structure des données
   - Vérifier les performances

#### Code type

```python
# Ingestion API Hub'Eau vers Bronze
def ingest_water_quality_data(year="2024", max_records=10000):
    # Récupération via API
    # Pagination automatique
    # Sauvegarde Delta Lake bronze
    pass
```

### 🌆 Après-midi (3h) : Automatisation

**Objectif** : Automatiser et optimiser l'ingestion

#### Tâches

1. **Notebook DLT** (2h)
   - Créer un pipeline Delta Live Tables
   - Ajouter les validations de qualité
   - Configurer le refresh automatique

2. **Monitoring** (1h)
   - Métriques d'ingestion
   - Logs et alertes
   - Dashboard de suivi

#### ✅ Livrables Jour 2

- [/] Pipeline d'ingestion Bronze fonctionnel (Notebook drafted)
- [ ] Données 2024 ingérées (échantillon significatif)
- [ ] Pipeline DLT configuré
- [ ] Monitoring de base en place

---

## 📅 Jour 3 : Transformations Silver (6h)

### 🌅 Matin (3h) : Nettoyage des Données

**Objectif** : Créer la couche Silver avec données nettoyées

#### Tâches

1. **Analyse de qualité** (1h)
   - Identifier les problèmes de données
   - Doublons, valeurs manquantes, formats
   - Définir les règles de nettoyage

2. **Transformations Silver** (2h)
   - Standardisation des formats de dates
   - Nettoyage des noms de communes
   - Enrichissement géographique
   - Catégorisation des paramètres

#### Code type

```python
@dlt.table(name="water_quality_silver")
def water_quality_silver():
    return (
        dlt.read("water_quality_bronze")
        .withColumn("date_prelevement", to_date(col("date_prelevement")))
        .withColumn("commune_clean", upper(trim(col("nom_commune"))))
        .filter(col("resultat_numerique").isNotNull())
    )
```

### 🌆 Après-midi (3h) : Enrichissement

**Objectif** : Enrichir les données avec des informations contextuelles

#### Tâches

1. **Données de référence** (1h30)
   - Codes INSEE et régions
   - Seuils réglementaires par paramètre
   - Classifications des communes

2. **Jointures et enrichissement** (1h30)
   - Ajouter les informations géographiques
   - Calculer les écarts aux seuils
   - Créer des indicateurs de conformité

#### ✅ Livrables Jour 3

- [ ] Couche Silver avec données nettoyées
- [ ] Enrichissement géographique
- [ ] Indicateurs de conformité calculés
- [ ] Documentation des transformations

---

## 📅 Jour 4 : Agrégations Gold (6h)

### 🌅 Matin (3h) : Tables Gold

**Objectif** : Créer les tables agrégées pour l'analyse

#### Tâches

1. **Définition des cas d'usage** (30 min)
   - Conformité par commune
   - Évolution temporelle
   - Analyse par paramètre
   - Comparaisons régionales

2. **Implémentation Gold** (2h30)
   - 6 tables Gold principales
   - Optimisation des performances
   - Partitionnement intelligent

#### Tables Gold à créer

```python
# 1. Conformité par commune
@dlt.table(name="conformite_par_commune")

# 2. Évolution temporelle des paramètres
@dlt.table(name="evolution_parametres")

# 3. Carte de qualité par région
@dlt.table(name="qualite_par_region")

# 4. Top communes conformes/non-conformes
@dlt.table(name="top_communes")

# 5. Analyse des non-conformités
@dlt.table(name="analyse_non_conformites")

# 6. Synthèse mensuelle
@dlt.table(name="synthese_mensuelle")
```

### 🌆 Après-midi (3h) : Validation et Tests

**Objectif** : Valider la qualité des données avec Great Expectations

#### Tâches

1. **Great Expectations** (2h)
   - Installation et configuration
   - Définition des expectations
   - Tests de validation automatiques

2. **Optimisation** (1h)
   - OPTIMIZE et Z-ORDER sur les tables
   - Vacuum des anciennes versions
   - Métriques de performance

#### ✅ Livrables Jour 4

- [ ] 6 tables Gold créées et optimisées
- [ ] Great Expectations configuré
- [ ] Tests de qualité automatisés
- [ ] Performance optimisée

---

## 📅 Jour 5 : Orchestration et Finalisation (6h)

### 🌅 Matin (3h) : Databricks Workflows

**Objectif** : Automatiser le pipeline complet

#### Tâches

1. **Workflow Databricks** (2h)
   - Orchestration Bronze → Silver → Gold
   - Gestion des dépendances
   - Scheduling quotidien (2h00 Europe/Paris)

2. **Tests end-to-end** (1h)
   - Exécution complète du pipeline
   - Validation des résultats
   - Monitoring des performances

### 🌆 Après-midi (3h) : Documentation et API

**Objectif** : Finaliser le projet avec documentation et API

#### Tâches

1. **API REST** (1h30) - BONUS
   - Exposition des données Gold
   - Endpoints par cas d'usage
   - Documentation Swagger

2. **Documentation finale** (1h30)
   - README complet
   - Guide d'utilisation
   - Architecture documentée
   - Rapport final

#### ✅ Livrables Jour 5

- [ ] Workflow Databricks opérationnel
- [ ] Pipeline automatisé et schedulé
- [ ] API REST (bonus)
- [ ] Documentation complète
- [ ] Projet finalisé

---

## 🎯 Livrables Finaux

### 📁 Structure du Repository

```
water-quality-pipeline/
├── .cloud/                 # Infrastructure Terraform
├── notebooks/              # Notebooks Databricks
├── scripts/               # Scripts Python utilitaires
├── docs/                  # Documentation
├── tests/                 # Tests automatisés
├── .env.example          # Template variables
└── README.md             # Guide principal
```

### 🔗 Liens Importants

- **Repository GitHub** : Lien vers le repo final
- **Databricks Workspace** : URL du workspace
- **Documentation API** : Swagger/OpenAPI
- **Dashboard** : Liens vers les visualisations

### 📊 Métriques de Succès

- ✅ **Infrastructure** : 100% déployée via Terraform
- ✅ **Données** : >100k enregistrements ingérés
- ✅ **Pipeline** : Bronze → Silver → Gold fonctionnel
- ✅ **Qualité** : 0 erreur dans les tests Great Expectations
- ✅ **Performance** : Pipeline complet < 30 minutes
- ✅ **Documentation** : Guide complet et à jour

## 🚨 Points d'Attention

### Risques identifiés

- **API Rate Limiting** : Respecter les limites Hub'Eau
- **Coûts Databricks** : Surveiller la consommation DBU
- **Volumétrie** : Adapter selon la taille réelle des données
- **Complexité DLT** : Prévoir du temps d'apprentissage

### Mitigation

- **Tests fréquents** : Valider chaque étape
- **Monitoring continu** : Coûts et performances
- **Documentation** : Chaque décision technique
- **Backup** : Sauvegardes régulières du code
