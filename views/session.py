import streamlit as st
import time
import threading
import av
import io
import os
from datetime import datetime
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

from database import (
    init_db, create_session, get_session, update_session,
    add_source, get_sources, delete_source,
    add_note, get_notes, delete_note,
    add_chat_message, get_chat_messages,
    add_transcript, add_distraction
)
from services.vision import process_frame, shared_state, start_calibration
from services.concentration_engine import engine
from services.cursor_tracker import inject_cursor_tracker
from services.voice_detector import (
    start_listening, stop_listening, set_session_theme,
    set_callbacks, get_status as vd_status, voice_state
)

init_db()
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# ── Video processor ────────────────────────────────────────────
class VisionProcessor(VideoProcessorBase):
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        img = process_frame(img)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ── Helpers ────────────────────────────────────────────────────
def _fmt_time(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def _score_color(s):
    if s > 70: return "#22c55e"
    if s > 45: return "#f97316"
    return "#ef4444"

def _extract_pdf_text(file_bytes):
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except:
        return ""

def _get_groq():
    import httpx
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()
    http_client = httpx.Client(verify=True)
    return Groq(api_key=os.getenv("GROQ_API_KEY"), http_client=http_client)

def _groq_clean_note(raw_text):
    try:
        client = _get_groq()
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":
                f"Corrige uniquement l'orthographe et la grammaire de cette note, "
                f"sans changer le sens ni ajouter de contenu. "
                f"Réponds UNIQUEMENT avec la note corrigée, sans explication.\n\nNote: {raw_text}"}],
            max_tokens=300, temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except:
        return raw_text

def _groq_chat(messages, sources_content, session_title):
    try:
        client  = _get_groq()
        has_src = bool(sources_content and sources_content.strip())
        system  = f"""Tu es Lumi, un assistant d'étude intelligent et bienveillant.
Session en cours : "{session_title}"
{"Sources de l'étudiant :" if has_src else "Aucune source chargée."}
{sources_content[:4000] if has_src else ""}
Réponds de façon concise (3-5 phrases max). Si la réponse est dans les sources, cite-les.
Réponds en français par défaut."""
        groq_msgs = [{"role":"system","content":system}] + \
                    [{"role":m["role"],"content":m["content"]} for m in messages[-10:]]
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=groq_msgs,
            max_tokens=400, temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Erreur : {e}"

def _groq_summary(sources_content, chat_messages, session_title):
    try:
        client  = _get_groq()
        has_src = bool(sources_content and sources_content.strip())
        chat_ex = "\n".join(f"{m['role']}: {m['content']}" for m in chat_messages[-5:])
        prompt  = f"""Session : '{session_title}'
{"Sources : " + sources_content[:2000] if has_src else "Pas encore de sources."}
{"Échanges : " + chat_ex if chat_ex else ""}
Fais un résumé ultra-concis en 2-3 phrases. Si pas de sources, dis bonjour et propose d'uploader des cours."""
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            max_tokens=200, temperature=0.5,
        )
        return resp.choices[0].message.content.strip()
    except:
        return "Bonjour ! Je suis Lumi. Upload tes cours pour commencer !"

def _play_tts(text):
    from services.voice_detector import _play_tts as vd_tts
    vd_tts(text)

def _setup_voice(sid, title, sources_content):
    """Configure et démarre le voice detector."""
    set_session_theme(st.session_state.get("session_theme", "général"))

    def on_lumi_question(question: str):
        """Callback appelé quand Lumi est interpellé."""
        try:
            history = get_chat_messages(sid)
            history.append({"role": "user", "content": question})
            reply   = _groq_chat(history, sources_content, title)
            add_chat_message(sid, "user",      question)
            add_chat_message(sid, "assistant", reply)
            _play_tts(reply[:300])
        except Exception as e:
            pass

    set_callbacks(on_lumi_question=on_lumi_question)
    start_listening()


# ══════════════════════════════════════════════════════════════
# SHOW
# ══════════════════════════════════════════════════════════════
def show():
    inject_cursor_tracker()

    # ── Init session ───────────────────────────────────────────
    if "session_id" not in st.session_state or st.session_state.session_id is None:
        title = st.session_state.get("new_session_title", "Nouvelle session")
        sid   = create_session(title)
        st.session_state.session_id            = sid
        st.session_state.session_title         = title
        st.session_state.session_start         = time.time()
        st.session_state.chat_history          = []
        st.session_state.summary_done          = False
        st.session_state.lumi_mode             = False
        st.session_state.lumi_question         = ""
        stop_listening()

    sid     = st.session_state.session_id
    title   = st.session_state.get("session_title", "Session")
    start   = st.session_state.get("session_start", time.time())
    elapsed = time.time() - start

    sources     = get_sources(sid)
    src_content = "\n\n".join(s.get("content","") for s in sources if s.get("content"))

    _setup_voice(sid, title, src_content)

    # ── CSS ────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .chat-user {
        background:linear-gradient(135deg,#9b6dff,#7c4fe0);
        color:white; border-radius:18px 18px 4px 18px;
        padding:10px 14px; margin:6px 0 6px 20%;
        font-size:0.92rem;
    }
    .chat-lumi {
        background:#2d2040; border:1.5px solid #4a3560;
        border-radius:18px 18px 18px 4px;
        padding:10px 14px; margin:6px 20% 6px 0;
        font-size:0.92rem; color:#f0eaff;
    }
    .chat-label { font-size:0.65rem; font-weight:700; text-transform:uppercase;
                  letter-spacing:0.1em; opacity:0.5; margin-bottom:3px; }
    .note-item {
        background:#2d2040; border:1px solid #4a3560; border-radius:10px;
        padding:10px 14px; margin-bottom:6px; font-size:0.9rem; color:#f0eaff;
    }
    .pdf-thumb {
        background:#2d2040; border:1.5px solid #4a3560; border-radius:12px;
        padding:1rem; text-align:center;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── HEADER ─────────────────────────────────────────────────
    h1, h2, h3 = st.columns([1, 3, 1])
    with h1:
        st.markdown("<div style='font-size:1.6rem;font-weight:800;color:#9b6dff;'>🌟 Lumi</div>",
                    unsafe_allow_html=True)
    with h2:
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="font-size:1.1rem;font-weight:700;color:#f0eaff;">{title}</div>
            <div style="font-size:1.8rem;font-weight:800;color:#9b6dff;
                        font-family:'Space Grotesk',sans-serif;">{_fmt_time(elapsed)}</div>
        </div>""", unsafe_allow_html=True)
    with h3:
        if st.button("🚪 Quitter", use_container_width=True):
            update_session(sid, duration_sec=elapsed)
            stop_listening()
            for k in ["session_id","session_title","session_start","chat_history",
                      "summary_done","lumi_mode","lumi_question","wake_listener_running",
                      "open_source"]:
                st.session_state.pop(k, None)
            st.session_state.page = "home"
            st.rerun()

    st.markdown("<hr style='margin:0.5rem 0 1rem'>", unsafe_allow_html=True)

    # ── LAYOUT ─────────────────────────────────────────────────
    sidebar, main = st.columns([1, 3], gap="medium")

    # ══ SIDEBAR ════════════════════════════════════════════════
    with sidebar:
        st.markdown("<div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
                    "letter-spacing:0.1em;color:#9b6dff;margin-bottom:0.6rem;'>📄 Sources</div>",
                    unsafe_allow_html=True)

        sources = get_sources(sid)
        to_delete = []
        for s in sources:
            if st.checkbox(f"📄 {s['filename']}", key=f"chk_{s['id']}"):
                to_delete.append(s["id"])

        if not sources:
            st.markdown("<div style='font-size:0.82rem;color:#7a6a9a;padding:8px 0;'>"
                        "Aucune source</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

        uploaded = st.file_uploader("", type=["pdf","txt"],
                                    label_visibility="collapsed", key="uploader")
        if uploaded:
            existing = [s["filename"] for s in get_sources(sid)]
            if uploaded.name not in existing:
                if uploaded.type == "application/pdf":
                    content = _extract_pdf_text(uploaded.read())
                else:
                    content = uploaded.read().decode("utf-8", errors="ignore")
                add_source(sid, uploaded.name, content)
                st.rerun()

        if st.button("🗑 Supprimer sélection", use_container_width=True):
            for did in to_delete:
                delete_source(did)
            st.rerun()

    # ══ MAIN ═══════════════════════════════════════════════════
    with main:

        # ── Caméra + Score ──────────────────────────────────────
        cam_col, score_col = st.columns([2, 1], gap="medium")

        with cam_col:
            ctx = webrtc_streamer(
                key="lumi-cam",
                video_processor_factory=VisionProcessor,
                rtc_configuration=RTC_CONFIG,
                media_stream_constraints={
                    "video": {"facingMode":"user","width":640,"height":480},
                    "audio": False
                },
                async_processing=True,
            )
            with shared_state.lock:
                calibrated = shared_state.calibrated
            if not calibrated:
                if st.button("🎯 Calibrer (3s)", key="calib_btn"):
                    start_calibration()
                    st.rerun()

        with score_col:
            with shared_state.lock:
                cam_score = shared_state.score
                cam_alert = shared_state.alert
                yaw       = shared_state.yaw

            engine.update_cursor(st.session_state.get("cursor_idle", 0))
            engine.update_tab(st.session_state.get("tab_visible", True))
            final = engine.compute_final(cam_score)
            fc    = _score_color(final)
            cc    = _score_color(cam_score)

            st.markdown(f"""
            <div style="background:#2d2040;border:1.5px solid #4a3560;border-radius:16px;
                        padding:1rem;text-align:center;margin-bottom:0.6rem;">
                <div style="font-size:0.68rem;color:#a896c8;font-weight:700;
                            text-transform:uppercase;letter-spacing:0.1em;">Score Global</div>
                <div style="font-size:2.8rem;font-weight:800;color:{fc};line-height:1.1;">{final}%</div>
                <div style="background:#382850;border-radius:99px;height:8px;
                            margin-top:6px;overflow:hidden;">
                    <div style="width:{final}%;height:100%;background:{fc};border-radius:99px;"></div>
                </div>
            </div>
            <div style="display:flex;gap:6px;">
                <div style="flex:1;background:#2d2040;border:1px solid #4a3560;
                            border-radius:12px;padding:8px;text-align:center;">
                    <div style="font-size:0.65rem;color:#a896c8;">📷 Caméra</div>
                    <div style="font-size:1.4rem;font-weight:800;color:{cc};">{cam_score}%</div>
                </div>
                <div style="flex:1;background:#2d2040;border:1px solid #4a3560;
                            border-radius:12px;padding:8px;text-align:center;">
                    <div style="font-size:0.65rem;color:#a896c8;">↔️ Yaw</div>
                    <div style="font-size:1.4rem;font-weight:800;color:#b89aff;">{yaw:+.0f}°</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if cam_alert:
                st.error(cam_alert)

        # ── Debug panel voice ───────────────────────────────────
        vs = vd_status()
        with st.expander("🔬 Debug voix", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🎙 Loop", "🟢 ON" if vs["running"] else "🔴 OFF")
            c2.metric("⏺ Enreg.", "🔴 OUI" if vs["is_recording"] else "⚪ non")
            c3.metric("🎯 Thème", vs["session_theme"])
            c4.metric("Lumi mode", "🟣 OUI" if vs["lumi_mode"] else "⚪ non")
            if vs["last_transcript"]:
                st.markdown(f"**Dernière transcription :** {vs['last_transcript']}")
            if vs["alert"]:
                st.warning(vs["alert"])

        # ── Onglets ─────────────────────────────────────────────
        tab_src, tab_lumi = st.tabs(["📄 Sources", "🌟 Lumi"])

        # ══ ONGLET SOURCES ══════════════════════════════════════
        with tab_src:
            sources = get_sources(sid)
            if not sources:
                st.markdown("<div style='text-align:center;padding:2rem;color:#7a6a9a;'>"
                            "Aucune source — ajoute un PDF depuis la sidebar !</div>",
                            unsafe_allow_html=True)
            else:
                if "open_source" not in st.session_state:
                    st.session_state.open_source = None

                # Miniatures
                ncols = min(len(sources), 3)
                thumb_cols = st.columns(ncols, gap="medium")
                for i, s in enumerate(sources):
                    with thumb_cols[i % ncols]:
                        st.markdown(f"""
                        <div class="pdf-thumb">
                            <div style="font-size:2rem;">📄</div>
                            <div style="font-size:0.82rem;color:#b89aff;margin-top:4px;
                                        font-weight:600;word-break:break-all;">
                                {s['filename']}
                            </div>
                        </div>""", unsafe_allow_html=True)
                        if st.button("Ouvrir", key=f"open_pdf_{s['id']}",
                                     use_container_width=True):
                            st.session_state.open_source = s["id"]
                            st.rerun()

                # Vue PDF
                if st.session_state.open_source:
                    src = next((s for s in sources
                                if s["id"] == st.session_state.open_source), None)
                    if src:
                        st.markdown("<hr>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-weight:700;color:#b89aff;margin-bottom:8px;'>"
                                    f"📄 {src['filename']}</div>", unsafe_allow_html=True)

                        content = src.get("content","") or "Contenu non disponible"
                        st.markdown(f"""
                        <div style="background:#221830;border:1px solid #4a3560;
                                    border-radius:12px;padding:1.2rem;
                                    max-height:280px;overflow-y:auto;
                                    font-size:0.88rem;color:#c4b8e0;line-height:1.7;
                                    white-space:pre-wrap;">{content[:3000]}{"..." if len(content)>3000 else ""}
                        </div>""", unsafe_allow_html=True)

                        # Notes
                        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
                        st.markdown("<div style='font-size:0.72rem;font-weight:700;"
                                    "text-transform:uppercase;letter-spacing:0.1em;"
                                    "color:#9b6dff;margin-bottom:0.6rem;'>📝 Notes</div>",
                                    unsafe_allow_html=True)

                        notes = get_notes(sid, src["id"])
                        for n in notes:
                            nc1, nc2 = st.columns([5, 1])
                            with nc1:
                                st.markdown(f"""
                                <div class="note-item">
                                    <div style="font-size:0.68rem;color:#7a6a9a;margin-bottom:4px;">
                                        {n['created_at'][:16]}
                                    </div>
                                    {n['clean_text']}
                                </div>""", unsafe_allow_html=True)
                            with nc2:
                                if st.button("🗑", key=f"del_note_{n['id']}"):
                                    delete_note(n["id"])
                                    st.rerun()

                        new_note = st.text_area("", placeholder="Tape ta note ici...",
                                                label_visibility="collapsed",
                                                key=f"note_input_{src['id']}", height=80)
                        if st.button("✨ Ajouter la note (Lumi corrige)",
                                     key=f"add_note_{src['id']}",
                                     use_container_width=True):
                            if new_note.strip():
                                with st.spinner("Lumi corrige ta note..."):
                                    clean = _groq_clean_note(new_note.strip())
                                add_note(sid, new_note.strip(), clean, src["id"])
                                st.rerun()

                        if st.button("← Retour", key="back_sources"):
                            st.session_state.open_source = None
                            st.rerun()

        # ══ ONGLET LUMI ══════════════════════════════════════════
        with tab_lumi:

            if st.session_state.get("lumi_mode"):
                st.markdown("""
                <div style="background:#3d1f4a;border:1.5px solid #9b6dff;border-radius:12px;
                            padding:10px 16px;margin-bottom:8px;font-size:0.9rem;color:#b89aff;">
                    🎤 Mode Lumi actif — je t'écoute !
                    Dis <b>"merci Lumi"</b> pour terminer.
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#2d2040;border:1px solid #4a3560;border-radius:12px;
                            padding:8px 16px;margin-bottom:8px;font-size:0.82rem;color:#7a6a9a;">
                    💡 Dis <b style="color:#9b6dff;">"Lumi"</b> pour me parler à voix haute
                </div>""", unsafe_allow_html=True)

            # Résumé auto
            if not st.session_state.get("summary_done", False):
                chat_msgs = get_chat_messages(sid)
                with st.spinner("🌟 Lumi prépare un résumé..."):
                    summary = _groq_summary(src_content, chat_msgs, title)
                add_chat_message(sid, "assistant", summary)
                st.session_state.summary_done = True
                _play_tts(summary[:200])

            # Affichage chat
            chat_msgs = get_chat_messages(sid)
            for m in chat_msgs[-20:]:
                if m["role"] == "user":
                    st.markdown(f"""
                    <div>
                        <div class="chat-label" style="text-align:right;color:#a896c8;">Toi</div>
                        <div class="chat-user">{m['content']}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div>
                        <div class="chat-label" style="color:#9b6dff;">🌟 Lumi</div>
                        <div class="chat-lumi">{m['content']}</div>
                    </div>""", unsafe_allow_html=True)

            # Input
            msg_col, btn_col = st.columns([4, 1])
            with msg_col:
                user_input = st.text_input("", placeholder="Pose une question à Lumi...",
                                           label_visibility="collapsed", key="chat_input")
            with btn_col:
                if st.button("Envoyer →", use_container_width=True, key="send_chat"):
                    if user_input.strip():
                        add_chat_message(sid, "user", user_input.strip())
                        history = get_chat_messages(sid)
                        with st.spinner("Lumi réfléchit..."):
                            reply = _groq_chat(history, src_content, title)
                        add_chat_message(sid, "assistant", reply)
                        # Pas de TTS pour le chat écrit
                        st.rerun()

    # Auto-refresh
    if ctx and ctx.state.playing:
        time.sleep(3)
        st.rerun()