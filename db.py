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
        CREATE TABLE IF NOT EXISTS prescription_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ocr_hash TEXT UNIQUE NOT NULL,
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

    # Alter table if prescription_cache columns don't exist
    cursor.execute("PRAGMA table_info(prescription_cache)")
    cache_cols = [row[1] for row in cursor.fetchall()]
    if "ocr_text" not in cache_cols:
        cursor.execute("ALTER TABLE prescription_cache ADD COLUMN ocr_text TEXT")
    if "corrected" not in cache_cols:
        cursor.execute("ALTER TABLE prescription_cache ADD COLUMN corrected INTEGER DEFAULT 0")

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
    # Exclude common non-medical words from database matching to prevent false positives (Task 7 verification)
    EXCLUDED_COMMON_WORDS = {
        "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
        "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "could",
        "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had",
        "has", "have", "having", "he", "her", "here", "hers", "him", "himself", "his", "how", "if", "in",
        "into", "is", "it", "its", "itself", "more", "most", "my", "myself", "no", "nor", "not", "of", "off",
        "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
        "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
        "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very",
        "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would",
        "you", "your", "yours", "yourself", "yourselves",
        "clouds", "sunny", "photo", "day", "water", "sun", "life", "heart", "sky", "trees", "beautiful", "landscape",
        "image", "picture", "camera", "phone", "mobile", "screen", "screenshot", "glass", "wood", "table", "chair",
        "house", "room", "office", "work", "paper", "book", "page", "text", "file", "document", "date", "time", "year"
    }
    # Find all alphanumeric words/numbers of length > 3
    words = [w.strip() for w in re.split(r'[^a-zA-Z0-9]', ocr_lower) if len(w.strip()) > 3 and w.strip() not in EXCLUDED_COMMON_WORDS]
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


def find_cached_prescription(ocr_hash: str) -> dict | None:
    """Retrieve cached prescription details by MD5 hash of OCR text."""
    if not ocr_hash:
        return None
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT result_json FROM prescription_cache WHERE ocr_hash = ?",
            (ocr_hash,)
        ).fetchone()
        if row:
            return json.loads(row["result_json"])
        return None
    except Exception:
        return None
    finally:
        conn.close()


def cache_prescription(ocr_hash: str, result_data: dict, ocr_text: str = None):
    """Cache prescription details by MD5 hash of OCR text."""
    if not ocr_hash or not result_data:
        return
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO prescription_cache (ocr_hash, result_json, ocr_text, corrected, created_at)
            VALUES (?, ?, ?, COALESCE((SELECT corrected FROM prescription_cache WHERE ocr_hash = ?), 0), ?)
            """,
            (ocr_hash, json.dumps(result_data, ensure_ascii=False), ocr_text, ocr_hash, datetime.now().isoformat())
        )
        conn.commit()
    except Exception as e:
        print(f"[WARN] Error caching prescription: {e}")
    finally:
        conn.close()


def update_prescription_cache(ocr_hash: str, corrected_json: dict, ocr_text: str = None) -> bool:
    """Overwrite cached prescription with doctor-corrected details and mark it as corrected."""
    if not ocr_hash or not corrected_json:
        return False
    conn = _get_conn()
    try:
        if ocr_text:
            conn.execute(
                """
                INSERT OR REPLACE INTO prescription_cache (ocr_hash, result_json, ocr_text, corrected, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (ocr_hash, json.dumps(corrected_json, ensure_ascii=False), ocr_text, datetime.now().isoformat())
            )
        else:
            conn.execute(
                """
                INSERT INTO prescription_cache (ocr_hash, result_json, corrected, created_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(ocr_hash) DO UPDATE SET
                    result_json = excluded.result_json,
                    corrected = 1,
                    created_at = excluded.created_at
                """,
                (ocr_hash, json.dumps(corrected_json, ensure_ascii=False), datetime.now().isoformat())
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"[WARN] Error updating prescription cache feedback: {e}")
        return False
    finally:
        conn.close()


def get_recent_corrected_prescriptions(limit: int = 2) -> list[dict]:
    """Retrieve recently corrected prescriptions with original OCR text and JSON results for few-shot learning."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT ocr_text, result_json 
            FROM prescription_cache 
            WHERE corrected = 1 AND ocr_text IS NOT NULL AND ocr_text != ''
            ORDER BY id DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        results = []
        for row in rows:
            results.append({
                "ocr_text": row["ocr_text"],
                "result_json": json.loads(row["result_json"])
            })
        return results
    except Exception as e:
        print(f"[WARN] Error fetching recent corrected prescriptions: {e}")
        return []
    finally:
        conn.close()


def save_custom_medicine(med_data: dict, query: str = None) -> bool:
    """Insert a dynamically generated custom medicine into the SQLite database."""
    name = med_data.get("medicineName", "").strip()
    if not name:
        return False
    
    unit = med_data.get("unit", "").strip()
    composition = med_data.get("activeSalts", "").strip()
    uses = med_data.get("uses", "").strip()
    side_effects = med_data.get("sideEffects", "").strip()
    manufacturer = med_data.get("manufacturer", "").strip()
    
    conn = _get_conn()
    try:
        # Save under AI corrected name
        conn.execute(
            """
            INSERT OR REPLACE INTO medicines (
                name, unit, composition, uses, side_effects, manufacturer,
                excellent_review_pct, average_review_pct, poor_review_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, unit, composition, uses, side_effects, manufacturer, 0, 0, 0)
        )
        
        # Also save under search query if different so subsequent lookups hit the DB
        if query and query.strip() and query.strip().lower() != name.lower():
            query_name = query.strip()
            conn.execute(
                """
                INSERT OR REPLACE INTO medicines (
                    name, unit, composition, uses, side_effects, manufacturer,
                    excellent_review_pct, average_review_pct, poor_review_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (query_name, unit, composition, uses, side_effects, manufacturer, 0, 0, 0)
            )
            
        conn.commit()
        return True
    except Exception as e:
        print(f"[WARN] Error saving custom medicine: {e}")
        return False
    finally:
        conn.close()


# Initialize database on import
init_db()



