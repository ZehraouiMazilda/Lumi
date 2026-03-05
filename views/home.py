import streamlit as st
from datetime import datetime

from database import init_db, get_all_sessions
init_db()

def _fmt_duration(mins):
    if mins < 60: return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h}h{m:02d}"

def _fmt_date(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d %b %Y")
    except:
        return date_str

def show():

    # ── CSS spécifique home ────────────────────────────────────
    st.markdown("""
    <style>
    .lumi-hero { text-align:center; padding:3rem 0 0.5rem; }
    .lumi-logo {
        display:inline-flex; align-items:center; justify-content:center;
        width:88px; height:88px;
        background:linear-gradient(135deg,#9b6dff,#7c4fe0);
        border-radius:24px; font-size:2.6rem;
        box-shadow:0 8px 40px rgba(155,109,255,0.5);
        margin-bottom:1.2rem;
        animation: float 3s ease-in-out infinite;
    }
    .lumi-title {
        font-family:'Outfit',sans-serif;
        font-size:3.6rem; font-weight:800;
        color:#f0eaff; line-height:1.1;
        letter-spacing:-0.02em; margin-bottom:0.5rem;
    }
    .lumi-desc {
        font-size:1.1rem; color:#a896c8;
        line-height:1.7; max-width:540px; margin:0 auto 0.5rem;
    }
    .lumi-desc b { color:#b89aff; }

    .how-box {
        background:#2d2040; border:1.5px solid #4a3560;
        border-radius:14px; padding:1.2rem 1rem;
        text-align:center;
        box-shadow:0 4px 20px rgba(155,109,255,0.1);
    }
    .how-box .icon { font-size:1.8rem; margin-bottom:6px; }
    .how-box .htitle { font-weight:700; color:#f0eaff; font-size:1rem; margin-bottom:4px; }
    .how-box .hdesc  { font-size:0.82rem; color:#a896c8; }

    .session-card {
        background:#2d2040; border:1.5px solid #4a3560;
        border-radius:16px; padding:1.5rem 1.6rem;
        text-align:center; cursor:pointer;
        box-shadow:0 4px 24px rgba(155,109,255,0.1);
        transition:border-color 0.2s, box-shadow 0.2s;
        margin-bottom:0.5rem;
    }
    .session-card:hover {
        border-color:#9b6dff;
        box-shadow:0 8px 32px rgba(155,109,255,0.25);
    }
    .session-card .stitle {
        font-size:1.15rem; font-weight:800;
        color:#f0eaff; margin-bottom:8px;
    }
    .session-card .stheme {
        font-size:1rem; font-weight:700;
        color:#b89aff; margin-bottom:12px;
        font-style:italic; line-height:1.5;
    }
    .session-card .smeta {
        font-size:0.82rem; color:#7a6a9a;
        display:flex; gap:16px; justify-content:center;
    }

    .footer-wrap {
        margin-top:4rem; border-top:1.5px solid #2d2040;
        padding:2rem 0 1rem; text-align:center;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── HERO ──────────────────────────────────────────────────
    st.markdown("""
    <div class="lumi-hero">
        <div class="lumi-logo">🌟</div>
        <div class="lumi-title">Lumi</div>
        <div class="lumi-desc">
            Ton assistant d'étude intelligent.<br>
            <b>Upload tes cours → pose des questions → Lumi t'écoute et t'analyse.</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── HOW IT WORKS ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    for col, icon, title, desc in [
        (c1, "📄", "Upload",   "Ajoute tes cours PDF ou texte"),
        (c2, "🎤", "Parle",    "Pose tes questions à voix haute"),
        (c3, "🧠", "Analyse",  "Lumi surveille ta concentration"),
        (c4, "📊", "Progresse","Consulte tes stats de session"),
    ]:
        with col:
            st.markdown(f"""
            <div class="how-box">
                <div class="icon">{icon}</div>
                <div class="htitle">{title}</div>
                <div class="hdesc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='margin:2rem 0'>", unsafe_allow_html=True)

    # ── SESSIONS ──────────────────────────────────────────────
    st.markdown("<div style='font-size:1.3rem;font-weight:700;color:#f0eaff;margin-bottom:1.2rem;'>📚 Mes sessions</div>", unsafe_allow_html=True)

    sessions = get_all_sessions()

    # Adapte les champs pour le display
    for s in sessions:
        s.setdefault("theme", "Aucun thème défini")
        s.setdefault("last_used", s.get("updated_at","")[:10])
        s.setdefault("duration", int(s.get("duration_sec", 0) // 60))

    if sessions:
        for i in range(0, len(sessions), 2):
            cols = st.columns(2, gap="medium")
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(sessions):
                    break
                s = sessions[idx]
                with col:
                    st.markdown(f"""
                    <div class="session-card">
                        <div class="stitle">{s['title']}</div>
                        <div class="stheme">"{s['theme']}"</div>
                        <div class="smeta">
                            <span>📅 {_fmt_date(s['last_used'])}</span>
                            <span>⏱ {_fmt_duration(s['duration'])}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Ouvrir →", key=f"open_{s['id']}", use_container_width=True):
                        st.session_state.selected_session = s
                        st.session_state.page = "session"
                        st.rerun()

            # Espace entre les lignes
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#7a6a9a;font-size:1rem;">
            Aucune session pour l'instant.<br>
            <span style="color:#9b6dff;font-weight:600;">Lance ta première session ci-dessous !</span>
        </div>
        """, unsafe_allow_html=True)

    # ── BOUTON NOUVELLE SESSION ────────────────────────────────
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        session_title = st.text_input("", placeholder="Nom de la session (ex: Révision Algo...)",
                                      label_visibility="collapsed", key="new_session_title_input")
        if st.button("✨ Commencer une nouvelle session", key="new_session"):
            title = session_title.strip() if session_title.strip() else "Nouvelle session"
            st.session_state.new_session_title = title
            st.session_state.session_id        = None
            st.session_state.page              = "session"
            st.rerun()

    # ── FOOTER ────────────────────────────────────────────────
    st.markdown("""
    <div class="footer-wrap">
        <div style="font-size:1.4rem;font-weight:800;color:#9b6dff;margin-bottom:0.4rem;">Lumi 🌟</div>
        <div style="font-size:0.88rem;color:#7a6a9a;margin-bottom:1rem;line-height:1.8;">
            Assistant d'étude IA · Détection de concentration · Transcription vocale
        </div>
        <div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin-bottom:1rem;">
            <a href="https://github.com" target="_blank"
               style="color:#a896c8;text-decoration:none;font-size:0.88rem;font-weight:600;">
               ⬡ GitHub
            </a>
            <span style="color:#4a3560;">·</span>
            <span style="color:#7a6a9a;font-size:0.85rem;">🤖 Groq · Llama 3.3</span>
            <span style="color:#4a3560;">·</span>
            <span style="color:#7a6a9a;font-size:0.85rem;">👁 MediaPipe</span>
            <span style="color:#4a3560;">·</span>
            <span style="color:#7a6a9a;font-size:0.85rem;">🎤 Whisper</span>
            <span style="color:#4a3560;">·</span>
            <span style="color:#7a6a9a;font-size:0.85rem;">⚡ Streamlit</span>
        </div>
        <div style="font-size:0.78rem;color:#4a3560;">Master SISE 2025–2026 · Fait avec 💜</div>
    </div>
    """, unsafe_allow_html=True)