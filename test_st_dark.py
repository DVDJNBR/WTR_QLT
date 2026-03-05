import streamlit as st

st.set_page_config(page_title="Qualité de l'eau France 2024", layout="wide", page_icon="💧")

_CSS_COMMON = """
    /* Largeur max */
    .block-container { max-width: 1200px !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    /* Pills pleine largeur — role=radio est l'attribut réel des boutons pills Streamlit */
    .stPills { width: 100% !important; }
    .stPills > div { display: flex !important; flex-wrap: wrap !important; width: 100% !important; gap: 6px !important; }
    button[role="radio"] { flex: 1 1 auto !important; justify-content: center !important; }
"""

st.markdown(f"""
    <style>
    {_CSS_COMMON}
    /* Fond global + header */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main,
    header[data-testid="stHeader"], [data-testid="stToolbar"] {{
        background-color: #0b0d11 !important; color: #e2e8f0 !important;
    }}
    .stMetric {{ background-color: #151921; border: 1px solid #232a35; padding: 15px; border-radius: 12px; }}
    /* BaseUI widgets (selectbox, input) */
    [data-baseweb="select"] > div, [data-baseweb="input"] > div,
    [data-baseweb="base-input"], [data-baseweb="textarea"] {{
        background-color: #151921 !important; color: #e2e8f0 !important; border-color: #232a35 !important;
    }}
    [data-baseweb="menu"], [data-baseweb="popover"] > div {{
        background-color: #151921 !important; color: #e2e8f0 !important;
    }}
    [data-baseweb="menu"] li:hover {{ background-color: #232a35 !important; }}
    /* Pills (role=radio) dark */
    button[role="radio"] {{
        background-color: #1e2530 !important; color: #e2e8f0 !important; border-color: #232a35 !important;
    }}
    button[role="radio"][aria-checked="true"] {{
        background-color: #3b82f6 !important; color: #ffffff !important;
    }}
    /* st.button (retour, etc.) dark */
    .stButton > button {{
        background-color: #1e2530 !important; color: #e2e8f0 !important; border-color: #232a35 !important;
    }}
    .stButton > button:disabled {{
        background-color: #13181f !important; color: #4a5568 !important;
    }}
    label, p, h1, h2, h3, .stMarkdown, .stCaption {{ color: #e2e8f0 !important; }}
    </style>
""", unsafe_allow_html=True)

st.pills("Mois", options=["Jan", "Feb"], default="Jan")
