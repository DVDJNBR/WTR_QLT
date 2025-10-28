# 💰 Databricks - Optimisation des Coûts

## 🎯 Workspace en cours de création
Le workspace `wtr-qlt-dbw-v2` est en train d'être créé avec le SKU **standard** (moins cher que premium).

## 💡 Optimisations à faire APRÈS création

### 1. **Configuration des Clusters (IMPORTANT)**
Quand tu créeras des clusters dans Databricks :

```
Cluster Settings à configurer :
├── Cluster Mode: "Single Node" (pour dev/test)
├── Databricks Runtime: "13.3 LTS" (stable et moins cher)
├── Node Type: "Standard_DS3_v2" (2 cores, 14GB RAM - suffisant)
├── Auto Termination: "120 minutes" (arrêt automatique)
├── Enable Autoscaling: OFF (pour contrôler les coûts)
└── Spot Instances: ON (si disponible, -70% de coût)
```

### 2. **Politiques de Cluster**
Dans Databricks Admin Console :
- **Cluster Policies** → Créer une policy "Cost Optimized"
- Limiter les types d'instances autorisées
- Forcer l'auto-termination à 2h max
- Interdire les clusters > 4 nodes

### 3. **Monitoring des Coûts**
- **Usage Dashboard** : Surveiller la consommation DBU
- **Alerts** : Configurer des alertes à 50€/mois
- **Tags** : Tagger tous les clusters avec "project=water-quality"

### 4. **Bonnes Pratiques Quotidiennes**

#### ✅ À FAIRE :
- Arrêter les clusters après usage
- Utiliser des notebooks partagés
- Préférer les jobs programmés aux clusters interactifs
- Utiliser Delta Lake pour optimiser les requêtes

#### ❌ À ÉVITER :
- Laisser des clusters tourner la nuit
- Créer des clusters > 4 nodes sans raison
- Utiliser Premium si Standard suffit
- Stocker des données dans DBFS (utilise le Data Lake)

## 📊 Estimation Coûts Water Quality Pipeline

### Workspace (fixe) :
- **Standard SKU** : ~5€/mois

### Clusters (variable) :
- **Dev/Test** (2h/jour) : ~15€/mois
- **Production** (jobs 1h/jour) : ~8€/mois
- **Total estimé** : ~28€/mois

### Pour le Brief (ponctuel) :
- **5 jours de dev** : ~5-10€ total
- **Très raisonnable** pour un projet d'apprentissage !

## 🚨 Alertes à Configurer

1. **Azure Cost Management** :
   - Alerte à 20€/mois sur le Resource Group
   - Notification par email

2. **Databricks Usage** :
   - Alerte à 100 DBU/jour
   - Review hebdomadaire des clusters actifs

## 🔧 Commandes Utiles

```bash
# Voir les coûts Azure
az consumption usage list --start-date 2024-10-01 --end-date 2024-10-31

# Lister les clusters Databricks actifs (via API)
curl -X GET https://wtr-qlt-dbw-v2.azuredatabricks.net/api/2.0/clusters/list
```

---

**💡 Conseil** : Pour le brief qualité de l'eau, tu peux facilement rester sous 10€ de coût total en éteignant les clusters après chaque session !