"""
Concentration Engine — fusion multi-signaux
Combine : Caméra (MediaPipe) + Comportement (curseur/onglet)
"""
import time
import threading
from collections import deque

class ConcentrationEngine:
    def __init__(self):
        self.lock = threading.Lock()

        # ── Signaux comportementaux (mis à jour via JS → Streamlit) ──
        self.tab_visible       = True     # onglet visible ?
        self.tab_hidden_since  = None     # timestamp départ onglet
        self.cursor_active     = True     # curseur actif ?
        self.cursor_idle_since = None     # timestamp début inactivité
        self.cursor_idle_secs  = 0        # secondes d'inactivité curseur

        # ── Score comportemental 0-100 ────────────────────────────
        self.behavior_score    = 100

        # ── Score final fusionné ──────────────────────────────────
        self.final_score       = 100
        self.final_history     = deque(maxlen=30)

        # ── Alertes ───────────────────────────────────────────────
        self.behavior_alert    = ""

        # ── Stats session ─────────────────────────────────────────
        self.tab_switches      = 0
        self.total_idle_secs   = 0
        self.session_start     = time.time()

    def update_tab(self, visible: bool):
        """Appelé quand l'onglet change de visibilité."""
        with self.lock:
            if not visible and self.tab_visible:
                # Vient de quitter l'onglet
                self.tab_hidden_since = time.time()
                self.tab_switches    += 1
            elif visible and not self.tab_visible:
                # Vient de revenir
                if self.tab_hidden_since:
                    self.total_idle_secs += time.time() - self.tab_hidden_since
                self.tab_hidden_since = None
            self.tab_visible = visible

    def update_cursor(self, idle_seconds: float):
        """Appelé périodiquement avec les secondes d'inactivité curseur."""
        with self.lock:
            self.cursor_idle_secs = idle_seconds
            self.cursor_active    = idle_seconds < 300  # < 5 min

    def _compute_behavior_score(self) -> int:
        """
        Score comportemental 0-100 :
        - Onglet caché       → 0
        - Curseur inactif    → dégradé progressif après 5min
        """
        with self.lock:
            tab_ok    = self.tab_visible
            idle_secs = self.cursor_idle_secs

        if not tab_ok:
            return 0

        # Dégradé curseur : 0 pénalité avant 5min, puis -10pts/min
        if idle_secs < 300:
            cursor_score = 100
        elif idle_secs < 600:   # 5-10 min
            cursor_score = int(100 - (idle_secs - 300) / 300 * 40)  # -40pts max
        else:
            cursor_score = 60   # plancher à 60 (peut quand même travailler)

        return cursor_score

    def compute_final(self, camera_score: int) -> int:
        """
        Fusion pondérée :
        Caméra      70%
        Comportement 30%
        """
        behavior = self._compute_behavior_score()

        with self.lock:
            self.behavior_score = behavior

            # Alerte comportementale
            if not self.tab_visible:
                self.behavior_alert = "🚨 Tu as quitté l'onglet !"
            elif self.cursor_idle_secs >= 300:
                mins = int(self.cursor_idle_secs // 60)
                self.behavior_alert = f"🖱️ Inactif depuis {mins} min"
            else:
                self.behavior_alert = ""

        final = int(camera_score * 0.70 + behavior * 0.30)

        with self.lock:
            self.final_history.append(final)
            # Lissage léger sur 10 points
            if len(self.final_history) >= 5:
                import numpy as np
                self.final_score = int(np.mean(list(self.final_history)[-10:]))
            else:
                self.final_score = final

        return self.final_score

    def get_status(self) -> dict:
        with self.lock:
            elapsed = time.time() - self.session_start
            return {
                "final_score":    self.final_score,
                "behavior_score": self.behavior_score,
                "tab_visible":    self.tab_visible,
                "cursor_idle":    self.cursor_idle_secs,
                "behavior_alert": self.behavior_alert,
                "tab_switches":   self.tab_switches,
                "total_idle":     self.total_idle_secs,
                "session_secs":   elapsed,
            }

# Instance globale
engine = ConcentrationEngine()