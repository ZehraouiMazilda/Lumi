# 🎯 MeetingAI — Analyse de réunion en temps réel

> Projet IA · Master SISE 2025–2026  
> Plateforme d'analyse intelligente de réunions : concentration, transcription, statistiques et résumé IA.

---

## ✨ Fonctionnalités

| Feature | Description | Techno |
|---|---|---|
| 🧠 Concentration | Détection du regard et des clignements en temps réel | MediaPipe Face Mesh |
| 📝 Transcription | Sous-titrage en direct | Whisper / saisie manuelle |
| 📊 Temps de parole | Stats et graphiques par participant | Plotly |
| ✨ Résumé IA | Compte-rendu structuré généré par LLM | Claude (Anthropic) |

---

## 🚀 Installation rapide

### Option 1 — Python local (recommandé)

```bash
# 1. Cloner / dézipper le projet
cd meeting-ai

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
streamlit run app.py
```

Ouvrir **http://localhost:8501** dans votre navigateur.

---

### Option 2 — Docker

```bash
# Build & run
docker-compose up --build

# Avec une clé Anthropic
ANTHROPIC_API_KEY=sk-ant-... docker-compose up --build
```

---

## 🔑 Clé API Anthropic (optionnel)

La clé API permet de générer un résumé intelligent avec Claude.  
Sans clé, un résumé de démonstration est généré automatiquement.

1. Créer un compte sur [console.anthropic.com](https://console.anthropic.com)
2. Générer une clé API
3. La coller dans le champ **"Clé API Anthropic"** au démarrage

---

## 📁 Structure du projet

```
meeting-ai/
├── app.py                  # Point d'entrée Streamlit + CSS global
├── pages/
│   ├── home.py             # Page d'accueil / configuration
│   ├── meeting.py          # Dashboard temps réel
│   └── summary.py          # Compte-rendu & statistiques
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🎬 Utilisation

1. **Page d'accueil** : Entrer le nom de la réunion, les participants, et optionnellement la clé API
2. **Réunion** : Autoriser l'accès à la webcam, sélectionner le locuteur actif, ajouter des lignes de transcription
3. **Résumé** : Cliquer "Terminer & résumé" pour accéder aux statistiques complètes et générer le résumé IA

---

## 🛠 Technologies utilisées

- **Streamlit** + **streamlit-webrtc** — Interface web + flux vidéo temps réel
- **MediaPipe Face Mesh** — Détection du visage et calcul EAR (Eye Aspect Ratio)
- **Plotly** — Graphiques interactifs
- **faster-whisper** — Transcription audio (prêt à brancher)
- **Anthropic Claude** — Génération du résumé IA

---

## 👥 Équipe

Master SISE 2025–2026 — Challenge IA Mars 2026
