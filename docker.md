# LUMI — Guide Docker

> Aya Mecheri · Maissa Lajimi · Mazilda Zehraoui — Master SISE 2025–2026

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé
- Clé API Groq ([console.groq.com](https://console.groq.com))

---

## Structure des fichiers Docker

```
lumi/
├── Dockerfile              # Image principale
├── docker-compose.yml      # Orchestration + volume + audio
├── .dockerignore           # Fichiers exclus du build
└── .streamlit/
    └── config.toml         # Config Streamlit (thème violet, headless)
```

---

## Démarrage rapide

### 1. Créer le fichier `.env`

```bash
# À la racine du projet
echo "GROQ_API_KEY=ta_cle_groq_ici" > .env
```

### 2. Builder et lancer

```bash
docker-compose up --build
```

### 3. Ouvrir dans le navigateur

```
http://localhost:8501
```

---

## Commandes utiles

```bash
# Lancer en arrière-plan
docker-compose up -d

# Voir les logs en temps réel
docker-compose logs -f lumi

# Arrêter
docker-compose down

# Arrêter ET supprimer le volume (reset DB)
docker-compose down -v

# Rebuild après modification du code
docker-compose up --build

# Entrer dans le conteneur (debug)
docker exec -it lumi-app bash
```

---

## Architecture Docker

```
┌─────────────────────────────────────────┐
│         HOST (ton PC)                   │
│                                         │
│  .env ──────────────────┐              │
│  /dev/snd (micro/audio) │              │
│                         ▼              │
│  ┌──────────────────────────────────┐  │
│  │   CONTENEUR lumi-app             │  │
│  │                                  │  │
│  │   Python 3.10-slim               │  │
│  │   Streamlit :8501                │  │
│  │   MediaPipe + OpenCV             │  │
│  │   Whisper (via Groq API)         │  │
│  │   gTTS + sounddevice             │  │
│  │                                  │  │
│  │   /app/data/lumi.db ──────────┐  │  │
│  └───────────────────────────────│──┘  │
│                                  │      │
│  PORT 8501 ◄──── localhost:8501  │      │
│                                  │      │
│  ┌───────────────────────────────▼──┐  │
│  │   VOLUME lumi-data (persistant)  │  │
│  │   → lumi.db sauvegardée          │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Variables d'environnement

| Variable | Obligatoire | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Oui | Clé API Groq (LLM + Whisper) |
| `DB_PATH` | Non | Chemin SQLite (défaut: `lumi.db`) |

---

## Persistance des données

La base SQLite est stockée dans un **volume Docker nommé** `lumi-data` :

```bash
# Localisation sur le host
docker volume inspect lumi_lumi-data

# Sauvegarder la DB
docker cp lumi-app:/app/data/lumi.db ./backup_lumi.db

# Restaurer la DB
docker cp ./backup_lumi.db lumi-app:/app/data/lumi.db
```

---

## Note sur l'audio

L'accès au microphone et aux haut-parleurs nécessite de partager le device audio du host :

```yaml
# Dans docker-compose.yml (déjà configuré)
devices:
  - /dev/snd:/dev/snd
group_add:
  - audio
```

> **Windows** : l'accès direct à `/dev/snd` n'est pas disponible.
> Le TTS (gTTS) fonctionnera via fichier temporaire.
> Le micro Whisper fonctionne via le navigateur (WebRTC).

---

## Troubleshooting

| Problème | Solution |
|---|---|
| `Port 8501 already in use` | `docker-compose down` puis relancer |
| `GROQ_API_KEY not found` | Vérifier que `.env` est à la racine |
| Audio muet | Vérifier que PulseAudio tourne sur le host |
| DB perdue après `down` | Utiliser `down` sans `-v` pour garder le volume |
| Build très long | Normal, MediaPipe est lourd (~500MB) |

---

<sub>● LUMI · Master SISE 2025–2026</sub>
