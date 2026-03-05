"""
Voice Detector — version simple qui marche
Chunks fixes 5s → Whisper → résultat immédiat
"""
import threading
import time
import os
import io
import json
import numpy as np
from dotenv import load_dotenv
load_dotenv()

_DIR = os.path.dirname(os.path.abspath(__file__))
_WAV = os.path.join(_DIR, "chunk.wav")

def _get_groq():
    import httpx
    from groq import Groq
    return Groq(api_key=os.getenv("GROQ_API_KEY"), http_client=httpx.Client(verify=True))

class VoiceState:
    def __init__(self):
        self.lock            = threading.Lock()
        self.running         = False
        self.is_recording    = False
        self.last_transcript = ""
        self.lumi_mode       = False
        self.session_theme   = "général"
        self.alert           = ""
        self.transcript_log  = []

voice_state = VoiceState()
_on_lumi_question = None
_on_alert = None

def set_callbacks(on_lumi_question=None, on_alert=None):
    global _on_lumi_question, _on_alert
    _on_lumi_question = on_lumi_question
    _on_alert = on_alert

def play_tts(text: str):
    def _run():
        tmp = None
        try:
            from gtts import gTTS
            import tempfile, subprocess
            buf = io.BytesIO()
            gTTS(text=str(text)[:150], lang='fr', slow=False).write_to_fp(buf)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(buf.getvalue())
                tmp = f.name
            ps = (
                "Add-Type -AssemblyName presentationCore; "
                "$mp = New-Object System.Windows.Media.MediaPlayer; "
                f"$mp.Open([uri]'{tmp}'); "
                "$mp.Play(); Start-Sleep 5; $mp.Stop()"
            )
            subprocess.run(['powershell', '-NoProfile', '-c', ps],
                           timeout=10, capture_output=True)
        except Exception:
            try:
                import winsound
                winsound.Beep(880, 150); winsound.Beep(1100, 150)
            except: pass
        finally:
            if tmp:
                try: os.unlink(tmp)
                except: pass
    threading.Thread(target=_run, daemon=True).start()

def start_listening():
    with voice_state.lock:
        if voice_state.running:
            return
        voice_state.running = True
    threading.Thread(target=_loop, daemon=True).start()

def stop_listening():
    with voice_state.lock:
        voice_state.running = False

def _loop():
    import sounddevice as sd
    import soundfile as sf

    SAMPLERATE = 16000
    DURATION   = 5  # secondes fixes

    while True:
        with voice_state.lock:
            if not voice_state.running:
                break
        try:
            with voice_state.lock:
                voice_state.is_recording = True

            audio = sd.rec(int(DURATION * SAMPLERATE),
                           samplerate=SAMPLERATE, channels=1, dtype='float32')
            sd.wait()

            with voice_state.lock:
                voice_state.is_recording = False

            # Vérifie RMS — ignore silence complet
            rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
            if rms < 0.005:
                continue

            sf.write(_WAV, audio, SAMPLERATE)
            _transcribe(_WAV)

        except Exception as e:
            with voice_state.lock:
                voice_state.is_recording = False
                voice_state.last_transcript = f"[Erreur: {e}]"
            time.sleep(1)

_HALLUCINATIONS = [
    "thank you for watching", "thanks for watching",
    "sous-titres", "subtitles by", "transcribed by", "amara.org",
    "♪", "[music]", "[silence]",
]

def _transcribe(path: str):
    try:
        groq = _get_groq()
        with open(path, "rb") as f:
            res = groq.audio.transcriptions.create(
                file=(os.path.basename(path), f),
                model="whisper-large-v3",
                language="fr",
                response_format="verbose_json",
                prompt="français, darija algérienne, kabyle"
            )
        text = (res.text or "").strip()
        print(f"[VOICE] '{text}'", flush=True)

        if not text:
            return
        if any(h in text.lower() for h in _HALLUCINATIONS):
            return

        with voice_state.lock:
            voice_state.last_transcript = text

        tl = text.lower()
        wake = ["lumi", "loumi", "loumy", "lumy", "lumie"]
        if any(w in tl for w in wake):
            if "merci" in tl:
                with voice_state.lock:
                    voice_state.lumi_mode = False
                play_tts("D'accord, à bientôt !")
                return
            with voice_state.lock:
                voice_state.lumi_mode = True
            if _on_lumi_question:
                _on_lumi_question(text)
            return

        with voice_state.lock:
            active = voice_state.lumi_mode
        if active:
            if _on_lumi_question:
                _on_lumi_question(text)
            return

        # Mode passif — log seulement, pas d'analyse thème pour l'instant
        with voice_state.lock:
            voice_state.transcript_log.append({
                "time": time.strftime("%H:%M:%S"),
                "text": text,
            })

    except Exception as e:
        with voice_state.lock:
            voice_state.last_transcript = f"[Erreur transcription: {e}]"
        print(f"[VOICE ERROR] {e}", flush=True)

def set_session_theme(theme: str):
    with voice_state.lock:
        voice_state.session_theme = theme

def get_status() -> dict:
    with voice_state.lock:
        return {
            "running":         voice_state.running,
            "is_recording":    voice_state.is_recording,
            "last_transcript": voice_state.last_transcript,
            "lumi_mode":       voice_state.lumi_mode,
            "session_theme":   voice_state.session_theme,
            "alert":           voice_state.alert,
            "transcript_log":  list(voice_state.transcript_log[-10:]),
            "last_theme":      "",
            "is_on_topic":     True,
        }

_play_tts = play_tts