"""
Voice Detector v3
- Enregistrement VAD : coupe après 3s de silence
- Son via winsound (Windows natif, pas de conflit fichier)
"""
import threading
import time
import os
import json
import numpy as np
from dotenv import load_dotenv

load_dotenv()

def _get_groq():
    import httpx
    from groq import Groq
    http_client = httpx.Client(verify=True)
    return Groq(api_key=os.getenv("GROQ_API_KEY"), http_client=http_client)

# ── State ─────────────────────────────────────────────────────
class VoiceState:
    def __init__(self):
        self.lock            = threading.Lock()
        self.running         = False
        self.is_recording    = False
        self.last_transcript = ""
        self.last_theme      = ""
        self.is_on_topic     = True
        self.alert           = ""
        self.transcript_log  = []
        self.session_theme   = "général"
        self.lumi_mode       = False
        self.lumi_question   = ""
        self.off_topic_count = 0

voice_state = VoiceState()

_on_lumi_question = None
_on_alert         = None

def set_callbacks(on_lumi_question=None, on_alert=None):
    global _on_lumi_question, _on_alert
    _on_lumi_question = on_lumi_question
    _on_alert         = on_alert

# ── TTS ───────────────────────────────────────────────────────
def _play_tts(text: str):
    """Joue du texte à voix haute — gTTS en mémoire, zéro fichier."""
    def _run():
        try:
            from gtts import gTTS
            import pygame
            import io
            buf = io.BytesIO()
            gTTS(text=text[:120], lang='fr', slow=False).write_to_fp(buf)
            buf.seek(0)
            pygame.mixer.init()
            pygame.mixer.music.load(buf, "mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception:
            try:
                import winsound
                winsound.Beep(880, 300)
                time.sleep(0.1)
                winsound.Beep(1100, 300)
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()

# ── VAD recording ─────────────────────────────────────────────
def _record_until_silence(samplerate=16000, silence_threshold=0.02,
                           silence_duration=3.0, max_duration=45.0):
    """
    Enregistre jusqu'à 3s de silence consécutif.
    Retourne numpy array ou None si trop silencieux.
    """
    import sounddevice as sd

    CHUNK      = int(samplerate * 0.1)   # 100ms par chunk
    max_chunks = int(max_duration / 0.1)
    sil_chunks = int(silence_duration / 0.1)

    frames         = []
    silent_count   = 0
    has_speech     = False

    for _ in range(max_chunks):
        with voice_state.lock:
            if not voice_state.running:
                break
        chunk = sd.rec(CHUNK, samplerate=samplerate, channels=1,
                       dtype='float32', blocking=True)
        rms = float(np.sqrt(np.mean(chunk**2)))

        if rms > silence_threshold:
            has_speech   = True
            silent_count = 0
            frames.append(chunk)
        else:
            if has_speech:
                frames.append(chunk)
                silent_count += 1
                if silent_count >= sil_chunks:
                    break   # 3s de silence → on coupe
            # Pas encore de parole → on attend sans stocker

    if not has_speech or len(frames) < 3:
        return None
    return np.concatenate(frames, axis=0)

# ── Loop principale ───────────────────────────────────────────
def start_listening():
    with voice_state.lock:
        if voice_state.running:
            return
        voice_state.running = True
    threading.Thread(target=_listen_loop, daemon=True).start()

def stop_listening():
    with voice_state.lock:
        voice_state.running = False

def _listen_loop():
    try:
        import soundfile as sf
    except Exception as e:
        with voice_state.lock:
            voice_state.last_transcript = f"[soundfile manquant: {e}]"
        return

    SAMPLERATE = 16000

    while True:
        with voice_state.lock:
            if not voice_state.running:
                break

        try:
            with voice_state.lock:
                voice_state.is_recording = True

            audio = _record_until_silence(samplerate=SAMPLERATE)

            with voice_state.lock:
                voice_state.is_recording = False

            if audio is None:
                continue

            path = "voice_chunk.wav"
            sf.write(path, audio, SAMPLERATE)
            _transcribe_and_process(path)

        except Exception as e:
            with voice_state.lock:
                voice_state.is_recording = False
                voice_state.last_transcript = f"[Erreur loop: {e}]"
            time.sleep(1)

def _transcribe_and_process(path: str):
    try:
        groq = _get_groq()
        with open(path, "rb") as f:
            result = groq.audio.transcriptions.create(
                file=(path, f),
                model="whisper-large-v3",
                language=None,
                response_format="verbose_json",
                prompt="français, anglais, darija algérienne, kabyle"
            )
        text = (result.text or "").strip()
        lang = getattr(result, 'language', 'fr')

        if not text or len(text) < 3:
            return

        # Filtre hallucinations connues de Whisper
        HALLUCINATIONS = [
            "thank you for watching", "thanks for watching",
            "sous-titres", "sous titres", "subtitles by",
            "transcribed by", "amara.org", "www.", ".com",
            "♪", "[music]", "[silence]", "...",
        ]
        if any(h in text.lower() for h in HALLUCINATIONS):
            return

        # Filtre longueur suspecte (hallucination souvent très courte)
        if len(text.split()) < 2:
            return

        ACCEPTED = {"fr", "en", "ar", "french", "english", "arabic"}
        if lang.lower() not in ACCEPTED:
            return

        with voice_state.lock:
            voice_state.last_transcript = text

        text_lower = text.lower()

        # Wake word "Lumi" — variantes : lumi, loumi, loumy, lomy
        wake_variants = ["lumi", "loumi", "loumy", "lomy", "lumie", "lumy"]
        is_wake = any(v in text_lower for v in wake_variants)

        if is_wake:
            if "merci" in text_lower:
                with voice_state.lock:
                    voice_state.lumi_mode = False
                _play_tts("D'accord !")
                return
            with voice_state.lock:
                voice_state.lumi_mode = True
            if _on_lumi_question:
                _on_lumi_question(text)
            return

        # Mode Lumi actif
        with voice_state.lock:
            lumi_active = voice_state.lumi_mode
        if lumi_active:
            if _on_lumi_question:
                _on_lumi_question(text)
            return

        # Mode passif → analyse thème
        _analyze_topic(text, lang)

    except Exception as e:
        with voice_state.lock:
            voice_state.last_transcript = f"[Erreur transcription: {e}]"

def _analyze_topic(text: str, lang: str):
    try:
        groq = _get_groq()
        with voice_state.lock:
            session_theme = voice_state.session_theme

        incomprehension_kw = [
            "comprends pas", "compris pas", "je sais pas", "c'est quoi",
            "qu'est-ce que", "comment ça", "i don't understand",
            "mafhemtch", "ma3andich", "wach", "kifach"
        ]
        is_incomprehension = any(k in text.lower() for k in incomprehension_kw)

        prompt = f"""Étudiant dit : "{text}"
Thème session : "{session_theme}"
Réponds UNIQUEMENT en JSON valide :
{{"theme_detecte": "3 mots max", "dans_le_theme": true, "explication": "courte"}}"""

        resp = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            max_tokens=120, temperature=0.1,
        )
        raw  = resp.choices[0].message.content.strip().replace("```json","").replace("```","")
        data = json.loads(raw)
        theme    = data.get("theme_detecte", "inconnu")
        on_topic = data.get("dans_le_theme", True)

        if is_incomprehension:
            on_topic = True

        alert_msg = ""
        if not on_topic:
            with voice_state.lock:
                voice_state.off_topic_count += 1
                count = voice_state.off_topic_count
            alert_msg = f"⚠️ Hors sujet ({count}x) — tu parles de '{theme}'"
            _play_tts(f"Attention, tu parles de {theme}, recentre-toi !")
            if _on_alert:
                _on_alert(alert_msg)
        else:
            with voice_state.lock:
                voice_state.off_topic_count = 0

        with voice_state.lock:
            voice_state.last_theme  = theme
            voice_state.is_on_topic = on_topic
            voice_state.alert       = alert_msg
            voice_state.transcript_log.append({
                "time": time.strftime("%H:%M:%S"), "text": text,
                "lang": lang, "theme": theme, "on_topic": on_topic,
            })
    except Exception:
        pass

def set_session_theme(theme: str):
    with voice_state.lock:
        voice_state.session_theme = theme

def get_status() -> dict:
    with voice_state.lock:
        return {
            "running":         voice_state.running,
            "is_recording":    voice_state.is_recording,
            "last_transcript": voice_state.last_transcript,
            "last_theme":      voice_state.last_theme,
            "is_on_topic":     voice_state.is_on_topic,
            "alert":           voice_state.alert,
            "transcript_log":  list(voice_state.transcript_log[-10:]),
            "session_theme":   voice_state.session_theme,
            "lumi_mode":       voice_state.lumi_mode,
        }