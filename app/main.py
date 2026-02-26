"""
Dashboard Taipy — Qualité de l'eau potable en Île-de-France (2024)
Version stable avec interface fixe et données consolidées
"""

import copy
import json
import threading
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from taipy.gui import Gui, State, invoke_callback

DATA_DIR = Path(__file__).parent / "data"

MOIS_LABELS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}

MOIS_COURTS = {
    1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Juil", 8: "Août",
    9: "Sept", 10: "Oct", 11: "Nov", 12: "Déc",
}

COLOR_SCALE = [
    (0.0, "#ff4d4d"), (0.8, "#ffaf40"), (0.95, "#32ff7e"), (1.0, "#18dcff"),
]

def _simplify_geojson(geojson: dict, decimals: int = 3) -> dict:
    def simplify_ring(ring):
        pts = [[round(c, decimals) for c in pt] for pt in ring]
        deduped = [pts[0]]
        for pt in pts[1:]:
            if pt != deduped[-1]:
                deduped.append(pt)
        return deduped

    g = copy.deepcopy(geojson)
    for feat in g["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            geom["coordinates"] = [simplify_ring(r) for r in geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            geom["coordinates"] = [
                [simplify_ring(r) for r in poly] for poly in geom["coordinates"]
            ]
    return g

# --- Chargement des données ---
df_agg = pd.read_parquet(DATA_DIR / "agg_commune_mois.parquet")
df_raw = pd.read_parquet(DATA_DIR / "prelevements_2024.parquet")

# Pré-traitement pour les noms de communes
with open(DATA_DIR / "communes.geojson", encoding="utf-8") as f:
    geojson_raw = json.load(f)
    geojson = _simplify_geojson(geojson_raw, decimals=3)

commune_names = {
    feat["properties"]["code_commune"]: feat["properties"]["nom_commune"]
    for feat in geojson["features"]
}
df_agg["nom_commune"] = df_agg["code_commune"].map(commune_names)
df_raw["nom_commune"] = df_raw["code_commune"].map(commune_names)

mois_disponibles = sorted(df_agg["mois"].unique().tolist())
mois_labels_list = [MOIS_LABELS[m] for m in mois_disponibles]
all_communes = sorted([c for c in df_agg["nom_commune"].unique().tolist() if isinstance(c, str)])

def create_fig(df: pd.DataFrame) -> go.Figure:
    # On s'assure que nom_commune est là pour le survol
    df_plot = df.copy()
    df_plot["nom_commune"] = df_plot["code_commune"].map(commune_names)
    
    fig = px.choropleth_mapbox(
        df_plot,
        geojson=geojson,
        locations="code_commune",
        featureidkey="properties.code_commune",
        color="compliance_rate",
        color_continuous_scale=COLOR_SCALE,
        range_color=[50, 100],
        mapbox_style="carto-darkmatter",
        zoom=9.2,
        center={"lat": 48.75, "lon": 2.45},
        opacity=0.8,
        hover_name="nom_commune",
        hover_data={"code_commune": False, "compliance_rate": ":.1f"}
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        mapbox=dict(pitch=45, bearing=10),
        coloraxis_colorbar=dict(
            title="Qualité %", thickness=15, len=0.4, 
            x=0.02, y=0.05, bgcolor="rgba(15, 23, 42, 0.8)",
            tickfont=dict(color="#e2e8f0")
        )
    )
    return fig

def compute_kpis(df: pd.DataFrame) -> tuple:
    return (
        len(df),
        round(float(df["compliance_rate"].mean()), 1),
        int((df["compliance_rate"] >= 95).sum()),
        int((df["compliance_rate"] < 95).sum()),
    )

class _HtmlChart:
    def __init__(self, html: str):
        self.html = html

# --- État initial ---
charts_cache: dict[int, _HtmlChart] = {}
kpis_cache: dict[int, tuple] = {}

is_ready = False
progress = 0
selected_month = 1
selected_month_label = MOIS_LABELS[1]
chart_figure = _HtmlChart("<div>Chargement...</div>")

# Analyse par commune (bloc permanent)
search_commune = "Paris" # Valeur par défaut
selected_commune_name = "Paris"
commune_trend_data = pd.DataFrame(columns=["mois", "Type", "Valeur"])

# Graphique de gauche (Distribution globale)
distrib_data = pd.DataFrame(columns=["Tranche", "Nombre"])

nb_communes = 0
conformity_mean = 0.0
nb_conformes = 0
nb_alerte = 0

chart_layout = {
    "xaxis": {
        "tickmode": "array", "tickvals": [1,2,3,4,5,6,7,8,9,10,11,12],
        "ticktext": ["Jan", "Fév", "Mar", "Avr", "Mai", "Jui", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"],
        "title": ""
    },
    "yaxis": {"range": [0, 105], "title": ""},
    "margin": {"l": 30, "r": 10, "t": 10, "b": 30},
    "plot_bgcolor": "rgba(0,0,0,0)", "paper_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#e2e8f0", "size": 10},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5, "font": {"size": 9}}
}

# Configuration pour le graphique de distribution (gauche)
distrib_layout = {
    "margin": {"l": 30, "r": 10, "t": 10, "b": 30},
    "font": {"color": "#e2e8f0", "size": 10},
    "yaxis": {"title": ""},
    "xaxis": {"title": ""}
}

no_bar_config = {"displayModeBar": False}

def on_init(state: State):
    global is_ready, progress
    state.is_ready = is_ready
    state.progress = progress
    if is_ready:
        _update_ui_for_month(state, 1)
        _update_commune_trend(state, state.search_commune)

def _update_ui_for_month(state: State, m: int):
    if m in charts_cache:
        state.chart_figure = charts_cache[m]
        state.selected_month_label = MOIS_LABELS[m]
        state.nb_communes, state.conformity_mean, state.nb_conformes, state.nb_alerte = kpis_cache[m]
        
        # Mise à jour de la distribution globale pour le graphique de gauche
        df_m = df_agg[df_agg["mois"] == m]
        bins = [0, 80, 95, 99, 100]
        labels = ["< 80%", "80-95%", "95-99%", "100%"]
        df_m["tranche"] = pd.cut(df_m["compliance_rate"], bins=bins, labels=labels, include_lowest=True)
        dist = df_m["tranche"].value_counts().reindex(labels).reset_index()
        dist.columns = ["Tranche", "Nombre"]
        state.distrib_data = dist

def _update_commune_trend(state: State, commune_name: str):
    df_c = df_raw[df_raw["nom_commune"] == commune_name].copy()
    if not df_c.empty:
        res = []
        for m in range(1, 13):
            df_m = df_c[df_c["mois"] == m]
            if not df_m.empty:
                global_rate = ((df_m["conformite_limites_bact_prelevement"] == "C") & 
                               (df_m["conformite_limites_pc_prelevement"] == "C")).mean() * 100
                bact_rate = (df_m["conformite_limites_bact_prelevement"] == "C").mean() * 100
                pc_rate = (df_m["conformite_limites_pc_prelevement"] == "C").mean() * 100
                res.append({"mois": m, "Type": "Global", "Valeur": global_rate})
                res.append({"mois": m, "Type": "Bactério", "Valeur": bact_rate})
                res.append({"mois": m, "Type": "Chimique", "Valeur": pc_rate})
            else:
                res.append({"mois": m, "Type": "Global", "Valeur": None})
        state.commune_trend_data = pd.DataFrame(res)
        state.selected_commune_name = commune_name

def on_month_select(state: State):
    for m, label in MOIS_LABELS.items():
        if label == state.selected_month_label:
            _update_ui_for_month(state, m)
            break

def on_commune_search(state: State):
    if state.search_commune:
        _update_commune_trend(state, state.search_commune)

def background_load(gui: Gui):
    global is_ready, progress, charts_cache, kpis_cache
    for i, m in enumerate(mois_disponibles):
        df_m = df_agg[df_agg["mois"] == m].copy()
        df_m["nom_commune"] = df_m["code_commune"].map(commune_names)
        fig = create_fig(df_m)
        charts_cache[m] = _HtmlChart(fig.to_html(include_plotlyjs="cdn", full_html=True, config={"displayModeBar": False, "displaylogo": False}))
        kpis_cache[m] = compute_kpis(df_m)
        progress = int(((i+1)/len(mois_disponibles))*100)
        gui.broadcast_callback(lambda s, p: s.assign("progress", p), [progress])
    
    is_ready = True
    gui.broadcast_callback(lambda s: s.assign("is_ready", True), [])
    gui.broadcast_callback(on_init, [])

page = """
<|container|
<|{not is_ready}|part|render={not is_ready}|class_name=text-center p3|
<br/><br/><br/>
# 💧 Qualité de l'eau IDF
### Analyse des données consolidées 2024...
<|{progress}|progress|>
|>

<|{is_ready}|part|render={is_ready}|
# 💧 Qualité de l'eau potable — Île-de-France 2024

<|layout|columns=1 1 1 1|
<|card|
**Communes**
<|{nb_communes}|text|class_name=h3|>
|>
<|card|
**Conformité**
<|{conformity_mean}%|text|class_name=h3|>
|>
<|card|
**Conformes**
<|{nb_conformes}|text|class_name=h3 color-success|>
|>
<|card|
**Alertes**
<|{nb_alerte}|text|class_name=h3 color-error|>
|>
|>

<br/>

<|layout|columns=1 1|
<|part|class_name=card p2|
#### 📊 État global (<|{selected_month_label}|text|>)
<|{distrib_data}|chart|type=bar|x=Tranche|y=Nombre|height=250px|plot_config={no_bar_config}|layout={distrib_layout}|>
<|part|class_name=text-muted|Répartition des communes par taux de conformité.|>
|>

<|part|class_name=card p2|
<|layout|columns=1 1|
#### 📈 <|{selected_commune_name}|text|class_name=dynamic-month|>
<|{search_commune}|selector|lov={all_communes}|on_change=on_commune_search|dropdown=True|label=🔍 Chercher...|class_name=fullwidth|>
|>
<|{commune_trend_data}|chart|type=line|x=mois|y=Valeur|color=Type|height=250px|layout={chart_layout}|plot_config={no_bar_config}|line_width=2|>
<|part|class_name=text-muted|Évolution mensuelle de la conformité (2024).|>
|>
|>

<br/>

<|part|class_name=map-container|
### Qualité de l'eau en : <|{selected_month_label + " 2024"}|text|class_name=dynamic-month|>

<|{selected_month_label}|toggle|lov={mois_labels_list}|on_change=on_month_select|class_name=month-selector|>

<br/>

<|part|content={chart_figure}|height=720px|>

<br/>

<|part|
**Légende :** &nbsp; 
🔴 < 80% &nbsp; 🟠 80-95% &nbsp; 🟢 95-99% &nbsp; 🔵 100%
|>

<br/>

<|part|class_name=text-muted|
*Source : Hub'Eau API (2024) · Données consolidées. Cherchez une commune pour voir son historique.*
|>
|>

|>
|>
"""

if __name__ == "__main__":
    Gui.register_content_provider(_HtmlChart, lambda c: c.html)
    gui = Gui(page)
    threading.Thread(target=background_load, args=(gui,), daemon=True).start()
    gui.run(
        host="0.0.0.0",
        port=8501,
        title="Qualité de l'eau IDF 2024",
        dark_mode=True,
        on_init=on_init,
        use_reloader=True,
        server_config={"socketio": {"max_http_buffer_size": 15 * 1024 * 1024}},
    )
