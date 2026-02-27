"""
Dashboard Streamlit — Qualité de l'eau potable en France (2024)
Version interactive avec Drill-down (France -> Départements)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path

# --- Configuration ---
st.set_page_config(page_title="Qualité de l'eau France 2024", layout="wide", page_icon="💧")

st.markdown("""
    <style>
    .main { background-color: #0b0d11; color: #e2e8f0; }
    .stMetric { background-color: #151921; border: 1px solid #232a35; padding: 15px; border-radius: 12px; }
    div[data-testid="stExpander"] { background-color: #151921; border: 1px solid #232a35; border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

DATA_DIR = Path(__file__).parent / "data"

MOIS_LABELS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}

COLOR_SCALE = [
    (0.0, "#ff4d4d"), (0.8, "#ffaf40"), (0.95, "#32ff7e"), (1.0, "#18dcff"),
]

# --- Chargement des données ---
@st.cache_data
def load_data():
    df_agg_commune = pd.read_parquet(DATA_DIR / "agg_commune_mois.parquet")
    df_agg_dept = pd.read_parquet(DATA_DIR / "agg_dept_mois.parquet")
    df_raw = pd.read_parquet(DATA_DIR / "prelevements_2024.parquet")

    with open(DATA_DIR / "departements.geojson", encoding="utf-8") as f:
        geojson_dept = json.load(f)
    with open(DATA_DIR / "communes_france.geojson", encoding="utf-8") as f:
        geojson_commune_all = json.load(f)

    dept_names = {f["properties"]["code"]: f["properties"]["nom"] for f in geojson_dept["features"]}
    commune_names = {f["properties"]["code"]: f["properties"]["nom"] for f in geojson_commune_all["features"]}

    df_agg_dept["nom_dept"] = df_agg_dept["code_departement"].map(dept_names)
    df_agg_commune["nom_commune"] = df_agg_commune["code_commune"].map(commune_names)

    return df_agg_commune, df_agg_dept, df_raw, geojson_dept, geojson_commune_all, dept_names, commune_names

df_agg_commune, df_agg_dept, df_raw, geojson_dept, geojson_commune_all, dept_names, commune_names = load_data()

# --- État de navigation ---
if "view_level" not in st.session_state:
    st.session_state.view_level = "National"
if "selected_dept_code" not in st.session_state:
    st.session_state.selected_dept_code = None
if "selected_month_label" not in st.session_state:
    st.session_state.selected_month_label = "Janvier"

def reset_view():
    st.session_state.view_level = "National"
    st.session_state.selected_dept_code = None

# Mois courant (valeur du run précédent, mise à jour par les pills après les KPIs)
selected_month_label = st.session_state["selected_month_label"] or "Janvier"
selected_month = [k for k, v in MOIS_LABELS.items() if v == selected_month_label][0]

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

# --- KPIs ---
if st.session_state.view_level == "National":
    df_m = df_agg_dept[df_agg_dept["mois"] == selected_month]
else:
    df_m = df_agg_commune[
        (df_agg_commune["mois"] == selected_month) &
        (df_agg_commune["code_departement"] == st.session_state.selected_dept_code)
    ]

nb_entites = len(df_m)
mean_rate = df_m["compliance_rate"].mean() if not df_m.empty else 0
nb_conformes = len(df_m[df_m["compliance_rate"] >= 95])
nb_alertes = len(df_m[df_m["compliance_rate"] < 95])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Zones", f"{nb_entites}")
c2.metric("Conformité moyenne", f"{mean_rate:.1f}%")

with c3:
    st.markdown(f"""
        <div style="background:#151921;border:1px solid #1a3a2a;padding:15px;border-radius:12px">
            <div style="font-size:0.8rem;color:#a0aec0;margin-bottom:4px">Conformes (≥95%)</div>
            <div style="font-size:1.8rem;font-weight:700;color:#32ff7e">{nb_conformes}</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
        <div style="background:#151921;border:1px solid #3a1a1a;padding:15px;border-radius:12px">
            <div style="font-size:0.8rem;color:#a0aec0;margin-bottom:4px">Alertes (&lt;95%)</div>
            <div style="font-size:1.8rem;font-weight:700;color:#ff4d4d">{nb_alertes}</div>
        </div>
    """, unsafe_allow_html=True)

# --- Sélecteur de mois (boutons, sous les KPIs) ---
st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
new_month_label = st.pills(
    "Mois",
    options=list(MOIS_LABELS.values()),
    default=selected_month_label,
    key="selected_month_label",
    label_visibility="collapsed",
)

st.divider()

# --- Main Layout ---
col_map, col_stats = st.columns([2, 1])

with col_map:
    if st.session_state.view_level == "National":
        fig = px.choropleth_mapbox(
            df_m,
            geojson=geojson_dept,
            locations="code_departement",
            featureidkey="properties.code",
            color="compliance_rate",
            color_continuous_scale=COLOR_SCALE,
            range_color=[70, 100],
            mapbox_style="carto-darkmatter",
            zoom=4.8,
            center={"lat": 46.5, "lon": 2.5},
            opacity=0.8,
            hover_name="nom_dept",
            template="plotly_dark",
        )
    else:
        features = [
            f for f in geojson_commune_all["features"]
            if f["properties"]["code"].startswith(st.session_state.selected_dept_code)
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
        if all_coords:
            center_lon = sum(c[0] for c in all_coords) / len(all_coords)
            center_lat = sum(c[1] for c in all_coords) / len(all_coords)
        else:
            center_lon, center_lat = 2.5, 46.5

        fig = px.choropleth_mapbox(
            df_m,
            geojson=geo_local,
            locations="code_commune",
            featureidkey="properties.code",
            color="compliance_rate",
            color_continuous_scale=COLOR_SCALE,
            range_color=[70, 100],
            mapbox_style="carto-darkmatter",
            zoom=7.5,
            center={"lat": center_lat, "lon": center_lon},
            opacity=0.8,
            hover_name="nom_commune",
            template="plotly_dark",
        )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        clickmode="event+select",
        mapbox=dict(pitch=40 if st.session_state.view_level == "National" else 0),
        coloraxis_colorbar=dict(title="%", thickness=15, len=0.5, x=0.02, y=0.05),
    )

    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="main_map")

    if st.session_state.view_level == "National" and event:
        points = event.get("selection", {}).get("points", [])
        if points:
            dept_code = points[0].get("location")
            if dept_code:
                st.session_state.selected_dept_code = dept_code
                st.session_state.view_level = "Department"
                st.rerun()

with col_stats:
    # --- Distribution ---
    st.subheader("Distribution")
    bins = [0, 80, 95, 99, 100]
    labels = ["< 80%", "80-95%", "95-99%", "100%"]
    df_plot = df_m.copy()
    df_plot["tranche"] = pd.cut(df_plot["compliance_rate"], bins=bins, labels=labels, include_lowest=True)
    dist = df_plot["tranche"].value_counts().reindex(labels).reset_index()
    dist.columns = ["Tranche", "Nombre"]

    fig_dist = px.bar(
        dist, x="Tranche", y="Nombre", template="plotly_dark", color="Tranche",
        color_discrete_map={"< 80%": "#ff4d4d", "80-95%": "#ffaf40", "95-99%": "#32ff7e", "100%": "#18dcff"},
    )
    fig_dist.update_layout(
        showlegend=False, height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    # --- Recherche ---
    st.subheader("Recherche")

    # Par département
    sorted_depts = sorted(dept_names.items(), key=lambda x: x[1])
    dept_options = {"": ""} | {code: nom for code, nom in sorted_depts}
    search_dept = st.selectbox(
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
    all_communes = sorted(commune_names.values())
    search_commune = st.selectbox("Par commune", options=[""] + all_communes, index=0)

    if search_commune:
        df_c = df_raw[df_raw["nom_commune"] == search_commune].copy()
        if not df_c.empty:
            res = []
            for m in range(1, 13):
                df_mo = df_c[df_c["mois"] == m]
                val = (
                    ((df_mo["conformite_limites_bact_prelevement"] == "C") &
                     (df_mo["conformite_limites_pc_prelevement"] == "C")).mean() * 100
                    if not df_mo.empty else None
                )
                res.append({"Mois": MOIS_LABELS[m][:3], "Conformité": val})

            df_trend = pd.DataFrame(res)
            fig_trend = px.line(df_trend, x="Mois", y="Conformité", markers=True, template="plotly_dark", range_y=[0, 105])
            fig_trend.update_layout(
                height=250, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            fig_trend.update_traces(line_color="#60a5fa")
            st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

st.caption("Source : Hub'Eau API (2024). Cliquez sur un département pour zoomer.")
