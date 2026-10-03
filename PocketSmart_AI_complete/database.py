import sqlite3
from contextlib import contextmanager
from pathlib import Path
from config import settings

DB_PATH = Path(__file__).resolve().parent / "pocketsmart.db"
if settings.database_url.startswith("sqlite:///"):
    raw = settings.database_url.replace("sqlite:///", "", 1)
    DB_PATH = (Path(__file__).resolve().parent / raw).resolve() if not Path(raw).is_absolute() else Path(raw)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            jti TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            planner_type TEXT NOT NULL,
            input_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_recommendations_user ON recommendations(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        """)

def create_user(username, email, password_hash):
    with get_db() as db:
        cur = db.execute("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)", (username, email, password_hash))
        return cur.lastrowid

def get_user_by_username(username):
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

def get_user_by_email(email):
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

def get_user(user_id):
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

def create_session(jti, user_id, expires_at):
    with get_db() as db:
        db.execute("INSERT INTO sessions(jti,user_id,expires_at) VALUES(?,?,?)", (jti, user_id, expires_at))

def get_session(jti):
    with get_db() as db:
        return db.execute("SELECT * FROM sessions WHERE jti=?", (jti,)).fetchone()

def revoke_session(jti):
    with get_db() as db:
        db.execute("UPDATE sessions SET revoked=1 WHERE jti=?", (jti,))

def create_recommendation(user_id, planner_type, input_json, result_json):
    with get_db() as db:
        cur = db.execute("INSERT INTO recommendations(user_id,planner_type,input_json,result_json) VALUES(?,?,?,?)", (user_id, planner_type, input_json, result_json))
        return cur.lastrowid

def get_recommendations(user_id, limit=50):
    with get_db() as db:
        return db.execute("SELECT * FROM recommendations WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()

def get_recommendation(user_id, recommendation_id):
    with get_db() as db:
        return db.execute("SELECT * FROM recommendations WHERE id=? AND user_id=?", (recommendation_id, user_id)).fetchone()
