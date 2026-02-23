# 📚 Documentation - Pipeline Qualité de l'Eau France

## 🎯 Vue d'ensemble

Documentation complète du projet de pipeline de données pour l'analyse de la qualité de l'eau potable en France.

## 📋 Structure de la Documentation

### 📖 Guides Principaux

1. **[01_contexte.md](01_contexte.md)** 🌊
   - Contexte du projet et objectifs
   - Architecture cible (Medallion)
   - Technologies utilisées
   - Livrables attendus

2. **[02_donnees.md](02_donnees.md)** 📊
   - Sources de données (API Hub'Eau, data.gouv.fr)
   - Structure des données
   - Paramètres analysés
   - Stratégie d'ingestion

3. **[03_infrastructure.md](03_infrastructure.md)** 🏗️
   - Infrastructure Azure (Terraform)
   - Configuration Databricks
   - Sécurité et optimisation des coûts
   - Troubleshooting

4. **[04_taches.md](04_taches.md)** 📅
   - Plan de travail détaillé (5 jours)
   - Tâches par jour avec livrables
   - Métriques de succès
   - Points d'attention

5. **[05_ressources.md](05_ressources.md)** 📚
   - Documentation officielle
   - Tutoriels vidéo
   - Exemples de code
   - Troubleshooting avancé

## 🚀 Quick Start

### Prérequis
- Azure CLI configuré (`az login`)
- Python 3.13+ avec uv
- Terraform installé
- Permissions Azure appropriées

### Déploiement Rapide
```bash
# 1. Cloner le repository
git clone <repository-url>
cd water-quality-pipeline

# 2. Installer les dépendances
uv sync

# 3. Déployer l'infrastructure
uv run invoke pipeline-setup

# 4. Vérifier le déploiement
uv run invoke infra-status
```

### Première Utilisation
1. **Lire le contexte** → [01_contexte.md](01_contexte.md)
2. **Comprendre les données** → [02_donnees.md](02_donnees.md)
3. **Déployer l'infrastructure** → [03_infrastructure.md](03_infrastructure.md)
4. **Suivre le plan de travail** → [04_taches.md](04_taches.md)

## 🎯 Parcours d'Apprentissage

### 👶 Débutant
1. **Contexte** : Comprendre les objectifs du projet
2. **Infrastructure** : Déployer Azure avec Terraform
3. **Databricks Basics** : Notebook `databricks_basics.ipynb`
4. **Test API** : Notebook `test_hubeau_api.ipynb`

### 🧑‍💻 Intermédiaire
1. **Ingestion Bronze** : Pipeline de récupération des données
2. **Transformations Silver** : Nettoyage et enrichissement
3. **Agrégations Gold** : Tables métier et analyses
4. **Qualité des données** : Great Expectations

### 🚀 Avancé
1. **Delta Live Tables** : Pipelines automatisés
2. **Databricks Workflows** : Orchestration complète
3. **Monitoring** : Métriques et alertes
4. **API REST** : Exposition des données

## 📊 Architecture du Projet

```
┌─────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES                       │
├─────────────────────────────────────────────────────────────┤
│  API Hub'Eau          │         Data.gouv.fr               │
│  (JSON, temps réel)   │         (CSV/ZIP, mensuel)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 AZURE DATA LAKE STORAGE GEN2               │
├─────────────────────────────────────────────────────────────┤
│  🥉 BRONZE          🥈 SILVER          🥇 GOLD             │
│  Données brutes     Données nettoyées  Données agrégées    │
│  Format Delta       Enrichies          Analyses métier     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   AZURE DATABRICKS                         │
├─────────────────────────────────────────────────────────────┤
│  • Delta Live Tables (DLT)                                 │
│  • PySpark Transformations                                 │
│  • Great Expectations (Qualité)                           │
│  • Workflows (Orchestration)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONSOMMATION                             │
├─────────────────────────────────────────────────────────────┤
│  • Notebooks d'analyse                                     │
│  • API REST (optionnel)                                    │
│  • Dashboards                                              │
│  • Rapports automatisés                                    │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Commandes Utiles

### Infrastructure
```bash
# Déploiement complet
uv run invoke pipeline-setup

# Étapes individuelles
uv run invoke get-subscription    # Récupérer subscription ID
uv run invoke tf-init            # Initialiser Terraform
uv run invoke tf-plan            # Créer le plan
uv run invoke tf-apply           # Déployer (+ .env automatique)

# Gestion
uv run invoke infra-status       # État de l'infrastructure
uv run invoke tf-output          # Voir les outputs
uv run invoke clean-files        # Nettoyer les fichiers locaux
uv run invoke azure-destroy      # DÉTRUIRE (attention!)
```

### Données
```bash
# Tests de connexion
python scripts/test_data_access.py
python scripts/test_hubeau_api.py

# Ingestion
uv run invoke bronze-ingestion   # Pipeline d'ingestion Bronze
```

### Databricks
```bash
# Notebooks à exécuter dans Databricks
notebooks/databricks_basics.ipynb      # Comprendre les bases
notebooks/test_hubeau_api.ipynb        # Tester l'API
notebooks/01_DLT_Ingestion_Qualite_Eau.py  # Pipeline DLT
```

## 📈 Métriques de Succès

### Infrastructure ✅
- [ ] Resource Group créé
- [ ] Data Lake Storage Gen2 déployé
- [ ] Databricks Workspace accessible
- [ ] Conteneurs bronze/silver/gold créés
- [ ] Fichier `.env` généré automatiquement

### Données ✅
- [ ] API Hub'Eau testée et fonctionnelle
- [ ] Échantillon de données récupéré
- [ ] Structure des données comprise
- [ ] Pipeline d'ingestion Bronze opérationnel

### Pipeline ✅
- [ ] Couche Bronze avec données brutes
- [ ] Couche Silver avec données nettoyées
- [ ] Couche Gold avec agrégations métier
- [ ] Tests de qualité (Great Expectations)
- [ ] Orchestration automatisée (Workflows)

## 🚨 Support et Troubleshooting

### Problèmes Courants
- **Terraform locked** → `uv run invoke tf-unlock --lock-id=ID`
- **Ressources existantes** → Changer les noms dans `terraform.tfvars`
- **Permissions Azure** → Vérifier `az account show`
- **Databricks inaccessible** → Vérifier l'URL dans `.env`

### Où Chercher de l'Aide
1. **Documentation** → [05_ressources.md](05_ressources.md)
2. **Logs** → Fichier `logs/infrastructure.log`
3. **Azure Portal** → Vérifier les ressources déployées
4. **Databricks UI** → Logs des clusters et jobs

## 🎯 Prochaines Étapes

Selon ton niveau et tes objectifs :

### 🏁 **Finir le projet de base**
→ Suivre [04_taches.md](04_taches.md) jour par jour

### 🚀 **Aller plus loin**
→ API REST, monitoring avancé, ML sur les données

### 📚 **Approfondir**
→ Certifications Azure Data Engineer, Databricks Developer

---

**💡 Conseil** : Commence par lire [01_contexte.md](01_contexte.md) pour bien comprendre les objectifs, puis suis le plan dans [04_taches.md](04_taches.md) !

**🎉 Bon projet !** 🌊