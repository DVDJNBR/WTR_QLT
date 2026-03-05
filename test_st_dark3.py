import streamlit as st

st.set_page_config(page_title="Qualité de l'eau France 2024", layout="wide", page_icon="💧")

_CSS_COMMON = """
    /* Largeur max */
    .block-container { max-width: 1200px !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    /* Pills pleine largeur — role=radio est l'attribut réel des boutons pills Streamlit */
    div[data-testid="stButtonGroup"] { width: 100% !important; display: flex !important; justify-content: center !important; }
    div[data-testid="stButtonGroup"] > div { display: flex !important; flex-wrap: wrap !important; width: 100% !important; gap: 6px !important; justify-content: center !important; }
    button[data-testid="stBaseButton-pills"], button[data-testid="stBaseButton-pillsActive"] { flex: 1 1 auto !important; justify-content: center !important; }
"""

st.markdown(f"""
    <style>
    {_CSS_COMMON}
    /* Fond global + header */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main,
    header[data-testid="stHeader"], [data-testid="stToolbar"] {{
        background-color: #0b0d11 !important; color: #e2e8f0 !important;
    }}
    /* Pills dark */
    button[data-testid="stBaseButton-pills"] {{
        background-color: #1e2530 !important; color: #e2e8f0 !important; border-color: #232a35 !important;
    }}
    button[data-testid="stBaseButton-pillsActive"] {{
        background-color: #3b82f6 !important; color: #ffffff !important; border-color: #3b82f6 !important;
    }}
    /* On hover un peu de couleur si on veut */
    button[data-testid="stBaseButton-pills"]:hover {{
        background-color: #232a35 !important;
    }}
    /* label, p, h1, h2, h3, .stMarkdown, .stCaption {{ color: #e2e8f0 !important; }} */

    div[data-testid="stMarkdownContainer"] p {{ color: inherit !important; }}
    </style>
""", unsafe_allow_html=True)

st.pills("Mois", options=["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"], default="Janvier")
