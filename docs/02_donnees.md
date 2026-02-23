# 📊 Sources de Données - Qualité de l'Eau France

## 🌊 Dataset Principal

### Informations générales
- **Période** : 2021-2025 (données en temps réel)
- **Organisme** : Ministère de la Santé et de la Prévention
- **Licence** : Licence Ouverte / Open Licence
- **Taille** : ~50-100 MB par extraction

## 🔗 Sources Disponibles

### 1. API Hub'Eau (Recommandée) ⭐
- **URL** : https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable
- **Documentation** : https://hubeau.eaufrance.fr/page/api-qualite-eau-potable
- **Format** : JSON
- **Avantages** :
  - ✅ API officielle et stable
  - ✅ Données structurées
  - ✅ Filtrage par commune, année, paramètre
  - ✅ Pagination intégrée
  - ✅ Mise à jour en temps réel

#### Endpoints principaux
- `/resultats_dis` : Résultats des analyses
- `/communes_udi` : Liste des communes
- `/installations` : Installations de distribution

#### Paramètres de filtrage
- `annee` : Année (max 10 années)
- `code_commune` : Code INSEE (max 20 codes)
- `nom_commune` : Nom de commune (max 20 noms)
- `code_reseau` : Code SISE-Eaux du réseau
- `page` / `size` : Pagination

### 2. Data.gouv.fr (Alternative)
- **URL** : https://www.data.gouv.fr/datasets/resultats-du-controle-sanitaire-de-leau-distribuee-commune-par-commune/
- **Format** : CSV dans des fichiers ZIP
- **Mise à jour** : Mensuelle
- **Avantages** :
  - ✅ Fichiers complets par période
  - ✅ Données historiques complètes

## 📋 Structure des Données

### Colonnes principales

#### Identification
- `Code commune INSEE` : Code INSEE de la commune
- `Nom de la commune` : Nom de la commune
- `Code postal` : Code postal
- `Nom de l'installation de distribution` : Nom du réseau

#### Paramètres de qualité
- `Date du prelevement` : Date de l'analyse
- `Code parametre` : Code du paramètre analysé
- `Libelle parametre` : Nom du paramètre
- `Resultat` / `resultat_numerique` : Valeur mesurée
- `Unite de mesure` : Unité (UFC/mL, mg/L, etc.)
- `Limite de qualite` : Seuil réglementaire
- `Reference de qualite` : Valeur de référence

#### Conformité
- `Conclusion sur le parametre` : Conforme / Non conforme / Conforme avec remarque
- `conclusion_conformite_prelevement` : Évaluation globale

#### Localisation
- `Coordonnee X` / `Coordonnee Y` : Longitude / Latitude

## 🧪 Paramètres Analysés

### Microbiologie
- **Bactéries aérobies revivifiables** (22°C et 36°C)
- **Escherichia coli** : Indicateur de contamination fécale
- **Entérocoques** : Bactéries résistantes
- **Bactéries coliformes** : Indicateurs de qualité

### Chimie
- **Nitrates (NO3)** : Limite réglementaire 50 mg/L
- **Nitrites (NO2)** : Limite réglementaire 0.5 mg/L  
- **Pesticides et métabolites** : Résidus phytosanitaires
- **Métaux lourds** : Aluminium, Cuivre, Fer, Plomb
- **Minéraux** : Fluorures, Chlorures
- **Physico-chimie** : pH, Conductivité

### Radioactivité
- **Tritium** : Isotope radioactif de l'hydrogène
- **Dose totale indicative** : Radioactivité globale

## 🎯 Architecture Medallion Détaillée

```
data.gouv.fr
    |
    v
[DLT Ingestion]
    |
    v
Bronze Layer (données brutes)
    |
    v
Silver Layer (données nettoyées et enrichies)
    |
    v
Gold Layer (données agrégées pour analyse)
    |
    v
[Visualisations / API]
```

## 📊 Exemples de Données

### Exemple API Hub'Eau
```json
{
  \"nom_commune\": \"Paris\",
  \"code_commune\": \"75056\",
  \"date_prelevement\": \"2024-01-15\",
  \"libelle_parametre\": \"Chlore libre\",
  \"resultat_numerique\": 0.5,
  \"unite_mesure\": \"mg/L\",
  \"conclusion_conformite_prelevement\": \"C\"
}
```

### Exemple CSV data.gouv.fr
```csv
Code commune INSEE,Nom de la commune,Date du prelevement,Libelle parametre,Resultat,Unite de mesure,Conclusion sur le parametre
75056,Paris,15/01/2024,Chlore libre,0.5,mg/L,Conforme
69123,Lyon,15/01/2024,Nitrates,25.0,mg/L,Conforme
```

## 🎯 Stratégie d'Ingestion

### Phase 1 : Test et Exploration
1. **API Hub'Eau** : Récupérer un échantillon (1000 résultats)
2. **Analyse** : Comprendre la structure des données
3. **Validation** : Vérifier la qualité des données

### Phase 2 : Ingestion Complète
1. **Pagination** : Récupérer toutes les données 2024
2. **Filtrage** : Par région ou département si nécessaire
3. **Sauvegarde** : Format Delta Lake dans Bronze

### Phase 3 : Historique (Optionnel)
1. **Data.gouv.fr** : Récupérer les données historiques
2. **Consolidation** : Fusionner avec les données API
3. **Dédoublonnage** : Éliminer les doublons

## 🔍 Points d'Attention

### Qualité des Données
- **Valeurs manquantes** : Certains résultats peuvent être NULL
- **Formats de dates** : Différents selon la source
- **Encodage** : Attention aux caractères spéciaux
- **Doublons** : Possibles entre API et CSV

### Volumétrie
- **API Hub'Eau** : ~1M résultats pour 2024
- **Pagination** : Max 1000 résultats par requête
- **Rate limiting** : Respecter les limites de l'API

### Conformité
- **RGPD** : Données publiques, pas de problème
- **Licence** : Licence Ouverte, usage libre
- **Attribution** : Mentionner la source