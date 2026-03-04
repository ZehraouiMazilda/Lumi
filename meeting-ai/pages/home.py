import streamlit as st


def show():
    # ── Header ────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 3rem 0 2rem;">
        <div style="font-family:'Syne',sans-serif; font-size:0.8rem; font-weight:700;
                    letter-spacing:0.2em; text-transform:uppercase; color:#4f6ef7; margin-bottom:1rem;">
            Projet IA · Master SISE 2025–2026
        </div>
        <div style="font-family:'Syne',sans-serif; font-size:3.2rem; font-weight:800;
                    background:linear-gradient(135deg,#e2e8f0,#94a3b8);
                    -webkit-background-clip:text; -webkit-text-fill-color:transparent; line-height:1.1;">
            Meeting<span style="background:linear-gradient(135deg,#4f6ef7,#7c3aed);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;">AI</span>
        </div>
        <div style="color:#64748b; font-size:1rem; margin-top:0.8rem; max-width:500px; margin-left:auto; margin-right:auto;">
            Analyse de réunion en temps réel — concentration, transcription, statistiques et résumé IA.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Features strip ────────────────────────────────────────
    f1, f2, f3, f4 = st.columns(4)
    features = [
        ("🧠", "Concentration", "Détection du regard & clignements via MediaPipe"),
        ("🎤", "Transcription", "Sous-titres en temps réel avec Whisper"),
        ("📊", "Temps de parole", "Stats par participant avec graphiques"),
        ("✨", "Résumé IA", "Résumé structuré généré par Claude"),
    ]
    for col, (icon, title, desc) in zip([f1, f2, f3, f4], features):
        with col:
            st.markdown(f"""
            <div class="card" style="text-align:center; padding:1.5rem 1rem;">
                <div style="font-size:1.8rem; margin-bottom:0.5rem;">{icon}</div>
                <div style="font-family:'Syne',sans-serif; font-weight:700; font-size:0.95rem;
                            color:#e2e8f0; margin-bottom:0.3rem;">{title}</div>
                <div style="font-size:0.78rem; color:#64748b; line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

    # ── Room setup ────────────────────────────────────────────
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("""
        <div class="card">
            <div class="card-title">⚙️ Configuration de la réunion</div>
        </div>
        """, unsafe_allow_html=True)

        meeting_name = st.text_input(
            "Nom de la réunion",
            placeholder="Ex: Sprint Review — Équipe Alpha",
            label_visibility="visible",
        )

        participants_raw = st.text_input(
            "Participants (séparés par des virgules)",
            placeholder="Alice, Bob, Charlie",
        )

        llm_key = st.text_input(
            "Clé API Anthropic (pour le résumé)",
            type="password",
            placeholder="sk-ant-...",
        )

        whisper_model = st.selectbox(
            "Modèle Whisper",
            ["tiny", "base", "small", "medium"],
            index=1,
            help="'tiny' = rapide, 'medium' = plus précis",
        )

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        if st.button("🚀 Démarrer la réunion", use_container_width=True):
            if not meeting_name:
                st.error("Veuillez entrer un nom de réunion.")
            else:
                participants = [p.strip() for p in participants_raw.split(",") if p.strip()] \
                    if participants_raw else ["Participant 1", "Participant 2"]

                st.session_state.meeting_name = meeting_name
                st.session_state.participants = participants
                st.session_state.llm_key = llm_key
                st.session_state.whisper_model = whisper_model
                st.session_state.transcript = []
                st.session_state.speech_times = {p: 0 for p in participants}
                st.session_state.concentration_history = {p: [] for p in participants}
                st.session_state.summary = ""
                st.session_state.page = "meeting"
                st.rerun()
