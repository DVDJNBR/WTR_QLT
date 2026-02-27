"""
Dashboard Taipy — Qualité de l'eau potable en France (2024)
Version Ultra-Stable — Pré-rendu Synchrone (Zéro Freeze)
"""

import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from taipy.gui import Gui, State

DATA_DIR = Path(__file__).parent / "data"

MOIS_LABELS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}

COLOR_SCALE = [
    (0.0, "#ff4d4d"), (0.8, "#ffaf40"), (0.95, "#32ff7e"), (1.0, "#18dcff"),
]

# --- CHARGEMENT DES DONNÉES ---
print(">>> Démarrage du dashboard (Echelle Nationale 2024)")
print("1/3 Chargement des fichiers Parquet et GeoJSON...", flush=True)

df_agg_commune = pd.read_parquet(DATA_DIR / "agg_commune_mois.parquet")
df_agg_dept = pd.read_parquet(DATA_DIR / "agg_dept_mois.parquet")
df_raw = pd.read_parquet(DATA_DIR / "prelevements_2024.parquet")

with open(DATA_DIR / "departements.geojson", encoding="utf-8") as f:
    geojson_dept = json.load(f)

with open(DATA_DIR / "communes_france.geojson", encoding="utf-8") as f:
    geojson_commune_all = json.load(f)

# Mapping noms
dept_names = {f["properties"]["code"]: f["properties"]["nom"] for f in geojson_dept["features"]}
commune_names = {f["properties"]["code"]: f["properties"]["nom"] for f in geojson_commune_all["features"]}

df_agg_dept["nom_dept"] = df_agg_dept["code_departement"].map(dept_names)
df_agg_commune["nom_commune"] = df_agg_commune["code_commune"].map(commune_names)
df_raw["nom_commune"] = df_raw["code_commune"].map(commune_names)

mois_disponibles = sorted(df_agg_dept["mois"].unique().tolist())
mois_labels_list = [MOIS_LABELS[m] for m in mois_disponibles]
all_communes = sorted([c for c in df_agg_commune["nom_commune"].unique().tolist() if isinstance(c, str)])

# --- MOTEUR DE RENDU ---
class _HtmlChart:
    def __init__(self, html: str):
        self.html = html

def create_dept_map(df: pd.DataFrame) -> go.Figure:
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson_dept,
        locations="code_departement",
        featureidkey="properties.code",
        color="compliance_rate",
        color_continuous_scale=COLOR_SCALE,
        range_color=[70, 100],
        mapbox_style="carto-darkmatter",
        zoom=5,
        center={"lat": 46.5, "lon": 2.5},
        opacity=0.8,
        hover_name="nom_dept",
        hover_data={"compliance_rate": ":.1f"}
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        mapbox=dict(pitch=45, bearing=0),
        coloraxis_colorbar=dict(
            title="Qualité %", thickness=15, len=0.4, 
            x=0.02, y=0.05, bgcolor="rgba(15, 23, 42, 0.8)",
            tickfont=dict(color="#e2e8f0")
        )
    )
    return fig

# --- PRÉ-RENDU (Le secret de la fluidité) ---
print("2/3 Pré-rendu des cartes mensuelles (Vitesse optimale)...", flush=True)
charts_cache = {}
kpis_cache = {}
distrib_cache = {}

for m in mois_disponibles:
    df_m = df_agg_dept[df_agg_dept["mois"] == m].copy()
    
    # Carte
    fig = create_dept_map(df_m)
    charts_cache[m] = _HtmlChart(fig.to_html(include_plotlyjs="cdn", full_html=True, config={"displayModeBar": False, "displaylogo": False}))
    
    # KPIs
    kpis_cache[m] = (
        len(df_m),
        round(float(df_m["compliance_rate"].mean()), 1),
        int((df_m["compliance_rate"] >= 95).sum()),
        int((df_m["compliance_rate"] < 95).sum())
    )
    
    # Distribution
    bins = [0, 80, 95, 99, 100]
    labels = ["< 80%", "80-95%", "95-99%", "100%"]
    df_m["tranche"] = pd.cut(df_m["compliance_rate"], bins=bins, labels=labels, include_lowest=True)
    dist = df_m["tranche"].value_counts().reindex(labels).reset_index()
    dist.columns = ["Tranche", "Nombre"]
    distrib_cache[m] = dist
    print(f"  - {MOIS_LABELS[m]} terminé", flush=True)

# --- ÉTAT INITIAL ---
selected_month = 1
selected_month_label = MOIS_LABELS[1]
chart_figure = charts_cache[1]
nb_entites, conformity_mean, nb_conformes, nb_alerte = kpis_cache[1]
distrib_data = distrib_cache[1]

search_commune = "Paris"
selected_commune_name = "Paris"
commune_trend_data = pd.DataFrame(columns=["mois", "Type", "Valeur"])

# Layouts graphiques
distrib_layout = {"margin": {"l": 30, "r": 10, "t": 10, "b": 30}, "font": {"color": "#e2e8f0", "size": 10}}
trend_layout = {"margin": {"l": 30, "r": 10, "t": 10, "b": 30}, "font": {"color": "#e2e8f0", "size": 10}, "yaxis": {"range": [0, 105]}}
no_bar_config = {"displayModeBar": False}

# --- LOGIQUE ---
def update_ui(state: State):
    m = state.selected_month
    if m in charts_cache:
        state.chart_figure = charts_cache[m]
        state.selected_month_label = MOIS_LABELS[m]
        state.nb_entites, state.conformity_mean, state.nb_conformes, state.nb_alerte = kpis_cache[m]
        state.distrib_data = distrib_cache[m]

def _update_commune_trend(state: State, commune_name: str):
    df_c = df_raw[df_raw["nom_commune"] == commune_name].copy()
    if not df_c.empty:
        res = []
        for m in range(1, 13):
            df_m = df_c[df_c["mois"] == m]
            if not df_m.empty:
                global_rate = ((df_m["conformite_limites_bact_prelevement"] == "C") & 
                               (df_m["conformite_limites_pc_prelevement"] == "C")).mean() * 100
                res.append({"mois": m, "Type": "Qualité", "Valeur": global_rate})
            else:
                res.append({"mois": m, "Type": "Qualité", "Valeur": None})
        state.commune_trend_data = pd.DataFrame(res)
        state.selected_commune_name = commune_name

def on_month_select(state: State):
    for m, label in MOIS_LABELS.items():
        if label == state.selected_month_label:
            state.selected_month = m
            update_ui(state)
            break

def on_commune_search(state: State):
    if state.search_commune:
        _update_commune_trend(state, state.search_commune)

def on_init(state: State):
    _update_commune_trend(state, state.search_commune)

# --- INTERFACE ---
page = """
<|container|
# 💧 Qualité de l'eau potable — France 2024

<|layout|columns=1 1 1 1|
<|card|
**Départements**
<|{nb_entites}|text|class_name=h3|>
|>
<|card|
**Conformité Moyenne**
<|{conformity_mean}%|text|class_name=h3|>
|>
<|card|
**Zones ≥ 95%**
<|{nb_conformes}|text|class_name=h3 color-success|>
|>
<|card|
**Zones < 95%**
<|{nb_alerte}|text|class_name=h3 color-error|>
|>
|>

<br/>

<|layout|columns=1 1|
<|part|class_name=card p2|
#### 📊 Distribution de la Qualité (<|{selected_month_label}|text|>)
<|{distrib_data}|chart|type=bar|x=Tranche|y=Nombre|height=200px|layout={distrib_layout}|plot_config={no_bar_config}|>
|>

<|part|class_name=card p2|
<|layout|columns=1 1|
#### 📈 <|{selected_commune_name}|text|class_name=dynamic-month|>
<|{search_commune}|selector|lov={all_communes}|on_change=on_commune_search|dropdown=True|label=🔍 Chercher une commune...|class_name=fullwidth|>
|>
<|{commune_trend_data}|chart|type=line|x=mois|y=Valeur|height=200px|layout={trend_layout}|plot_config={no_bar_config}|line_width=3|>
|>
|>

<br/>

<|part|class_name=map-container|
### Qualité par département : <|{selected_month_label + " 2024"}|text|class_name=dynamic-month|>
<|{selected_month_label}|toggle|lov={mois_labels_list}|on_change=on_month_select|class_name=month-selector|>
<br/>
<|part|content={chart_figure}|height=720px|>
|>

<br/>
<|Source : Hub'Eau API (2024) - Données nationales consolidées.|text|class_name=text-muted|>
|>
"""

print("3/3 Lancement du serveur Taipy...", flush=True)
if __name__ == "__main__":
    Gui.register_content_provider(_HtmlChart, lambda c: c.html)
    gui = Gui(page)
    gui.run(
        host="0.0.0.0",
        port=8501,
        title="Qualité de l'eau France 2024",
        dark_mode=True,
        on_init=on_init,
        use_reloader=False, # Désactivé pour stabilité avec pré-rendu lourd
        server_config={"socketio": {"max_http_buffer_size": 15 * 1024 * 1024}},
    )
