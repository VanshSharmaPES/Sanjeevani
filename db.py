#!/usr/bin/env python3
# db.py — SQLite database for user authentication and scan history
import sqlite3
import hashlib
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "sanjeevani.db")


def _get_conn():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            scan_type TEXT NOT NULL,
            language TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a static salt."""
    salted = f"sanjeevani_{password}_salt"
    return hashlib.sha256(salted.encode()).hexdigest()


def register_user(username: str, password: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username.strip().lower(), _hash_password(password), datetime.now().isoformat())
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose a different one."
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> tuple[bool, int | None]:
    """Authenticate a user. Returns (success, user_id)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (username.strip().lower(),)
    ).fetchone()
    conn.close()

    if row is None:
        return False, None
    if row["password_hash"] == _hash_password(password):
        return True, row["id"]
    return False, None


def save_scan(user_id: int, scan_type: str, language: str, result_data: dict):
    """Save a scan result for a user."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO scan_history (user_id, scan_type, language, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, scan_type, language, json.dumps(result_data, ensure_ascii=False), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_user_history(user_id: int, limit: int = 50) -> list[dict]:
    """Get scan history for a user, most recent first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, scan_type, language, result_json, created_at FROM scan_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()

    history = []
    for row in rows:
        entry = {
            "id": row["id"],
            "scan_type": row["scan_type"],
            "language": row["language"],
            "result": json.loads(row["result_json"]),
            "created_at": row["created_at"]
        }
        history.append(entry)
    return history


def delete_scan(user_id: int, scan_id: int) -> bool:
    """Delete a specific scan entry for a user."""
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM scan_history WHERE id = ? AND user_id = ?",
        (scan_id, user_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# Initialize database on import
init_db()
