# 🥇 Gold Layer - KPI Definitions (PRD-lite)

**Propriétaire**: John (PM)
**Objectif**: Transformer les données nettoyées (Silver) en insights actionnables pour l'ANSES.

## 🎯 Indicateurs de Performance (KPIs)

### 1. Conformité par Commune

- **Description**: Pourcentage de prélèvements conformes sur une période donnée (mois/année).
- **Calcul**: `(Nombre de résultats conformes / Nombre total de prélèvements) * 100`
- **Granularité**: Commune, Département, Région.

### 2. Évolution Temporelle

- **Description**: Tendance de la présence de paramètres critiques (Nitrates, Pesticides).
- **Métrique**: Moyenne glissante du `numeric_result` par mois.
- **Visualisation**: Line chart par paramètre.

### 3. Top 10 des Non-Conformités

- **Description**: Identification des communes les plus à risque.
- **Critère**: Plus grand nombre absolu de prélèvements "non_compliant" sur les 12 derniers mois.

### 4. Alertes de Seuils

- **Description**: Détection des dépassements de limites réglementaires.
- **Métrique**: `numeric_result > limit_quality`.

## 🛠️ Structure des Tables Gold (Cibles)

| Table                     | Colonnes Clés                                   | Description                        |
| :------------------------ | :---------------------------------------------- | :--------------------------------- |
| `gold_compliance_summary` | `city_code`, `sampling_year`, `compliance_rate` | Vue synthétique par ville          |
| `gold_parameter_trends`   | `parameter_code`, `sampling_month`, `avg_value` | Analyse temporelle                 |
| `gold_hotspots`           | `department_code`, `non_compliant_count`        | Focus géographique sur les risques |

## 🚀 Prochaine Étape

Validation de ces KPIs avec l'utilisateur avant l'implémentation du notebook `03_Gold_Agregations.py`.
