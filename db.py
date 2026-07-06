#!/usr/bin/env python3
# db.py — SQLite database for user authentication and scan history
import sqlite3
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
import secrets
from medicine_matcher import build_medicine_profile, compare_medicine_profiles

DB_PATH = os.path.join(os.path.dirname(__file__), "sanjeevani.db")


def _get_conn():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _backfill_formulation_variants(cursor: sqlite3.Cursor) -> None:
    rows = cursor.execute(
        """
        SELECT id, name, unit
        FROM medicines
        WHERE formulation_variant IS NULL OR formulation_variant = ''
        """
    ).fetchall()
    if not rows:
        return
    updates = []
    for row in rows:
        profile = build_medicine_profile({"name": row["name"], "unit": row["unit"] or ""})
        updates.append((profile["formulation_variant"], row["id"]))
    cursor.executemany("UPDATE medicines SET formulation_variant = ? WHERE id = ?", updates)


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
            poor_review_pct INTEGER,
            price REAL,
            is_discontinued INTEGER DEFAULT 0,
            medicine_type TEXT,
            composition_key TEXT,
            ingredient_key TEXT,
            dosage_form TEXT,
            route TEXT,
            release_type TEXT,
            formulation_variant TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicine_alternatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT NOT NULL,
            medicine_composition TEXT,
            alternate_name TEXT NOT NULL,
            alternate_composition TEXT,
            manufacturer TEXT,
            price REAL,
            reason TEXT,
            source TEXT DEFAULT 'doctor_curated',
            status TEXT DEFAULT 'doctor_curated',
            created_by TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(medicine_name, alternate_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            password_hash TEXT,
            role TEXT,
            phone TEXT,
            email TEXT,
            otp TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(medicines)")
    medicine_columns = {row[1] for row in cursor.fetchall()}
    medicine_migrations = {
        "price": "REAL", "is_discontinued": "INTEGER DEFAULT 0",
        "medicine_type": "TEXT", "composition_key": "TEXT",
        "ingredient_key": "TEXT", "dosage_form": "TEXT", "route": "TEXT",
        "release_type": "TEXT", "formulation_variant": "TEXT",
        "created_at": "TEXT",
    }
    for column, definition in medicine_migrations.items():
        if column not in medicine_columns:
            cursor.execute(f"ALTER TABLE medicines ADD COLUMN {column} {definition}")
    _backfill_formulation_variants(cursor)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_name ON medicines(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_composition ON medicines(composition)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_composition_key ON medicines(composition_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_ingredient_key ON medicines(ingredient_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_form_route_release ON medicines(dosage_form, route, release_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_formulation_variant ON medicines(formulation_variant)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_discontinued ON medicines(is_discontinued)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_medicines_alternate_lookup ON medicines(composition_key, is_discontinued, dosage_form, route, release_type)")

    # Alter table if role column doesn't exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if "role" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'patient'")
    if "phone" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "email" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

    # Alter table if email column doesn't exist on otp_verifications
    cursor.execute("PRAGMA table_info(otp_verifications)")
    otp_columns = [row[1] for row in cursor.fetchall()]
    if "email" not in otp_columns:
        cursor.execute("ALTER TABLE otp_verifications ADD COLUMN email TEXT")

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


def register_user(username: str, password: str, role: str = "patient", email: str = None) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    
    if len(password) > 128:
        return False, "Password cannot be more than 128 characters"
    if role not in ("patient", "doctor"):
        role = "patient"

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (username.strip().lower(), _hash_password(password), role, email, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose a different one."
    finally:
        conn.close()


def register_user_with_hash(username: str, password_hash: str, role: str = "patient", email: str = None) -> tuple[bool, str]:
    """Register a new user with an already-computed password hash. Returns (success, message)."""
    if not username or not password_hash:
        return False, "Username and password are required."
    if role not in ("patient", "doctor"):
        role = "patient"

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (username.strip().lower(), password_hash, role, email, datetime.now(timezone.utc).isoformat())
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
    if len(new_password) > 128:
        return False, "Password cannot be more than 128 characters."
    
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
    if len(password) > 128:
        return False, None, None

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
        (user_id, scan_type, language, json.dumps(result_data, ensure_ascii=False), datetime.now(timezone.utc).isoformat())
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
            (medicine_name.strip().lower(), json.dumps(result_data, ensure_ascii=False), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def search_medicines(query: str, limit: int = 15) -> list[dict]:
    """Search medicines in the local medicines lookup table sorted by match relevance."""
    if not query:
        return []
    conn = _get_conn()
    try:
        q_lower = query.lower().strip()
        rows = conn.execute(
            """
            SELECT id, name, unit, composition, uses, side_effects, manufacturer,
                   price, is_discontinued, medicine_type, dosage_form, route,
                   release_type, formulation_variant
            FROM medicines
            WHERE name LIKE ? AND COALESCE(is_discontinued, 0) = 0
            ORDER BY 
                CASE 
                    -- Exact match (case-insensitive)
                    WHEN LOWER(name) = ? THEN 1
                    
                    -- Starts with query as a full word (e.g. "Dolo 650", "Dolo-M")
                    WHEN LOWER(name) LIKE ? AND (SUBSTR(LOWER(name), LENGTH(?)+1, 1) NOT BETWEEN 'a' AND 'z') THEN 2
                    
                    -- Starts with query as a prefix of a word (e.g. "Dolonex")
                    WHEN LOWER(name) LIKE ? THEN 3
                    
                    -- Contains query as a full word (e.g. "Vitamin Dolo")
                    WHEN LOWER(name) LIKE ? AND (SUBSTR(LOWER(name), INSTR(LOWER(name), ?) + LENGTH(?), 1) NOT BETWEEN 'a' AND 'z') THEN 4
                    
                    -- Substring match (e.g. "Aldoloc")
                    ELSE 5
                END,
                name ASC
            LIMIT ?
            """,
            (
                f"%{query}%",
                q_lower,
                f"{q_lower}%",
                q_lower,
                f"{q_lower}%",
                f"% {q_lower}%",
                q_lower,
                q_lower,
                limit
            )
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
                ,"price": row["price"]
                ,"isDiscontinued": bool(row["is_discontinued"])
                ,"medicineType": row["medicine_type"]
                ,"dosageForm": row["dosage_form"]
                ,"route": row["route"]
                ,"releaseType": row["release_type"]
                ,"formulationVariant": row["formulation_variant"]
                ,"id": row["id"]
            })
        return results
    except Exception as e:
        print(f"[WARN] Error searching medicines: {e}")
        return []
    finally:
        conn.close()


ALTERNATE_WARNINGS = [
    "Use-case/indication is not available in the local CSV.",
    "Do not substitute without doctor/pharmacist approval.",
    "Verify allergies, contraindications, interactions, pregnancy status, age, renal/hepatic status, and patient-specific suitability.",
]
FORMULATION_REVIEW_WARNING = (
    "Selected medicine may have a special formulation such as fast absorption. "
    "Verify formulation equivalence before substitution."
)


def _alternate_response(row: dict, comparison: dict, curated: bool = False) -> dict:
    formulation_review = not comparison.get("formulationMatch", True)
    status = "doctor_curated" if curated else "review_required"
    if curated:
        status_label = "Doctor/pharmacist curated"
        confidence_score = 100
    elif formulation_review:
        status_label = "Composition match — formulation review required"
        confidence_score = 85
    else:
        status_label = "Composition/form match - use-case review required"
        confidence_score = 95
    warnings = list(ALTERNATE_WARNINGS)
    if formulation_review:
        warnings.insert(0, FORMULATION_REVIEW_WARNING)
    return {
        "medicineName": row.get("name") or row.get("alternate_name"),
        "activeSalts": row.get("composition") or row.get("alternate_composition") or "",
        "manufacturer": row.get("manufacturer") or "",
        "price": row.get("price"),
        "unit": row.get("unit") or "",
        "source": "doctor_curated" if curated else "local_database",
        "substitutionSafety": status,
        "confidenceScore": confidence_score,
        "statusLabel": status_label,
        "compositionMatch": "exact",
        "formMatch": comparison["formMatch"],
        "routeMatch": comparison["routeMatch"],
        "releaseMatch": comparison["releaseMatch"],
        "formulationMatch": comparison.get("formulationMatch", True),
        "useCaseStatus": status,
        "matchReasons": comparison["matchReasons"],
        "safetyWarnings": warnings,
        "reason": row.get("reason") or "",
        "createdBy": row.get("created_by") or "",
    }


def get_medicine_alternatives(medicine_name: str, limit: int = 10) -> list[dict]:
    """Return strict local and manually curated alternate candidates."""
    if not medicine_name:
        return []
    conn = _get_conn()
    try:
        selected_row = conn.execute("SELECT * FROM medicines WHERE name = ? LIMIT 1", (medicine_name.strip(),)).fetchone()
        if not selected_row:
            selected_row = conn.execute(
                "SELECT * FROM medicines WHERE LOWER(name) = LOWER(?) LIMIT 1", (medicine_name.strip(),)
            ).fetchone()
        if not selected_row:
            return []
        selected = build_medicine_profile(dict(selected_row))
        if (
            not selected["composition_key"]
            or selected["composition"].casefold() in {"not specified", "unknown", "n/a"}
            or selected.get("medicine_type") == "ai_generated"
        ):
            return []

        curated_rows = conn.execute(
            """
            SELECT ma.*, m.unit, m.dosage_form, m.route, m.release_type,
                   m.formulation_variant,
                   m.composition_key, m.ingredient_key, m.is_discontinued
            FROM medicine_alternatives ma
            LEFT JOIN medicines m ON LOWER(m.name) = LOWER(ma.alternate_name)
            WHERE LOWER(ma.medicine_name) = LOWER(?)
              AND ma.status = 'doctor_curated'
              AND COALESCE(m.is_discontinued, 0) = 0
            ORDER BY ma.alternate_name COLLATE NOCASE
            """,
            (selected["name"],),
        ).fetchall()
        candidates = conn.execute(
            """
            SELECT * FROM medicines
            WHERE composition_key = ?
              AND LOWER(name) != LOWER(?)
              AND COALESCE(is_discontinued, 0) = 0
              AND COALESCE(medicine_type, '') != 'ai_generated'
              AND dosage_form = ? AND route = ? AND release_type = ?
            ORDER BY CASE WHEN price IS NULL OR price <= 0 THEN 1 ELSE 0 END,
                     price ASC, name COLLATE NOCASE ASC
            LIMIT 100
            """,
            (
                selected["composition_key"], selected["name"], selected["dosage_form"],
                selected["route"], selected["release_type"],
            ),
        ).fetchall()

        output: list[dict] = []
        seen: set[str] = set()
        for raw in curated_rows:
            row = dict(raw)
            candidate = build_medicine_profile({
                "name": row["alternate_name"],
                "composition": row["alternate_composition"],
                "unit": row.get("unit") or "",
                "dosage_form": row.get("dosage_form") or "",
                "route": row.get("route") or "",
                "release_type": row.get("release_type") or "",
                "formulation_variant": row.get("formulation_variant") or "",
                "composition_key": row.get("composition_key") or "",
            })
            comparison = compare_medicine_profiles(selected, candidate)
            if comparison["eligible"]:
                output.append(_alternate_response(row, comparison, curated=True))
                seen.add(row["alternate_name"].casefold())

        for raw in candidates:
            row = dict(raw)
            if row["name"].casefold() in seen:
                continue
            comparison = compare_medicine_profiles(selected, row)
            if comparison["eligible"]:
                output.append(_alternate_response(row, comparison))
                seen.add(row["name"].casefold())
            if len(output) >= limit:
                break
        return output[:limit]
    finally:
        conn.close()


def save_medicine_alternative(data: dict) -> tuple[bool, str]:
    required = ("medicineName", "alternateName", "reason", "createdBy")
    missing = [field for field in required if not str(data.get(field) or "").strip()]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    conn = _get_conn()
    try:
        selected_row = conn.execute(
            "SELECT * FROM medicines WHERE LOWER(name) = LOWER(?) LIMIT 1",
            (data["medicineName"].strip(),),
        ).fetchone()
        candidate_row = conn.execute(
            "SELECT * FROM medicines WHERE LOWER(name) = LOWER(?) AND COALESCE(is_discontinued, 0) = 0 LIMIT 1",
            (data["alternateName"].strip(),),
        ).fetchone()
        if not selected_row or not candidate_row:
            return False, "Both medicines must exist as active products in the local database."
        if selected_row["medicine_type"] == "ai_generated" or candidate_row["medicine_type"] == "ai_generated":
            return False, "AI-generated catalog entries cannot be used for alternate curation."
        comparison = compare_medicine_profiles(dict(selected_row), dict(candidate_row))
        if not comparison["eligible"]:
            return False, "Curated alternate rejected: " + "; ".join(comparison["blockReasons"])
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO medicine_alternatives (
                medicine_name, medicine_composition, alternate_name,
                alternate_composition, manufacturer, price, reason,
                source, status, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'doctor_curated', 'doctor_curated', ?, ?)
            ON CONFLICT(medicine_name, alternate_name) DO UPDATE SET
                medicine_composition=excluded.medicine_composition,
                alternate_composition=excluded.alternate_composition,
                manufacturer=excluded.manufacturer, price=excluded.price,
                reason=excluded.reason, created_by=excluded.created_by,
                created_at=excluded.created_at
            """,
            (
                selected_row["name"], selected_row["composition"],
                candidate_row["name"], candidate_row["composition"],
                candidate_row["manufacturer"], candidate_row["price"],
                str(data["reason"]).strip(), str(data["createdBy"]).strip(), now,
            ),
        )
        conn.commit()
        return True, "Doctor/pharmacist-curated alternate saved."
    except sqlite3.IntegrityError as exc:
        return False, f"Could not save curated alternate: {exc}"
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
            ALLOWED_TABLES = {"users", "scan_history", "drug_cache", "prescription_cache", "medicines"}
            for table in tables:
                if table == "sqlite_sequence":
                    continue
                if table not in ALLOWED_TABLES:
                    print(f"[WARN] Blocked potential SQL injection in table query: {table}")
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
            (ocr_hash, json.dumps(result_data, ensure_ascii=False), ocr_text, ocr_hash, datetime.now(timezone.utc).isoformat())
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
                (ocr_hash, json.dumps(corrected_json, ensure_ascii=False), ocr_text, datetime.now(timezone.utc).isoformat())
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
                (ocr_hash, json.dumps(corrected_json, ensure_ascii=False), datetime.now(timezone.utc).isoformat())
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
    profile = build_medicine_profile({"name": name, "composition": composition, "unit": unit})
    created_at = datetime.now(timezone.utc).isoformat()
    
    conn = _get_conn()
    try:
        # Save under AI corrected name
        conn.execute(
            """
            INSERT OR IGNORE INTO medicines (
                name, unit, composition, uses, side_effects, manufacturer,
                excellent_review_pct, average_review_pct, poor_review_pct,
                is_discontinued, medicine_type, composition_key, ingredient_key,
                dosage_form, route, release_type, formulation_variant, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'ai_generated', ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, unit, composition, uses, side_effects, manufacturer, 0, 0, 0,
             profile["composition_key"], profile["ingredient_key"], profile["dosage_form"],
             profile["route"], profile["release_type"], profile["formulation_variant"], created_at)
        )
        
        # Also save under search query if different so subsequent lookups hit the DB
        if query and query.strip() and query.strip().lower() != name.lower():
            query_name = query.strip()
            conn.execute(
                """
                INSERT OR IGNORE INTO medicines (
                    name, unit, composition, uses, side_effects, manufacturer,
                    excellent_review_pct, average_review_pct, poor_review_pct,
                    is_discontinued, medicine_type, composition_key, ingredient_key,
                    dosage_form, route, release_type, formulation_variant, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'ai_generated', ?, ?, ?, ?, ?, ?, ?)
                """,
                (query_name, unit, composition, uses, side_effects, manufacturer, 0, 0, 0,
                 profile["composition_key"], profile["ingredient_key"], profile["dosage_form"],
                 profile["route"], profile["release_type"], profile["formulation_variant"], created_at)
            )
            
        conn.commit()
        return True
    except Exception as e:
        print(f"[WARN] Error saving custom medicine: {e}")
        return False
    finally:
        conn.close()


def send_email_otp(to_email: str, subject: str, body: str) -> bool:
    """Send an email using Resend REST API or SMTP fallback."""
    import urllib.request
    import urllib.parse
    import json
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    resend_key = os.getenv("RESEND_API_KEY")
    sender_email = os.getenv("SMTP_SENDER", "onboarding@resend.dev")

    # 1. Try Resend REST API if key is present
    if resend_key:
        url = "https://api.resend.com/emails"
        payload = {
            "from": f"Sanjeevani <{sender_email}>",
            "to": [to_email],
            "subject": subject,
            "text": body
        }
        headers = {
            "Authorization": f"Bearer {resend_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                print(f"[RESEND] Email successfully sent to {to_email}: {res_json}")
                return "id" in res_json
        except Exception as e:
            print(f"[ERROR] Resend API failed: {e}")
            # If Resend API fails, fallback to SMTP if configured

    # 2. Try Brevo REST API if key is present
    brevo_key = os.getenv("BREVO_API_KEY")
    if brevo_key:
        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {"email": sender_email, "name": "Sanjeevani"},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body
        }
        headers = {
            "api-key": brevo_key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                print(f"[BREVO] Email successfully sent to {to_email}: {res_json}")
                return "messageId" in res_json
        except Exception as e:
            print(f"[ERROR] Brevo API failed: {e}")

    # 3. Try SMTP fallback if configured
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if smtp_server and smtp_username and smtp_password:
        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            port_val = int(smtp_port)
            if port_val == 465:
                server = smtplib.SMTP_SSL(smtp_server, port_val, timeout=8)
            else:
                server = smtplib.SMTP(smtp_server, port_val, timeout=8)
                server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(msg["From"], to_email, msg.as_string())
            server.close()
            print(f"[SMTP] Email successfully sent to {to_email}")
            return True
        except Exception as e:
            print(f"[ERROR] SMTP failed to send email: {e}")

    # 4. Fallback to console print if neither is configured
    if not resend_key and not brevo_key and not (smtp_server and smtp_username and smtp_password):
        print(f"\n[MOCK OTP EMAIL] To: {to_email}\nSubject: {subject}\nBody: {body}\n")
        return True

    return False



def create_otp_verification(username: str, action: str, password_hash: str = None, role: str = None, email: str = None) -> tuple[bool, str]:
    """Generate and send a 6-digit OTP code for registration or reset."""
    import secrets
    from datetime import datetime, timedelta, timezone
    
    # Generate a cryptographically secure random 6-digit OTP
    otp = f"{secrets.randbelow(900000) + 100000}"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    created_at = datetime.now(timezone.utc).isoformat()
    
    conn = _get_conn()
    try:
        # Clear existing OTPs for the same user & action
        conn.execute(
            "DELETE FROM otp_verifications WHERE LOWER(username) = ? AND action = ?",
            (username.strip().lower(), action)
        )
        conn.execute(
            """
            INSERT INTO otp_verifications (username, action, password_hash, role, email, otp, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (username.strip().lower(), action, password_hash, role, email, otp, expires_at, created_at)
        )
        conn.commit()
        
        # Prepare the email subject and body
        if action == "register":
            subject = "Sanjeevani Registration OTP"
            body = f"Welcome to Sanjeevani!\n\nYour 6-digit verification code (OTP) is {otp}.\nThis code expires in 5 minutes.\n\nThank you,\nSanjeevani Team"
        else:
            subject = "Sanjeevani Password Reset OTP"
            body = f"Hello,\n\nYou requested a password reset for your Sanjeevani account.\n\nYour 6-digit verification code (OTP) is {otp}.\nThis code expires in 5 minutes.\n\nIf you did not request this, please ignore this email.\n\nThank you,\nThe Sanjeevani Team"
            
        print(f"\n[OTP] Generated verification code for user '{username}' ({action}): {otp}\n")
        
        # Send Email if email is provided
        if email:
            send_email_otp(email, subject, body)
            
        return True, otp
    except Exception as e:
        print(f"[ERROR] Failed to create OTP verification: {e}")
        return False, ""
    finally:
        conn.close()


def verify_otp_verification(username: str, action: str, otp: str) -> tuple[bool, dict | None]:
    """Verify code correctness and expiration state. If valid, deletes the record."""
    from datetime import datetime, timezone
    
    conn = _get_conn()
    try:
        row = conn.execute(
            """
            SELECT * FROM otp_verifications 
            WHERE LOWER(username) = ? AND action = ? AND otp = ?
            """,
            (username.strip().lower(), action, otp.strip())
        ).fetchone()
        
        if not row:
            return False, None
            
        expires_at = datetime.fromisoformat(row["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            # Delete expired code
            conn.execute("DELETE FROM otp_verifications WHERE id = ?", (row["id"],))
            conn.commit()
            return False, None
            
        # Valid code: delete it and return its values
        res_data = dict(row)
        conn.execute("DELETE FROM otp_verifications WHERE id = ?", (row["id"],))
        conn.commit()
        return True, res_data
    except Exception as e:
        print(f"[ERROR] Failed to verify OTP verification: {e}")
        return False, None
    finally:
        conn.close()


def get_user_email(username: str) -> str | None:
    """Retrieve the email associated with a username."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT email FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
        return row["email"] if row else None
    except Exception:
        return None
    finally:
        conn.close()


# Initialize database on import
init_db()
