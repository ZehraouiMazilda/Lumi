import streamlit as st
from datetime import datetime
from database import (
    init_db, get_session, get_session_stats,
    get_timeline, get_chat_messages, get_notes,
    get_sources, get_transcripts
)
import os

init_db()

def _fmt_duration(secs):
    if not secs: return "—"
    mins = int(secs // 60)
    if mins < 60: return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h}h{m:02d}"

def _fmt_date(date_str):
    try:
        d = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        return d.strftime("%d %b %Y à %H:%M")
    except: return date_str[:16] if date_str else "—"

def _score_color(s):
    if not s: return "#4a3560"
    if s >= 70: return "#22c55e"
    if s >= 45: return "#f97316"
    return "#ef4444"

def _score_label(s):
    if not s: return "Pas de données"
    if s >= 80: return "Excellente"
    if s >= 70: return "Très bonne"
    if s >= 55: return "Correcte"
    if s >= 40: return "Fragile"
    return "Difficile"

def _get_groq():
    import httpx
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()
    return Groq(api_key=os.getenv("GROQ_API_KEY"), http_client=httpx.Client(verify=True))

def _generate_report(session, stats, timeline, messages, notes, sources):
    """Génère un rapport LLM complet et créatif sur la session."""
    try:
        title     = session.get("title","—")
        duration  = _fmt_duration(session.get("duration_sec",0))
        score_avg = stats.get("score_avg") or 0
        score_min = stats.get("score_min") or 0
        score_max = stats.get("score_max") or 0
        alert_eyes    = stats.get("alert_eyes") or 0
        alert_yaw     = stats.get("alert_yaw") or 0
        alert_pitch   = stats.get("alert_pitch") or 0
        alert_no_face = stats.get("alert_no_face") or 0
        lumi_calls    = stats.get("lumi_calls") or 0
        notes_count   = stats.get("notes_count") or 0
        summary       = stats.get("summary","")

        # Timeline analysis
        tl_scores = [t.get("score_global") or 0 for t in timeline]
        tl_times  = [t.get("elapsed_sec") or 0 for t in timeline]
        best_period = "—"
        worst_period = "—"
        if tl_scores and tl_times:
            best_idx  = tl_scores.index(max(tl_scores))
            worst_idx = tl_scores.index(min(tl_scores))
            best_period  = f"{int(tl_times[best_idx]//60)} min ({tl_scores[best_idx]}%)"
            worst_period = f"{int(tl_times[worst_idx]//60)} min ({tl_scores[worst_idx]}%)"

        # Chat questions
        questions = [m["content"] for m in messages if m["role"]=="user"][:5]
        questions_str = "\n".join(f"- {q}" for q in questions) if questions else "Aucune question posée"

        # Notes
        notes_str = "\n".join(f"- {n['clean_text'][:80]}" for n in notes[:5]) if notes else "Aucune note"

        # Sources
        sources_str = ", ".join(s["filename"] for s in sources) if sources else "Aucune source"

        prompt = f"""Tu es Lumi, un assistant d'étude bienveillant mais honnête. Génère un rapport d'analyse complet, créatif et personnalisé pour cette session d'étude.

DONNÉES DE SESSION :
- Sujet : {title}
- Durée : {duration}
- Sources étudiées : {sources_str}
- Score concentration moyen : {score_avg:.0f}% ({_score_label(score_avg)})
- Score minimum : {score_min}% | Score maximum : {score_max}%
- Meilleur moment : {best_period}
- Moment difficile : {worst_period}
- Alertes yeux fermés/clignements : {alert_eyes}x
- Alertes tête gauche/droite : {alert_yaw}x
- Alertes tête haut/bas : {alert_pitch}x
- Alertes visage absent : {alert_no_face}x
- Questions posées à Lumi : {lumi_calls}x
- Notes prises : {notes_count}
- Résumé du contenu étudié : {summary}

Questions posées à Lumi :
{questions_str}

Notes prises :
{notes_str}

INSTRUCTIONS :
Génère exactement ce JSON (et RIEN d'autre, pas de markdown, pas de ```):
{{
  "verdict": "Une phrase courte et directe sur la session (ex: 'Une session solide mais avec des creux.')",
  "score_humain": "Traduction humaine du score (ex: 'Ton cerveau était là à 70% du temps — pas mal !')",
  "analyse_concentration": "2-3 phrases analysant les patterns de concentration, les moments forts/faibles, les tendances observées dans la timeline",
  "analyse_distractions": "2-3 phrases sur les types de distractions dominantes et ce qu'elles révèlent sur le comportement",
  "analyse_engagement": "2 phrases sur l'engagement (questions posées, notes prises, utilisation de Lumi)",
  "point_fort": "Un point fort très spécifique de cette session",
  "point_faible": "Un point faible très spécifique à corriger",
  "conseil_1_titre": "Titre court du 1er conseil",
  "conseil_1": "Conseil concret et actionnable basé sur les vraies données (2 phrases max)",
  "conseil_2_titre": "Titre court du 2ème conseil",
  "conseil_2": "Conseil concret et actionnable (2 phrases max)",
  "conseil_3_titre": "Titre court du 3ème conseil",
  "conseil_3": "Conseil concret et actionnable (2 phrases max)",
  "technique_focus": "Nom d'une technique de concentration recommandée (ex: Pomodoro 25/5, Pomodoro 50/10, Flow state, etc.)",
  "technique_explication": "Pourquoi cette technique spécifiquement pour ce profil (1 phrase)",
  "next_session": "Suggestion concrète pour la prochaine session (1 phrase motivante)",
  "phrase_motivation": "Une phrase de conclusion courte, percutante, personnalisée au sujet étudié"
}}"""

        r = _get_groq().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"user","content":prompt}],
            max_tokens=1200, temperature=0.7
        )
        import json
        raw = r.choices[0].message.content.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[REPORT ERROR] {e}", flush=True)
        return None


def show():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Space+Mono&family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&display=swap');

    .block-container { padding: 2rem 3rem !important; max-width: 860px !important; margin: 0 auto !important; }

    .lumi-dot { display:inline-block;width:10px;height:10px;border-radius:50%;
        background:#9b6dff;box-shadow:0 0 10px #9b6dff;
        animation:lumipulse 2s ease-in-out infinite;vertical-align:middle;margin-right:8px; }
    @keyframes lumipulse{0%,100%{opacity:1;box-shadow:0 0 10px #9b6dff}50%{opacity:0.3;box-shadow:0 0 3px #9b6dff}}

    .eyebrow { font-family:'Space Mono',monospace;font-size:0.58rem;
        color:#9b6dff;letter-spacing:0.2em;text-transform:uppercase; }
    .section-title { font-family:'Syne',sans-serif;font-size:1.5rem;
        font-weight:800;color:#f0eaff;letter-spacing:-0.02em;margin-bottom:0.8rem; }

    /* Hero */
    .hero-title { font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;
        color:#f0eaff;letter-spacing:-0.02em;line-height:1.15; }
    .hero-score { font-family:'Syne',sans-serif;font-size:3.5rem;font-weight:800;line-height:1; }
    .hero-meta { font-family:'Space Mono',monospace;font-size:0.6rem;color:#4a3560;margin-top:0.4rem; }

    /* Verdict */
    .verdict-box { background:linear-gradient(135deg,#1a0d2e,#13101e);
        border:1px solid #9b6dff44;border-left:3px solid #9b6dff;
        border-radius:14px;padding:1.4rem 1.6rem;margin-bottom:0; }
    .verdict-text { font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;
        color:#f0eaff;margin-bottom:0.4rem; }
    .verdict-human { font-family:'Bricolage Grotesque',sans-serif;font-size:0.88rem;
        color:#9b6dff;font-style:italic; }

    /* Stat cards */
    .stat-card { background:#13101e;border:1px solid #2d2040;
        border-radius:12px;padding:1rem 1.1rem;text-align:center; }
    .stat-val { font-family:'Syne',sans-serif;font-size:1.6rem;
        font-weight:800;line-height:1;margin-bottom:3px; }
    .stat-lbl { font-family:'Space Mono',monospace;font-size:0.52rem;
        color:#4a3560;letter-spacing:0.1em;text-transform:uppercase; }

    /* Analyse cards */
    .analyse-card { background:#13101e;border:1px solid #2d2040;
        border-radius:12px;padding:1.1rem 1.2rem;height:100%; }
    .analyse-icon { font-size:1.2rem;margin-bottom:0.4rem; }
    .analyse-title { font-family:'Space Mono',monospace;font-size:0.55rem;
        color:#9b6dff;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:0.5rem; }
    .analyse-text { font-family:'Bricolage Grotesque',sans-serif;font-size:0.82rem;
        color:#b89aff;line-height:1.65; }

    /* Timeline */
    .tl-wrap { display:flex;gap:3px;align-items:flex-end;height:90px;margin:0.6rem 0; }
    .tl-bar { flex:1;border-radius:3px 3px 0 0;min-height:4px; }
    .tl-legend { display:flex;justify-content:space-between;
        font-family:'Space Mono',monospace;font-size:0.52rem;color:#4a3560;margin-top:3px; }

    /* Conseil cards */
    .conseil-card { background:#13101e;border:1px solid #2d2040;
        border-radius:12px;padding:1.1rem 1.2rem; }
    .conseil-num { font-family:'Space Mono',monospace;font-size:0.52rem;
        color:#4a3560;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:4px; }
    .conseil-title { font-family:'Syne',sans-serif;font-size:0.88rem;
        font-weight:700;color:#e0d8ff;margin-bottom:6px; }
    .conseil-text { font-family:'Bricolage Grotesque',sans-serif;font-size:0.8rem;
        color:#5a4a7a;line-height:1.6; }

    /* Technique */
    .tech-box { background:linear-gradient(135deg,#1a0d2e,#0e0b1a);
        border:1px solid #9b6dff33;border-radius:14px;padding:1.2rem 1.4rem;
        display:flex;align-items:center;gap:1.2rem; }
    .tech-name { font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:#9b6dff; }
    .tech-why { font-family:'Bricolage Grotesque',sans-serif;font-size:0.8rem;color:#5a4a7a; }

    /* Alert bars */
    .alert-card { background:#13101e;border:1px solid #2d2040;border-radius:12px;padding:0.9rem 1rem; }
    .alert-label { font-family:'Space Mono',monospace;font-size:0.52rem;
        color:#9b6dff;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:3px; }
    .alert-count { font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800; }
    .alert-bar-bg { background:#1e1530;border-radius:99px;height:3px;margin-top:5px;overflow:hidden; }
    .alert-bar { height:3px;border-radius:99px; }

    /* Chat */
    .chat-a { background:#13101e;border:1px solid #2d2040;border-radius:12px 12px 12px 4px;
        padding:8px 12px;margin:3px 12% 3px 0;font-family:'Bricolage Grotesque',sans-serif;
        font-size:0.8rem;color:#e0d8ff;line-height:1.6; }
    .chat-u { background:linear-gradient(135deg,#9b6dff,#7c4fe0);border-radius:12px 12px 4px 12px;
        padding:8px 12px;margin:3px 0 3px 12%;font-family:'Bricolage Grotesque',sans-serif;
        font-size:0.8rem;color:#fff; }
    .chat-lbl { font-family:'Space Mono',monospace;font-size:0.5rem;color:#4a3560;
        text-transform:uppercase;letter-spacing:0.1em;margin-bottom:1px; }

    /* Note */
    .note-item { background:#13101e;border:1px solid #2d2040;border-radius:10px;
        padding:8px 12px;margin-bottom:5px;font-family:'Bricolage Grotesque',sans-serif;
        font-size:0.8rem;color:#e0d8ff;line-height:1.6; }
    .note-d { font-family:'Space Mono',monospace;font-size:0.5rem;color:#4a3560;margin-bottom:2px; }

    /* Motivation */
    .motiv-box { background:linear-gradient(135deg,#2d1b4e,#1a0d2e);
        border-radius:16px;padding:1.8rem;text-align:center;
        border:1px solid #9b6dff33; }
    .motiv-text { font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;
        color:#f0eaff;line-height:1.4; }
    .motiv-next { font-family:'Bricolage Grotesque',sans-serif;font-size:0.82rem;
        color:#9b6dff;margin-top:0.6rem; }

    /* Source pill */
    .src-pill { background:#13101e;border:1px solid #2d2040;border-radius:99px;
        padding:4px 13px;font-family:'Bricolage Grotesque',sans-serif;
        font-size:0.75rem;color:#9b6dff;font-weight:600;
        display:inline-block;margin:3px 3px; }
    </style>
    """, unsafe_allow_html=True)

    sid = st.session_state.get("selected_session_id")

    # ── Header ──────────────────────────────────────────────
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<span class="lumi-dot"></span><span style="font-family:Syne,sans-serif;font-size:1.3rem;font-weight:800;color:#f0eaff;">Lumi</span>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div style="text-align:right;font-family:Space Mono,monospace;font-size:0.6rem;color:#2d2040;padding-top:6px;">Rapport de session</div>', unsafe_allow_html=True)
    st.divider()

    if not sid:
        _, bc, _ = st.columns([1, 1, 1])
        with bc:
            st.markdown('<div class="section-title" style="text-align:center;">Aucune session</div>', unsafe_allow_html=True)
            if st.button("Retour", use_container_width=True):
                st.session_state["page"] = "home"; st.rerun()
        return

    # ── Charger données ───────────────────────────────────────
    session  = get_session(sid)
    stats    = get_session_stats(sid)
    timeline = get_timeline(sid)
    messages = get_chat_messages(sid)
    notes    = get_notes(sid)
    sources  = get_sources(sid)

    if not session:
        st.error("Session introuvable.")
        return

    title     = session.get("title","—")
    duration  = session.get("duration_sec", 0)
    created   = session.get("created_at","")
    score_avg = stats.get("score_avg") or 0
    score_min = stats.get("score_min") or 0
    score_max = stats.get("score_max") or 0
    lumi_calls = stats.get("lumi_calls") or 0
    summary   = stats.get("summary","")
    sc = _score_color(score_avg)

    # ── Générer rapport LLM ───────────────────────────────────
    cache_key = f"report_{sid}"
    if cache_key not in st.session_state:
        with st.spinner("Lumi analyse ta session..."):
            st.session_state[cache_key] = _generate_report(
                session, stats, timeline, messages, notes, sources)
    report = st.session_state.get(cache_key)

    # ── HERO ─────────────────────────────────────────────────
    st.markdown('<div class="eyebrow">Rapport · Session</div>', unsafe_allow_html=True)

    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f'<div class="hero-title">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="hero-meta">{_fmt_date(created)} &nbsp;·&nbsp; {_fmt_duration(duration)} &nbsp;·&nbsp; {_score_label(score_avg)}</div>', unsafe_allow_html=True)
    with h2:
        st.markdown(f'<div class="hero-score" style="color:{sc};text-align:right;">{int(score_avg)}%</div><div style="font-family:Space Mono,monospace;font-size:0.52rem;color:#4a3560;text-align:right;margin-top:3px;">CONCENTRATION</div>', unsafe_allow_html=True)

    st.markdown(f'<div style="background:#1e1530;border-radius:99px;height:5px;margin:0.8rem 0;overflow:hidden;"><div style="width:{int(score_avg)}%;height:100%;background:{sc};border-radius:99px;"></div></div>', unsafe_allow_html=True)

    # ── Verdict LLM ──────────────────────────────────────────
    if report:
        st.markdown(f"""
        <div class="verdict-box">
            <div class="verdict-text">{report.get('verdict','')}</div>
            <div class="verdict-human">{report.get('score_humain','')}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
    _, bc, _ = st.columns([3, 1, 3])
    with bc:
        if st.button("Retour", key="back_home", use_container_width=True):
            st.session_state["page"] = "home"; st.rerun()

    st.divider()

    # ── KPIs ─────────────────────────────────────────────────
    st.markdown('<div class="eyebrow">Chiffres clés</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">En un coup d\'œil</div>', unsafe_allow_html=True)

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    kpis = [
        (f"{int(score_avg)}%", "Moy.",     sc),
        (f"{int(score_min)}%", "Min",      _score_color(score_min)),
        (f"{int(score_max)}%", "Max",      _score_color(score_max)),
        (f"{lumi_calls}",      "Lumi",     "#9b6dff"),
        (f"{len(notes)}",      "Notes",    "#9b6dff"),
        (f"{len(sources)}",    "Sources",  "#4a3560"),
    ]
    for col,(val,lbl,color) in zip([k1,k2,k3,k4,k5,k6],kpis):
        with col:
            st.markdown(f'<div class="stat-card"><div class="stat-val" style="color:{color};">{val}</div><div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.divider()

    # ── Analyse LLM ───────────────────────────────────────────
    if report:
        st.markdown('<div class="eyebrow">Analyse Lumi</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Ce que révèlent tes données</div>', unsafe_allow_html=True)

        a1, a2 = st.columns(2, gap="medium")
        with a1:
            st.markdown(f"""
            <div class="analyse-card">
                <div class="analyse-title">Concentration</div>
                <div class="analyse-text">{report.get('analyse_concentration','')}</div>
            </div>""", unsafe_allow_html=True)
        with a2:
            st.markdown(f"""
            <div class="analyse-card">
                <div class="analyse-title">Distractions</div>
                <div class="analyse-text">{report.get('analyse_distractions','')}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        b1, b2 = st.columns([1, 1], gap="medium")
        with b1:
            st.markdown(f"""
            <div class="analyse-card">
                <div class="analyse-title">Engagement</div>
                <div class="analyse-text">{report.get('analyse_engagement','')}</div>
            </div>""", unsafe_allow_html=True)
        with b2:
            pf_color = "#22c55e"
            pp_color = "#ef4444"
            st.markdown(f"""
            <div class="analyse-card">
                <div class="analyse-title" style="color:#22c55e;">Point fort</div>
                <div class="analyse-text" style="color:#b89aff;margin-bottom:0.8rem;">{report.get('point_fort','')}</div>
                <div class="analyse-title" style="color:#ef4444;">A améliorer</div>
                <div class="analyse-text" style="color:#b89aff;">{report.get('point_faible','')}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

    # ── Timeline ──────────────────────────────────────────────
    if timeline:
        st.markdown('<div class="eyebrow">Timeline</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Concentration minute par minute</div>', unsafe_allow_html=True)

        tl_scores = [t.get("score_global") or 0 for t in timeline]
        tl_secs   = [t.get("elapsed_sec") or 0 for t in timeline]
        max_s = max(tl_scores) if tl_scores else 100
        max_s = max(max_s, 1)

        bars = '<div class="tl-wrap">'
        for i, (s, sec) in enumerate(zip(tl_scores, tl_secs)):
            h = max(4, int((s / max_s) * 90))
            c = _score_color(s)
            m = int(sec // 60)
            bars += f'<div class="tl-bar" style="height:{h}px;background:{c};" title="{m}min · {s}%"></div>'
        bars += '</div>'
        if len(tl_secs) > 1:
            bars += f'<div class="tl-legend"><span>0 min</span><span>{int(tl_secs[len(tl_secs)//2]//60)} min</span><span>{int(tl_secs[-1]//60)} min</span></div>'
        st.markdown(bars, unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        total = len(tl_scores)
        good = sum(1 for s in tl_scores if s >= 70)
        med  = sum(1 for s in tl_scores if 45 <= s < 70)
        bad  = sum(1 for s in tl_scores if s < 45)

        t1, t2, t3 = st.columns(3, gap="medium")
        for col, (label, count, color) in zip([t1,t2,t3],[
            ("Bons segments",   good, "#22c55e"),
            ("Segments moyens", med,  "#f97316"),
            ("Segments faibles",bad,  "#ef4444"),
        ]):
            pct = int(count/total*100) if total else 0
            with col:
                st.markdown(f"""
                <div class="alert-card">
                    <div class="alert-label">{label}</div>
                    <div class="alert-count" style="color:{color};">{count} <span style="font-size:0.75rem;color:#4a3560;">· {pct}%</span></div>
                    <div class="alert-bar-bg"><div class="alert-bar" style="width:{pct}%;background:{color};"></div></div>
                </div>""", unsafe_allow_html=True)

        st.divider()

    # ── Alertes caméra ────────────────────────────────────────
    st.markdown('<div class="eyebrow">Alertes caméra</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Tes patterns de distraction</div>', unsafe_allow_html=True)

    alert_data = [
        ("Clignements excessifs", stats.get("alert_eyes") or 0,     "#9b6dff", "Fatigue oculaire"),
        ("Tête gauche / droite",  stats.get("alert_yaw") or 0,      "#f97316", "Regard détourné"),
        ("Tête haut / bas",       stats.get("alert_pitch") or 0,    "#ef4444", "Déconcentration"),
        ("Visage absent",         stats.get("alert_no_face") or 0,  "#4a3560", "Absent de l'écran"),
    ]
    total_alerts = sum(a[1] for a in alert_data) or 1

    al1, al2, al3, al4 = st.columns(4, gap="medium")
    for col, (label, count, color, sublabel) in zip([al1,al2,al3,al4], alert_data):
        pct = int(count / total_alerts * 100)
        with col:
            st.markdown(f"""
            <div class="alert-card">
                <div class="alert-label">{label}</div>
                <div class="alert-count" style="color:{color};">{count}</div>
                <div style="font-family:'Space Mono',monospace;font-size:0.5rem;color:#4a3560;margin-top:2px;">{sublabel}</div>
                <div class="alert-bar-bg"><div class="alert-bar" style="width:{pct}%;background:{color};"></div></div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Conseils LLM ──────────────────────────────────────────
    if report:
        st.markdown('<div class="eyebrow">Recommandations</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">3 choses à changer maintenant</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3, gap="medium")
        for col, (num, t_key, c_key) in zip([c1,c2,c3],[
            ("01", "conseil_1_titre", "conseil_1"),
            ("02", "conseil_2_titre", "conseil_2"),
            ("03", "conseil_3_titre", "conseil_3"),
        ]):
            with col:
                st.markdown(f"""
                <div class="conseil-card">
                    <div class="conseil-num">Conseil {num}</div>
                    <div class="conseil-title">{report.get(t_key,'')}</div>
                    <div class="conseil-text">{report.get(c_key,'')}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # Technique recommandée
        st.markdown(f"""
        <div class="tech-box">
            <div style="font-size:1.8rem;">🎯</div>
            <div>
                <div style="font-family:'Space Mono',monospace;font-size:0.52rem;color:#4a3560;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:3px;">Technique recommandée</div>
                <div class="tech-name">{report.get('technique_focus','')}</div>
                <div class="tech-why">{report.get('technique_explication','')}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.divider()

    # ── Sources ───────────────────────────────────────────────
    if sources:
        st.markdown('<div class="eyebrow">Sources étudiées</div>', unsafe_allow_html=True)
        pills = "".join(f'<span class="src-pill">{s["filename"]}</span>' for s in sources)
        st.markdown(f'<div style="margin-bottom:0.5rem;">{pills}</div>', unsafe_allow_html=True)
        st.divider()

    # ── Notes ─────────────────────────────────────────────────
    if notes:
        st.markdown('<div class="eyebrow">Notes</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Tes notes corrigées par Lumi</div>', unsafe_allow_html=True)
        for n in notes:
            st.markdown(f'<div class="note-item"><div class="note-d">{n.get("created_at","")[:16]}</div>{n.get("clean_text","")}</div>', unsafe_allow_html=True)
        st.divider()

    # ── Conversation ──────────────────────────────────────────
    if messages:
        st.markdown('<div class="eyebrow">Conversation</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Tes échanges avec Lumi</div>', unsafe_allow_html=True)
        for m in messages:
            if m["role"] == "user":
                st.markdown(f'<div class="chat-lbl" style="text-align:right;">Toi</div><div class="chat-u">{m["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-lbl">Lumi</div><div class="chat-a">{m["content"]}</div>', unsafe_allow_html=True)
        st.divider()

    # ── Motivation finale ─────────────────────────────────────
    if report:
        next_s = report.get("next_session","")
        motiv  = report.get("phrase_motivation","")
        st.markdown(f"""
        <div class="motiv-box">
            <div class="motiv-text">{motiv}</div>
            {f'<div class="motiv-next">{next_s}</div>' if next_s else ''}
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────
    st.divider()
    f1, f2, f3 = st.columns([2, 1, 1], gap="large")
    with f1:
        st.markdown('<span class="lumi-dot"></span><span style="font-family:Syne,sans-serif;font-weight:800;color:#f0eaff;">Lumi</span>', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Bricolage Grotesque,sans-serif;font-size:0.8rem;color:#2d2040;line-height:1.7;margin-top:0.4rem;max-width:240px;">Assistant d\'étude conçu pour rester concentré et analyser tes sessions.</div>', unsafe_allow_html=True)
    with f2:
        st.markdown('<div style="font-family:Space Mono,monospace;font-size:0.58rem;color:#4a3560;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:0.5rem;">Stack</div>', unsafe_allow_html=True)
        for x in ["Streamlit","Groq / Llama 3.1","Whisper Large v3","MediaPipe"]:
            st.markdown(f'<div style="font-family:Bricolage Grotesque,sans-serif;font-size:0.78rem;color:#4a3560;margin-bottom:3px;">{x}</div>', unsafe_allow_html=True)
    with f3:
        st.markdown('<div style="font-family:Space Mono,monospace;font-size:0.58rem;color:#4a3560;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:0.5rem;">Fonctions</div>', unsafe_allow_html=True)
        for x in ["Détection concentration","Réponses vocales TTS","Analytics session","Sauvegarde DB"]:
            st.markdown(f'<div style="font-family:Bricolage Grotesque,sans-serif;font-size:0.78rem;color:#4a3560;margin-bottom:3px;">{x}</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Space Mono,monospace;font-size:0.58rem;color:#1e1530;text-align:center;padding-top:1.2rem;">2025–2026 · Master SISE · Python · SQLite · gTTS · OpenCV</div>', unsafe_allow_html=True)