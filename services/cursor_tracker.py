"""
Cursor Tracker — injecte JS pour détecter :
- Inactivité curseur > 5min
- Changement d'onglet
Et renvoie les données vers Streamlit via query params
"""
import streamlit as st

CURSOR_JS = """
<script>
(function(){
    const INACTIVITY_LIMIT = 5 * 60 * 1000; // 5 min
    let lastActivity = Date.now();
    let tabHiddenSince = null;

    // ── Activité curseur + clavier ───────────────────────────
    function resetActivity(){
        lastActivity = Date.now();
        const w = document.getElementById('cursor-warning');
        if(w) w.style.display = 'none';
        // Envoie idle=0 à Streamlit
        window._stIdleSecs = 0;
    }
    document.addEventListener('mousemove', resetActivity);
    document.addEventListener('keydown',   resetActivity);
    document.addEventListener('click',     resetActivity);
    document.addEventListener('scroll',    resetActivity);

    // Vérifie inactivité toutes les 10s
    setInterval(() => {
        const idleMs   = Date.now() - lastActivity;
        const idleSecs = Math.floor(idleMs / 1000);
        window._stIdleSecs = idleSecs;

        const w = document.getElementById('cursor-warning');
        if(idleMs > INACTIVITY_LIMIT){
            if(w){
                const mins = Math.floor(idleMs / 60000);
                const el   = w.querySelector('#idle-time');
                if(el) el.textContent = mins + ' min';
                w.style.display = 'flex';
            }
        }
    }, 10000);

    // ── Changement d'onglet ──────────────────────────────────
    document.addEventListener('visibilitychange', () => {
        const tabW = document.getElementById('tab-warning');
        if(document.hidden){
            tabHiddenSince = Date.now();
            window._stTabHidden = true;
            if(tabW) tabW.style.display = 'flex';
        } else {
            window._stTabHidden = false;
            if(tabW) tabW.style.display = 'none';
        }
    });

    // Expose les valeurs pour lecture Streamlit (via composant)
    window._stIdleSecs  = 0;
    window._stTabHidden = false;
})();
</script>

<!-- Warning curseur inactif -->
<div id="cursor-warning" style="
    display:none; position:fixed; bottom:24px; right:24px; z-index:9999;
    background:white; border:2px solid #f97316; border-radius:16px;
    padding:14px 20px; box-shadow:0 8px 32px rgba(249,115,22,0.25);
    flex-direction:column; gap:4px; max-width:280px;
    font-family:'Plus Jakarta Sans',sans-serif;
">
    <div style="font-weight:700; color:#f97316; font-size:0.9rem;">
        🖱️ Tu es toujours là ?
    </div>
    <div style="font-size:0.78rem; color:#78716c; line-height:1.5;">
        Inactif depuis <b id="idle-time">5 min</b><br>
        Bouge ta souris si tu travailles !
    </div>
</div>

<!-- Warning changement d'onglet -->
<div id="tab-warning" style="
    display:none; position:fixed; top:20px; left:50%;
    transform:translateX(-50%); z-index:9999;
    background:white; border:2px solid #ef4444; border-radius:16px;
    padding:14px 24px; box-shadow:0 8px 32px rgba(239,68,68,0.25);
    flex-direction:row; align-items:center; gap:12px;
    font-family:'Plus Jakarta Sans',sans-serif;
">
    <div style="font-size:1.4rem;">🚨</div>
    <div>
        <div style="font-weight:700; color:#ef4444; font-size:0.9rem;">
            Tu as quitté la page !
        </div>
        <div style="font-size:0.75rem; color:#78716c;">
            Reviens te concentrer sur tes cours
        </div>
    </div>
</div>
"""

def inject_cursor_tracker():
    st.markdown(CURSOR_JS, unsafe_allow_html=True)