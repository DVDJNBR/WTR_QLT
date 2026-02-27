"""
Dashboard Streamlit — Qualité de l'eau potable en France (2024)
Carte pleine largeur avec insets DOM-TOM (Option B) + drill-down départements
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from pathlib import Path

# --- Configuration ---
st.set_page_config(page_title="Qualité de l'eau France 2024", layout="wide", page_icon="💧")

st.markdown("""
    <style>
    .main { background-color: #0b0d11; color: #e2e8f0; }
    .stMetric { background-color: #151921; border: 1px solid #232a35; padding: 15px; border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

DATA_DIR = Path(__file__).parent / "data"

# Téléchargement automatique du GeoJSON DOM-TOM si absent
_DOMTOM_PATH = DATA_DIR / "departements_domtom.geojson"
if not _DOMTOM_PATH.exists():
    import urllib.request
    _URL = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-avec-outre-mer.geojson"
    with urllib.request.urlopen(_URL, timeout=30) as r:
        _data = json.load(r)
    _data["features"] = [f for f in _data["features"] if f["properties"]["code"] in {"971","972","973","974","976"}]
    with open(_DOMTOM_PATH, "w", encoding="utf-8") as f:
        json.dump(_data, f, ensure_ascii=False)

MOIS_LABELS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}

# Colorscale partagée (format go.Figure)
COLOR_SCALE = [[0.0, "#ff4d4d"], [0.8, "#ffaf40"], [0.95, "#32ff7e"], [1.0, "#18dcff"]]

# Config insets DOM-TOM : (code, nom, lat, lon, zoom, x_domain)
DOM_TOM_CONFIG = [
    ("971", "Guadeloupe",  16.17, -61.57,  7.5, [0.00, 0.185]),
    ("972", "Martinique",  14.67, -61.00,  8.5, [0.20, 0.385]),
    ("973", "Guyane",       4.00, -53.00,  4.5, [0.40, 0.585]),
    ("974", "La Réunion", -21.10,  55.50,  8.5, [0.60, 0.785]),
    ("976", "Mayotte",    -12.80,  45.15,  9.5, [0.80, 0.985]),
]
DOMTOM_CODES = {c[0] for c in DOM_TOM_CONFIG}

# --- Chargement des données ---
@st.cache_data
def load_data():
    df_agg_commune = pd.read_parquet(DATA_DIR / "agg_commune_mois.parquet")
    df_agg_dept    = pd.read_parquet(DATA_DIR / "agg_dept_mois.parquet")
    df_raw         = pd.read_parquet(DATA_DIR / "prelevements_2024.parquet")

    with open(DATA_DIR / "departements.geojson", encoding="utf-8") as f:
        geojson_dept = json.load(f)
    with open(DATA_DIR / "communes_france.geojson", encoding="utf-8") as f:
        geojson_commune_all = json.load(f)
    with open(DATA_DIR / "departements_domtom.geojson", encoding="utf-8") as f:
        geojson_domtom = json.load(f)

    dept_names    = {f["properties"]["code"]: f["properties"]["nom"] for f in geojson_dept["features"]}
    domtom_names  = {f["properties"]["code"]: f["properties"]["nom"] for f in geojson_domtom["features"]}
    dept_names.update(domtom_names)
    commune_names = {f["properties"]["code"]: f["properties"]["nom"] for f in geojson_commune_all["features"]}

    df_agg_dept["nom_dept"]       = df_agg_dept["code_departement"].map(dept_names)
    df_agg_commune["nom_commune"] = df_agg_commune["code_commune"].map(commune_names)

    return (df_agg_commune, df_agg_dept, df_raw,
            geojson_dept, geojson_commune_all, geojson_domtom,
            dept_names, commune_names)

(df_agg_commune, df_agg_dept, df_raw,
 geojson_dept, geojson_commune_all, geojson_domtom,
 dept_names, commune_names) = load_data()

# --- Session state ---
if "view_level"           not in st.session_state: st.session_state.view_level           = "National"
if "selected_dept_code"   not in st.session_state: st.session_state.selected_dept_code   = None
if "selected_month_label" not in st.session_state: st.session_state.selected_month_label = "Janvier"

def reset_view():
    st.session_state.view_level         = "National"
    st.session_state.selected_dept_code = None

# Mois courant (session state, mis à jour par les pills après les KPIs)
selected_month_label = st.session_state["selected_month_label"] or "Janvier"
selected_month = next(k for k, v in MOIS_LABELS.items() if v == selected_month_label)

# --- Header ---
col_title, col_btn = st.columns([4, 1])
with col_title:
    if st.session_state.view_level == "National":
        st.title("Qualité de l'eau — France 2024")
    else:
        name = dept_names.get(st.session_state.selected_dept_code, "Département")
        st.title(f"Qualité de l'eau — {name} 2024")
with col_btn:
    if st.session_state.view_level == "Department":
        st.button("Retour France", on_click=reset_view)

# --- Données du mois courant ---
dept_code = st.session_state.selected_dept_code
is_domtom = dept_code in DOMTOM_CODES

if st.session_state.view_level == "National":
    df_m = df_agg_dept[df_agg_dept["mois"] == selected_month]
else:
    df_m = df_agg_commune[
        (df_agg_commune["mois"] == selected_month) &
        (df_agg_commune["code_departement"] == dept_code)
    ]

# --- KPIs : 2 métriques + 3 blocs colorés ---
nb_zones    = len(df_m)
mean_rate   = df_m["compliance_rate"].mean() if not df_m.empty else 0
nb_conforme  = len(df_m[df_m["compliance_rate"] >= 95])
nb_vigilance = len(df_m[(df_m["compliance_rate"] >= 80) & (df_m["compliance_rate"] < 95)])
nb_alerte    = len(df_m[df_m["compliance_rate"] < 80])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Zones", f"{nb_zones}")
c2.metric("Conformité", f"{mean_rate:.1f}%")

KPI_CARDS = [
    (c3, "Conforme ≥95%",   nb_conforme,  "#0a1f14", "#1e4030", "#32ff7e"),
    (c4, "Vigilance 80–95%", nb_vigilance, "#1a1500", "#3a3000", "#ffaf40"),
    (c5, "Alerte &lt;80%",  nb_alerte,    "#1a0808", "#3a1515", "#ff4d4d"),
]
for col, label, count, bg, border, color in KPI_CARDS:
    with col:
        st.markdown(f"""
            <div style="background:{bg};border:1px solid {border};padding:15px;border-radius:12px">
                <div style="font-size:0.8rem;color:#a0aec0;margin-bottom:6px">{label}</div>
                <div style="font-size:2rem;font-weight:700;color:{color};line-height:1">{count}</div>
            </div>
        """, unsafe_allow_html=True)

# --- Sélecteur de mois (pills, sous les KPIs) ---
st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
st.pills(
    "Mois", options=list(MOIS_LABELS.values()),
    default=selected_month_label,
    key="selected_month_label",
    label_visibility="collapsed",
)

st.divider()

# ============================================================
# CARTE PLEINE LARGEUR
# ============================================================

def coloraxis_config():
    return dict(
        colorscale=COLOR_SCALE, cmin=70, cmax=100,
        colorbar=dict(
            title=dict(text="%", font=dict(size=11)),
            thickness=12, len=0.35, x=0.005, y=0.65, yanchor="middle",
        ),
    )

def common_mapbox_layout():
    return dict(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        clickmode="event+select",
        showlegend=False,
    )

if st.session_state.view_level == "National":
    # ── Carte nationale : métropole + 5 insets DOM-TOM ──────────────────
    fig = go.Figure()

    df_metro = df_m[~df_m["code_departement"].isin(DOMTOM_CODES)]

    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson_dept,
        locations=df_metro["code_departement"],
        z=df_metro["compliance_rate"],
        featureidkey="properties.code",
        coloraxis="coloraxis",
        text=df_metro["nom_dept"],
        hovertemplate="<b>%{text}</b><br>Conformité : %{z:.1f}%<extra></extra>",
        marker_opacity=0.8,
        marker_line_width=0.5,
        marker_line_color="#1e2530",
        subplot="mapbox",
    ))

    for i, (code, name, lat, lon, zoom, x_dom) in enumerate(DOM_TOM_CONFIG):
        feat = [f for f in geojson_domtom["features"] if f["properties"]["code"] == code]
        if not feat:
            continue
        geo  = {"type": "FeatureCollection", "features": feat}
        df_t = df_m[df_m["code_departement"] == code]
        locs  = df_t["code_departement"] if not df_t.empty else pd.Series(dtype=str)
        zvals = df_t["compliance_rate"]   if not df_t.empty else pd.Series(dtype=float)
        texts = [name] * len(df_t)        if not df_t.empty else []

        fig.add_trace(go.Choroplethmapbox(
            geojson=geo, locations=locs, z=zvals,
            featureidkey="properties.code",
            coloraxis="coloraxis",
            text=texts,
            hovertemplate="<b>%{text}</b><br>Conformité : %{z:.1f}%<extra></extra>",
            marker_opacity=0.8,
            marker_line_width=0.5,
            marker_line_color="#1e2530",
            subplot=f"mapbox{i+2}",
        ))
        fig.update_layout(**{f"mapbox{i+2}": dict(
            style="carto-darkmatter",
            center={"lat": lat, "lon": lon},
            zoom=zoom,
            domain={"x": x_dom, "y": [0.01, 0.22]},
        )})

    # Étiquettes des insets
    label_x = [0.093, 0.293, 0.493, 0.693, 0.893]
    for (code, name, *_), x_c in zip(DOM_TOM_CONFIG, label_x):
        fig.add_annotation(
            text=name, x=x_c, y=0.235,
            xref="paper", yref="paper",
            showarrow=False, font=dict(size=9, color="#718096"),
            xanchor="center",
        )

    fig.update_layout(
        **common_mapbox_layout(),
        mapbox=dict(
            style="carto-darkmatter",
            center={"lat": 46.5, "lon": 2.5},
            zoom=4.8, pitch=40,
            domain={"x": [0, 1], "y": [0.25, 1.0]},
        ),
        coloraxis=coloraxis_config(),
        height=680,
    )

    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="main_map")

    if event:
        points = event.get("selection", {}).get("points", [])
        if points:
            clicked = points[0].get("location")
            if clicked:
                st.session_state.selected_dept_code = clicked
                st.session_state.view_level = "Department"
                st.rerun()

else:
    # ── Drill-down département ───────────────────────────────────────────
    if is_domtom:
        # Pas de GeoJSON communes pour DOM-TOM → affichage département
        dt_map = {c: (lat, lon, zoom) for c, _, lat, lon, zoom, _ in DOM_TOM_CONFIG}
        lat, lon, zoom = dt_map[dept_code]
        feat = [f for f in geojson_domtom["features"] if f["properties"]["code"] == dept_code]
        geo  = {"type": "FeatureCollection", "features": feat}
        df_d = df_agg_dept[(df_agg_dept["mois"] == selected_month) &
                           (df_agg_dept["code_departement"] == dept_code)]

        fig = go.Figure(go.Choroplethmapbox(
            geojson=geo,
            locations=df_d["code_departement"] if not df_d.empty else pd.Series(dtype=str),
            z=df_d["compliance_rate"]           if not df_d.empty else pd.Series(dtype=float),
            featureidkey="properties.code",
            coloraxis="coloraxis",
            text=df_d["nom_dept"] if not df_d.empty else [],
            hovertemplate="<b>%{text}</b><br>Conformité : %{z:.1f}%<extra></extra>",
            marker_opacity=0.8,
        ))
        fig.update_layout(
            **common_mapbox_layout(),
            mapbox=dict(style="carto-darkmatter", center={"lat": lat, "lon": lon}, zoom=zoom),
            coloraxis=coloraxis_config(),
            height=580,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="dept_map")
        st.caption("Données cartographiques communes non disponibles pour ce territoire — affichage au niveau départemental.")

    else:
        # Métropole : commune-level
        features = [
            f for f in geojson_commune_all["features"]
            if f["properties"]["code"].startswith(dept_code)
        ]
        geo_local = {"type": "FeatureCollection", "features": features}

        all_coords = []
        for feat in features:
            geom = feat["geometry"]
            if geom is None:
                continue
            if geom["type"] == "Polygon":
                all_coords.extend(geom["coordinates"][0])
            elif geom["type"] == "MultiPolygon":
                for poly in geom["coordinates"]:
                    all_coords.extend(poly[0])
        center_lon = sum(c[0] for c in all_coords) / len(all_coords) if all_coords else 2.5
        center_lat = sum(c[1] for c in all_coords) / len(all_coords) if all_coords else 46.5

        fig = go.Figure(go.Choroplethmapbox(
            geojson=geo_local,
            locations=df_m["code_commune"],
            z=df_m["compliance_rate"],
            featureidkey="properties.code",
            coloraxis="coloraxis",
            text=df_m["nom_commune"],
            hovertemplate="<b>%{text}</b><br>Conformité : %{z:.1f}%<extra></extra>",
            marker_opacity=0.8,
            marker_line_width=0.3,
            marker_line_color="#1e2530",
        ))
        fig.update_layout(
            **common_mapbox_layout(),
            mapbox=dict(style="carto-darkmatter",
                        center={"lat": center_lat, "lon": center_lon}, zoom=7.5),
            coloraxis=coloraxis_config(),
            height=580,
        )
        st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="dept_map")

st.divider()

# ============================================================
# PANNEAU BAS : Distribution + Recherche
# ============================================================
col_dist, col_search = st.columns([1, 1])

with col_dist:
    st.subheader("Distribution")
    bins   = [0, 80, 95, 99, 100]
    labels = ["< 80%", "80-95%", "95-99%", "100%"]
    df_plot = df_m.copy()
    df_plot["tranche"] = pd.cut(df_plot["compliance_rate"], bins=bins, labels=labels, include_lowest=True)
    dist = df_plot["tranche"].value_counts().reindex(labels).reset_index()
    dist.columns = ["Tranche", "Nombre"]

    fig_dist = go.Figure(go.Bar(
        x=dist["Tranche"], y=dist["Nombre"],
        marker_color=["#ff4d4d", "#ffaf40", "#32ff7e", "#18dcff"],
    ))
    fig_dist.update_layout(
        template="plotly_dark", showlegend=False, height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

with col_search:
    st.subheader("Recherche")

    # Par département
    sorted_depts  = sorted(dept_names.items(), key=lambda x: x[1])
    dept_options  = {"": ""} | {code: nom for code, nom in sorted_depts}
    search_dept   = st.selectbox(
        "Par département",
        options=list(dept_options.keys()),
        format_func=lambda c: dept_options[c],
        index=0,
    )
    if search_dept and search_dept != st.session_state.get("selected_dept_code"):
        st.session_state.selected_dept_code = search_dept
        st.session_state.view_level = "Department"
        st.rerun()

    # Par commune
    all_communes  = sorted(commune_names.values())
    search_commune = st.selectbox("Par commune", options=[""] + all_communes, index=0)

    if search_commune:
        df_c = df_raw[df_raw["nom_commune"] == search_commune].copy()
        if not df_c.empty:
            res = []
            for m in range(1, 13):
                df_mo = df_c[df_c["mois"] == m]
                val = (
                    ((df_mo["conformite_limites_bact_prelevement"] == "C") &
                     (df_mo["conformite_limites_pc_prelevement"]   == "C")).mean() * 100
                    if not df_mo.empty else None
                )
                res.append({"Mois": MOIS_LABELS[m][:3], "Conformité": val})

            df_trend = pd.DataFrame(res)
            fig_trend = go.Figure(go.Scatter(
                x=df_trend["Mois"], y=df_trend["Conformité"],
                mode="lines+markers", line=dict(color="#60a5fa", width=2),
                marker=dict(size=6),
            ))
            fig_trend.update_layout(
                template="plotly_dark", height=230,
                yaxis=dict(range=[0, 105]),
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

st.caption("Source : Hub'Eau API (2024). Cliquez sur un département pour zoomer.")
