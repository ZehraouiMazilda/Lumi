import sqlite3
import json
import bcrypt
from datetime import datetime

DB_PATH = "lumi.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at   TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER,
        title        TEXT NOT NULL,
        theme        TEXT DEFAULT '',
        duration_sec REAL DEFAULT 0,
        created_at   TEXT DEFAULT (datetime('now')),
        updated_at   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        filename   TEXT NOT NULL,
        content    TEXT DEFAULT '',
        added_at   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        source_id  INTEGER,
        raw_text   TEXT NOT NULL,
        clean_text TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (source_id)  REFERENCES sources(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        role       TEXT NOT NULL,
        content    TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS voice_transcripts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   INTEGER NOT NULL,
        text         TEXT NOT NULL,
        lang         TEXT DEFAULT 'fr',
        theme        TEXT DEFAULT '',
        on_topic     INTEGER DEFAULT 1,
        mode         TEXT DEFAULT 'passive',
        created_at   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS distraction_events (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   INTEGER NOT NULL,
        event_type   TEXT NOT NULL,
        detail       TEXT DEFAULT '',
        created_at   TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )""")

    conn.commit()
    conn.close()

# ── Users ──────────────────────────────────────────────────────
def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_conn()
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", (username, hashed))
        conn.commit(); conn.close()
        return True, "Compte créé !"
    except sqlite3.IntegrityError:
        return False, "Nom d'utilisateur déjà pris."

def login_user(username, password):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return True, dict(row)
    return False, None

# ── Sessions ───────────────────────────────────────────────────
def create_session(title, user_id=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO sessions (title, user_id) VALUES (?,?)", (title, user_id))
    sid = cur.lastrowid
    conn.commit(); conn.close()
    return sid

def update_session(session_id, theme=None, duration_sec=None):
    conn = get_conn()
    if theme is not None:
        conn.execute("UPDATE sessions SET theme=?, updated_at=datetime('now') WHERE id=?", (theme, session_id))
    if duration_sec is not None:
        conn.execute("UPDATE sessions SET duration_sec=?, updated_at=datetime('now') WHERE id=?", (duration_sec, session_id))
    conn.commit(); conn.close()

def get_all_sessions(user_id=None):
    conn = get_conn()
    if user_id:
        rows = conn.execute("SELECT * FROM sessions WHERE user_id=? ORDER BY updated_at DESC", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_session(session_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ── Sources ────────────────────────────────────────────────────
def add_source(session_id, filename, content=""):
    conn = get_conn()
    cur = conn.execute("INSERT INTO sources (session_id, filename, content) VALUES (?,?,?)",
                       (session_id, filename, content))
    sid = cur.lastrowid
    conn.commit(); conn.close()
    return sid

def get_sources(session_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM sources WHERE session_id=? ORDER BY added_at", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_source(source_id):
    conn = get_conn()
    conn.execute("DELETE FROM sources WHERE id=?", (source_id,))
    conn.execute("DELETE FROM notes WHERE source_id=?", (source_id,))
    conn.commit(); conn.close()

# ── Notes ──────────────────────────────────────────────────────
def add_note(session_id, raw_text, clean_text, source_id=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO notes (session_id, source_id, raw_text, clean_text) VALUES (?,?,?,?)",
        (session_id, source_id, raw_text, clean_text))
    nid = cur.lastrowid
    conn.commit(); conn.close()
    return nid

def get_notes(session_id, source_id=None):
    conn = get_conn()
    if source_id:
        rows = conn.execute("SELECT * FROM notes WHERE session_id=? AND source_id=? ORDER BY created_at",
                            (session_id, source_id)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_note(note_id):
    conn = get_conn()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit(); conn.close()

# ── Chat ───────────────────────────────────────────────────────
def add_chat_message(session_id, role, content):
    conn = get_conn()
    conn.execute("INSERT INTO chat_messages (session_id, role, content) VALUES (?,?,?)",
                 (session_id, role, content))
    conn.commit(); conn.close()

def get_chat_messages(session_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM chat_messages WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Voice transcripts ──────────────────────────────────────────
def add_transcript(session_id, text, lang="fr", theme="", on_topic=True, mode="passive"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO voice_transcripts (session_id, text, lang, theme, on_topic, mode) VALUES (?,?,?,?,?,?)",
        (session_id, text, lang, theme, int(on_topic), mode))
    conn.commit(); conn.close()

def get_transcripts(session_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM voice_transcripts WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Distraction events ─────────────────────────────────────────
def add_distraction(session_id, event_type, detail=""):
    conn = get_conn()
    conn.execute("INSERT INTO distraction_events (session_id, event_type, detail) VALUES (?,?,?)",
                 (session_id, event_type, detail))
    conn.commit(); conn.close()

def get_distractions(session_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM distraction_events WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]