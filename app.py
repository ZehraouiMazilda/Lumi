import streamlit as st

st.set_page_config(
    page_title="Lumi",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg:        #1a1225;
    --bg2:       #221830;
    --surface:   #2d2040;
    --surface2:  #382850;
    --border:    #4a3560;
    --purple:    #9b6dff;
    --purple2:   #7c4fe0;
    --purple3:   #b89aff;
    --purple4:   #f0eaff;
    --text:      #f0eaff;
    --muted:     #a896c8;
    --muted2:    #7a6a9a;
    --radius:    16px;
    --shadow:    0 4px 24px rgba(155,109,255,0.12);
    --shadow-lg: 0 12px 48px rgba(155,109,255,0.22);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    font-family: 'Outfit', sans-serif;
    color: var(--text);
    font-size: 17px;
}
[data-testid="stAppViewContainer"] > .main { background: var(--bg) !important; }
[data-testid="stSidebar"]  { display: none !important; }
#MainMenu, footer, header  { visibility: hidden !important; }
[data-testid="stToolbar"]  { display: none !important; }
.block-container { padding: 1rem 2rem !important; max-width: 100% !important; }

/* ── Animations ── */
@keyframes fadeUp {
    from { opacity:0; transform:translateY(20px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes glow {
    0%,100% { box-shadow: 0 0 20px rgba(155,109,255,0.3); }
    50%      { box-shadow: 0 0 40px rgba(155,109,255,0.6); }
}
@keyframes float {
    0%,100% { transform: translateY(0px); }
    50%      { transform: translateY(-8px); }
}
.anim-1 { animation: fadeUp 0.5s 0.0s ease both; }
.anim-2 { animation: fadeUp 0.5s 0.1s ease both; }
.anim-3 { animation: fadeUp 0.5s 0.2s ease both; }
.anim-4 { animation: fadeUp 0.5s 0.3s ease both; }
.anim-5 { animation: fadeUp 0.5s 0.4s ease both; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--purple), var(--purple2)) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.7rem 1.8rem !important;
    box-shadow: 0 4px 20px rgba(155,109,255,0.35) !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(155,109,255,0.5) !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 1rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--purple) !important;
    box-shadow: 0 0 0 3px rgba(155,109,255,0.2) !important;
}
.stTextInput label, .stTextArea label {
    color: var(--muted) !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    border: 1.5px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    border-radius: 9px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--purple), var(--purple2)) !important;
    color: white !important;
}

/* ── Cards ── */
.card {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 1.6rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}
.card-glow {
    background: var(--surface);
    border: 1.5px solid var(--purple);
    border-radius: var(--radius);
    padding: 1.6rem;
    box-shadow: var(--shadow-lg);
    margin-bottom: 1rem;
    animation: glow 3s ease-in-out infinite;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1.2rem 0 !important; }

/* ── Alerts ── */
.stAlert { border-radius: 12px !important; font-size: 1rem !important; }

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}
[data-testid="metric-container"] label {
    color: var(--muted) !important;
    font-size: 0.82rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--purple3) !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session defaults ───────────────────────────────────────────
for k, v in {"page": "home", "user": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Routing ───────────────────────────────────────────────────
page = st.session_state.page

# Conteneur unique par page force le re-render complet
st.markdown(f'<div id="page-{page}"></div>', unsafe_allow_html=True)

if page == "home":
    from views.home import show; show()
elif page == "session":
    from views.session import show; show()
elif page == "analytics":
    from views.analytics import show; show()
elif page == "auth":
    from views.auth import show; show()