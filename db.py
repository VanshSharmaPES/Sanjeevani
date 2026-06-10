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
            role TEXT DEFAULT 'patient',
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drug_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT UNIQUE NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            unit TEXT,
            composition TEXT,
            uses TEXT,
            side_effects TEXT,
            image_url TEXT,
            manufacturer TEXT,
            excellent_review_pct INTEGER,
            average_review_pct INTEGER,
            poor_review_pct INTEGER
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_name ON medicines(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_composition ON medicines(composition)")

    # Alter table if role column doesn't exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if "role" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'patient'")

    conn.commit()
    conn.close()

    # Register default test accounts for peer testing
    register_user("hemanth", "admin@123", "doctor")
    register_user("pranay", "admin@123", "doctor")
    register_user("vansh", "admin@123", "doctor")
    register_user("patient1", "sanjeevani_patient_2026", "patient")


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a static salt."""
    salted = f"sanjeevani_{password}_salt"
    return hashlib.sha256(salted.encode()).hexdigest()


def register_user(username: str, password: str, role: str = "patient") -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    if role not in ("patient", "doctor"):
        role = "patient"

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username.strip().lower(), _hash_password(password), role, datetime.now().isoformat())
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose a different one."
    finally:
        conn.close()


def reset_password(username: str, new_password: str) -> tuple[bool, str]:
    """Reset user's password."""
    if not username or not new_password:
        return False, "Username and new password are required."
    if len(new_password) < 4:
        return False, "Password must be at least 4 characters."
    
    conn = _get_conn()
    try:
        # Check if user exists
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
        if not row:
            return False, "User not found."
            
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (_hash_password(new_password), username.strip().lower())
        )
        conn.commit()
        return True, "Password reset successfully!"
    except Exception as e:
        return False, f"Failed to reset password: {e}"
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> tuple[bool, int | None, str | None]:
    """Authenticate a user. Returns (success, user_id, role)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, password_hash, role FROM users WHERE username = ?",
        (username.strip().lower(),)
    ).fetchone()
    conn.close()

    if row is None:
        return False, None, None
    if row["password_hash"] == _hash_password(password):
        return True, row["id"], row["role"]
    return False, None, None



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


def get_cached_drug(medicine_name: str) -> dict | None:
    """Retrieve cached drug details by name (case-insensitive normalized)."""
    if not medicine_name:
        return None
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT result_json FROM drug_cache WHERE LOWER(medicine_name) = ?",
            (medicine_name.strip().lower(),)
        ).fetchone()
        if row:
            return json.loads(row["result_json"])
        return None
    except Exception:
        return None
    finally:
        conn.close()


def find_cached_drug_by_ocr(ocr_text: str) -> dict | None:
    """Check if any cached medicine name is found as a substring in the OCR text."""
    if not ocr_text:
        return None
    ocr_lower = ocr_text.lower()
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT medicine_name, result_json FROM drug_cache").fetchall()
        for row in rows:
            name = row["medicine_name"].lower()
            if name in ocr_lower and len(name) > 3:
                return json.loads(row["result_json"])
        return None
    except Exception:
        return None
    finally:
        conn.close()


def find_db_drug_by_ocr(ocr_text: str) -> dict | None:
    """Check if any word in the OCR text matches a medicine name in the medicines table."""
    if not ocr_text:
        return None
    import re
    ocr_lower = ocr_text.lower()
    # Find all alphanumeric words/numbers of length > 3
    words = [w.strip() for w in re.split(r'[^a-zA-Z0-9]', ocr_lower) if len(w.strip()) > 3]
    if not words:
        return None
        
    conn = _get_conn()
    try:
        for word in words:
            # First search exact name match or prefix match
            row = conn.execute(
                """
                SELECT name, unit, composition, uses, side_effects, manufacturer 
                FROM medicines 
                WHERE LOWER(name) = ? OR LOWER(name) LIKE ?
                LIMIT 1
                """,
                (word, f"{word} %")
            ).fetchone()
            if row:
                return {
                    "is_medicine": True,
                    "medicine_name": row["name"],
                    "active_salts": [s.strip() for s in row["composition"].split("+") if s.strip()] if row["composition"] else [],
                    "dosage_strength": "N/A",
                    "is_high_dosage": False,
                    "dosage_info": "Normal dosage (database lookup fallback)",
                    "conditions": [s.strip() for s in row["uses"].split(",") if s.strip()] if row["uses"] else [],
                    "what_it_does": "Active ingredient acts on the target symptoms.",
                    "suitable_age_group": "Adults/Children (verify with practitioner)",
                    "advice": f"Medicine identified via lookup database: {row['name']} by {row['manufacturer']}. Salts: {row['composition']}."
                }
        return None
    except Exception as e:
        print(f"[WARN] Error in find_db_drug_by_ocr: {e}")
        return None
    finally:
        conn.close()


def cache_drug(medicine_name: str, result_data: dict):
    """Cache drug details by name."""
    if not medicine_name or not result_data:
        return
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO drug_cache (medicine_name, result_json, created_at) VALUES (?, ?, ?)",
            (medicine_name.strip().lower(), json.dumps(result_data, ensure_ascii=False), datetime.now().isoformat())
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def search_medicines(query: str, limit: int = 15) -> list[dict]:
    """Search medicines in the local medicines lookup table."""
    if not query:
        return []
    conn = _get_conn()
    try:
        # Search by name or composition using case-insensitive LIKE
        rows = conn.execute(
            """
            SELECT name, unit, composition, uses, side_effects, manufacturer
            FROM medicines
            WHERE name LIKE ? OR composition LIKE ?
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        
        results = []
        for row in rows:
            results.append({
                "medicineName": row["name"],
                "unit": row["unit"],
                "activeSalts": row["composition"],
                "uses": row["uses"],
                "sideEffects": row["side_effects"],
                "manufacturer": row["manufacturer"]
            })
        return results
    except Exception as e:
        print(f"[WARN] Error searching medicines: {e}")
        return []
    finally:
        conn.close()


def get_db_status() -> dict:
    """Get status of the database (existence, size, table row counts)."""
    status = {
        "db_path": DB_PATH,
        "db_exists": os.path.exists(DB_PATH),
    }
    if status["db_exists"]:
        status["db_size_bytes"] = os.path.getsize(DB_PATH)
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            status["tables"] = tables
            
            counts = {}
            for table in tables:
                if table == "sqlite_sequence":
                    continue
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                    counts[table] = cursor.fetchone()[0]
                except Exception as e:
                    counts[table] = f"Error: {e}"
            status["row_counts"] = counts
            conn.close()
        except Exception as e:
            status["error"] = str(e)
    return status


# Initialize database on import
init_db()


