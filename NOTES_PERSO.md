# 📓 Notes Perso - Projet Qualité Eau (Simplon Data Engineer)

## 🚨 IMPORTANT : RÉCUPÉRATION INFRA (20/02/26)
L'infrastructure Azure a été **redéployée à neuf** car les anciennes ressources étaient bloquées/supprimées.
- **Nouveau Workspace Databricks** : `wtr-qlt-dbw-v2`
- **Nouveau Data Lake** : `wtrqltadls`
- **Action Requise** : Avant de relancer les notebooks, je dois mettre à jour les **Secrets Databricks** (`azure-credentials`) avec la nouvelle `DATALAKE_ACCESS_KEY` qui se trouve dans mon fichier `.env` local.

## 📍 Où j'en suis dans le Brief
1.  **Infrastructure** : ✅ Terminé. Déployé via Terraform + Invoke.
2.  **Ingestion Bronze** : 🟡 Code prêt (`01_...`), à tester sur le nouveau cluster.
3.  **Transformation Silver** : 🟡 Code prêt (`02_...`), à valider.
4.  **Agrégations Gold** : 🔴 À affiner. Le code actuel (`03_...`) est un template, je dois le tuner pour que mes agrégats (KPIs) soient "Data-Sharp" pour le rendu Simplon.

## 🎯 Rappel du Focus (Simplon)
Le projet doit démontrer ma maîtrise du **Pipeline Medallion** sur Databricks :
- Ingestion propre depuis API Hub'Eau (pagination logicielle).
- Nettoyage et typage strict en Silver.
- Modélisation en **Star Schema** en Gold (Dim/Fact) pour l'analytique.

## 🛠️ Commandes Utiles
- `uv run invoke infra-status` : Pour vérifier si mon infra est toujours OK.
- `uv run invoke env-save` : Pour rafraîchir mon `.env` si besoin.
