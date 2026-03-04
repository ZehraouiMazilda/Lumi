import streamlit as st

st.set_page_config(
    page_title="MeetingAI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS global ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg:        #0a0d14;
    --surface:   #111520;
    --surface2:  #171c2e;
    --border:    #1e2540;
    --accent:    #4f6ef7;
    --accent2:   #7c3aed;
    --green:     #22d3a0;
    --orange:    #f59e0b;
    --red:       #ef4444;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --radius:    14px;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}

[data-testid="stAppViewContainer"] > .main {
    background: var(--bg) !important;
}

[data-testid="stSidebar"] { display: none !important; }

/* Hide Streamlit default elements */
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(79, 110, 247, 0.35) !important;
}

/* Cards */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.8rem;
}

/* Metric */
.metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1;
}
.metric-label {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 0.2rem;
}

/* Progress bar */
.prog-bar-bg {
    background: var(--border);
    border-radius: 99px;
    height: 8px;
    margin-top: 0.6rem;
    overflow: hidden;
}
.prog-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width 0.5s ease;
}

/* Subtitle area */
.subtitle-box {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.2rem;
    min-height: 120px;
    max-height: 200px;
    overflow-y: auto;
    font-size: 0.95rem;
    line-height: 1.7;
}
.subtitle-line {
    padding: 0.2rem 0;
    border-bottom: 1px solid var(--border);
    color: var(--text);
}
.subtitle-line:last-child { border-bottom: none; color: #fff; }

/* Speaker pill */
.speaker-pill {
    display: inline-block;
    background: rgba(79,110,247,0.15);
    border: 1px solid rgba(79,110,247,0.3);
    border-radius: 99px;
    padding: 0.15rem 0.7rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--accent);
    margin-right: 0.5rem;
    font-family: 'Syne', sans-serif;
}

/* Status dot */
.dot-live {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--red);
    border-radius: 50%;
    animation: pulse 1.2s infinite;
    margin-right: 6px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.8); }
}

/* Summary box */
.summary-box {
    background: linear-gradient(135deg, rgba(79,110,247,0.07), rgba(124,58,237,0.07));
    border: 1px solid rgba(79,110,247,0.25);
    border-radius: var(--radius);
    padding: 1.2rem 1.4rem;
    font-size: 0.92rem;
    line-height: 1.8;
    white-space: pre-wrap;
}

/* Divider */
.divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1rem 0;
}

/* Header */
.app-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 1.5rem;
}
.app-logo {
    font-family: 'Syne', sans-serif;
    font-size: 1.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #4f6ef7, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Selectbox / input */
div[data-baseweb="select"] > div {
    background: var(--surface2) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
}
.stTextArea textarea {
    background: var(--surface2) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Spinner */
.stSpinner > div { border-top-color: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)

# ── Navigation state ──────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"

# ── Routing ───────────────────────────────────────────────────
if st.session_state.page == "home":
    from pages.home import show
    show()
elif st.session_state.page == "meeting":
    from pages.meeting import show
    show()
elif st.session_state.page == "summary":
    from pages.summary import show
    show()
