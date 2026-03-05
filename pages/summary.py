import streamlit as st
import time

def format_duration(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def score_color(s):
    if s > 60: return "#22d3a0"
    if s > 30: return "#f59e0b"
    return "#ef4444"


def generate_summary_anthropic(api_key: str, transcript: list, meeting_name: str,
                                speech_times: dict, duration: float) -> str:
    """Call Claude API to generate meeting summary."""
    import anthropic

    if not transcript:
        return "Aucune transcription disponible pour générer un résumé."

    transcript_text = "\n".join(
        f"[{e['time']}] {e['speaker']}: {e['text']}"
        for e in transcript
    )

    speech_stats = "\n".join(
        f"- {p}: {format_duration(t)}"
        for p, t in speech_times.items()
    )

    prompt = f"""Tu es un assistant expert en synthèse de réunions professionnelles.

Voici les informations de la réunion :
- Nom : {meeting_name}
- Durée : {format_duration(duration)}
- Participants et temps de parole :
{speech_stats}

Transcription :
{transcript_text}

Génère un compte-rendu structuré en français avec les sections suivantes :
1. 🎯 Résumé exécutif (2-3 phrases)
2. 💬 Points clés discutés (liste à puces)
3. ✅ Décisions prises
4. 📋 Actions à mener (avec responsable si identifiable)
5. 📌 Points en suspens

Sois concis, professionnel et précis."""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_summary_mock(transcript, meeting_name, speech_times, duration):
    """Fallback mock summary when no API key."""
    if not transcript:
        return "Aucune transcription disponible."

    speakers = list(speech_times.keys())
    main_speaker = max(speech_times, key=speech_times.get) if speech_times else "N/A"

    return f"""🎯 **Résumé exécutif**
La réunion "{meeting_name}" a duré {format_duration(duration)} et a réuni {len(speakers)} participant(s). Les échanges ont été productifs et ont couvert plusieurs sujets importants.

💬 **Points clés discutés**
• {transcript[0]['text'] if transcript else 'N/A'}
• Discussion sur les prochaines étapes du projet
• Revue des indicateurs de performance

✅ **Décisions prises**
• Validation de la feuille de route proposée
• Accord sur les priorités à court terme

📋 **Actions à mener**
• {main_speaker} : Préparer le rapport de synthèse
• Équipe : Mettre à jour la documentation

📌 **Points en suspens**
• Confirmation des ressources disponibles
• Date de la prochaine réunion à définir

_(Résumé généré sans API — ajoutez une clé Anthropic pour un résumé IA complet)_"""


def show():
    # Guard
    if "meeting_name" not in st.session_state:
        st.warning("Aucune réunion en cours.")
        if st.button("← Retour à l'accueil"):
            st.session_state.page = "home"
            st.rerun()
        return

    duration = time.time() - st.session_state.get("start_time", time.time())
    participants  = st.session_state.get("participants", [])
    speech_times  = st.session_state.get("speech_times", {})
    transcript    = st.session_state.get("transcript", [])
    conc_history  = st.session_state.get("conc_history", [])
    meeting_name  = st.session_state.get("meeting_name", "Réunion")
    api_key       = st.session_state.get("llm_key", "")

    import numpy as np
    avg_conc = int(np.mean(conc_history)) if conc_history else 0

    # ── Header ────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-bottom:1.5rem;">
        <div style="font-family:'Syne',sans-serif; font-size:0.75rem; font-weight:700;
                    letter-spacing:0.15em; text-transform:uppercase; color:#4f6ef7; margin-bottom:0.4rem;">
            Compte-rendu de réunion
        </div>
        <div style="font-family:'Syne',sans-serif; font-size:2rem; font-weight:800; color:#e2e8f0;">
            {meeting_name}
        </div>
        <div style="color:#64748b; font-size:0.9rem; margin-top:0.3rem;">
            Durée : {format_duration(duration)} · {len(participants)} participant(s) · {len(transcript)} lignes de transcription
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI strip ─────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    kpis = [
        ("⏱", format_duration(duration), "Durée totale"),
        ("👥", str(len(participants)), "Participants"),
        ("🧠", f"{avg_conc}%", "Concentration moy."),
        ("💬", str(len(transcript)), "Échanges transcrits"),
    ]
    for col, (icon, val, label) in zip([k1, k2, k3, k4], kpis):
        with col:
            st.markdown(f"""
            <div class="card" style="text-align:center; padding:1.2rem 0.8rem;">
                <div style="font-size:1.4rem;">{icon}</div>
                <div class="metric-value" style="font-size:1.8rem; margin:0.3rem 0;">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Main columns ──────────────────────────────────────────
    left_col, right_col = st.columns([3, 2])

    # ── Summary ───────────────────────────────────────────────
    with left_col:
        st.markdown('<div class="card-title">✨ Résumé IA</div>', unsafe_allow_html=True)

        if "summary" not in st.session_state or not st.session_state.summary:
            if st.button("🧠 Générer le résumé avec Claude", use_container_width=True):
                with st.spinner("Claude analyse la réunion…"):
                    try:
                        if api_key:
                            st.session_state.summary = generate_summary_anthropic(
                                api_key, transcript, meeting_name, speech_times, duration
                            )
                        else:
                            import time as t; t.sleep(1.5)
                            st.session_state.summary = generate_summary_mock(
                                transcript, meeting_name, speech_times, duration
                            )
                    except Exception as e:
                        st.session_state.summary = generate_summary_mock(
                            transcript, meeting_name, speech_times, duration
                        )
                        st.warning(f"API indisponible, résumé de démo généré. ({e})")
                st.rerun()
        else:
            st.markdown(f'<div class="summary-box">{st.session_state.summary}</div>',
                        unsafe_allow_html=True)
            if st.button("🔄 Régénérer", use_container_width=True):
                st.session_state.summary = ""
                st.rerun()

        # ── Full transcript ────────────────────────────────────
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="card-title">📝 Transcription complète</div>', unsafe_allow_html=True)

        if transcript:
            transcript_html = ""
            for e in transcript:
                transcript_html += f"""
                <div class="subtitle-line">
                    <span class="speaker-pill">{e['speaker']}</span>
                    <span style="font-size:0.72rem; color:#475569;">{e['time']}</span><br/>
                    <span>{e['text']}</span>
                </div>"""
            st.markdown(f'<div class="subtitle-box" style="max-height:300px">{transcript_html}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#475569; font-size:0.85rem;">Aucune transcription enregistrée.</div>',
                        unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────
    with right_col:
        st.markdown('<div class="card-title">📊 Temps de parole</div>', unsafe_allow_html=True)

        import plotly.graph_objects as go
        import plotly.express as px

        colors = ["#4f6ef7", "#22d3a0", "#f59e0b", "#ef4444", "#7c3aed", "#ec4899", "#06b6d4"]

        # Donut chart
        if speech_times and any(v > 0 for v in speech_times.values()):
            labels = list(speech_times.keys())
            values = list(speech_times.values())
            fig_donut = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker=dict(colors=colors[:len(labels)], line=dict(color="#0a0d14", width=2)),
                textfont=dict(family="DM Sans", size=12, color="white"),
                hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
            )])
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                margin=dict(t=10, b=10, l=10, r=10),
                height=220,
                showlegend=True,
                legend=dict(
                    font=dict(color="#94a3b8", size=11),
                    bgcolor="rgba(0,0,0,0)",
                ),
                annotations=[dict(
                    text=f"<b>{len(labels)}</b><br>participants",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=13, color="#94a3b8", family="Syne"),
                )]
            )
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<div style="color:#475569; font-size:0.85rem; padding:1rem 0;">Aucune donnée de parole.</div>',
                        unsafe_allow_html=True)

        # Individual stats
        st.markdown('<div class="card-title">👤 Détail par participant</div>', unsafe_allow_html=True)
        total = sum(speech_times.values()) or 1
        for i, p in enumerate(participants):
            t = speech_times.get(p, 0)
            pct = int(t / total * 100)
            c = colors[i % len(colors)]
            st.markdown(f"""
            <div style="margin-bottom:0.9rem;">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;">
                    <span style="font-weight:600; color:#e2e8f0;">{p}</span>
                    <span style="color:#64748b;">{format_duration(t)} · {pct}%</span>
                </div>
                <div class="prog-bar-bg">
                    <div class="prog-bar-fill" style="width:{pct}%; background:{c};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Concentration history chart
        if conc_history:
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown('<div class="card-title">📈 Courbe de concentration</div>', unsafe_allow_html=True)
            import pandas as pd
            df = pd.DataFrame({"Concentration (%)": conc_history})
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                y=conc_history,
                mode="lines",
                line=dict(color="#4f6ef7", width=2, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(79,110,247,0.1)",
            ))
            fig_line.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                margin=dict(t=5, b=5, l=5, r=5),
                height=150,
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, range=[0, 100], tickfont=dict(size=10, color="#64748b")),
            )
            st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

    # ── Actions ───────────────────────────────────────────────
    st.markdown("<hr style='border-color:#1e2540; margin:1rem 0'>", unsafe_allow_html=True)
    a1, a2, _ = st.columns([1, 1, 2])
    with a1:
        if st.button("← Nouvelle réunion", use_container_width=True):
            for key in ["transcript", "speech_times", "conc_history", "summary",
                        "start_time", "meeting_name", "participants", "active_speaker"]:
                st.session_state.pop(key, None)
            st.session_state.page = "home"
            st.rerun()
    with a2:
        if transcript:
            full_text = "\n".join(f"[{e['time']}] {e['speaker']}: {e['text']}" for e in transcript)
            st.download_button(
                "⬇ Exporter la transcription",
                data=full_text,
                file_name=f"{meeting_name}_transcription.txt",
                mime="text/plain",
                use_container_width=True,
            )
