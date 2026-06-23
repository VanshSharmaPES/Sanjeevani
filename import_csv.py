"""Import the Indian medicine CSV with deterministic safety metadata."""
import io
import os
import re
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from itertools import repeat

import pandas as pd

from medicine_matcher import build_medicine_profile

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(__file__)
DB_PATH = os.path.join(ROOT, "sanjeevani.db")
CSV_PATH = os.path.join(ROOT, "A_Z_medicines_dataset_of_India.csv")
REQUIRED_COLUMNS = {
    "name", "price(₹)", "Is_discontinued", "manufacturer_name", "type",
    "pack_size_label", "short_composition1", "short_composition2",
}


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_price(value) -> float | None:
    try:
        cleaned = re.sub(r"[^0-9.]", "", clean(value))
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def parse_bool(value) -> int:
    return int(clean(value).casefold() in {"1", "true", "yes", "y"})


def create_schema(cursor: sqlite3.Cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS medicines")
    cursor.execute("""
        CREATE TABLE medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            unit TEXT,
            composition TEXT,
            uses TEXT,
            side_effects TEXT,
            image_url TEXT,
            manufacturer TEXT,
            excellent_review_pct INTEGER DEFAULT 0,
            average_review_pct INTEGER DEFAULT 0,
            poor_review_pct INTEGER DEFAULT 0,
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
    cursor.execute("CREATE INDEX idx_medicines_name ON medicines(name)")
    cursor.execute("CREATE INDEX idx_medicines_composition ON medicines(composition)")
    cursor.execute("CREATE INDEX idx_medicines_composition_key ON medicines(composition_key)")
    cursor.execute("CREATE INDEX idx_medicines_ingredient_key ON medicines(ingredient_key)")
    cursor.execute("CREATE INDEX idx_medicines_form_route_release ON medicines(dosage_form, route, release_type)")
    cursor.execute("CREATE INDEX idx_medicines_formulation_variant ON medicines(formulation_variant)")
    cursor.execute("CREATE INDEX idx_medicines_discontinued ON medicines(is_discontinued)")
    cursor.execute("CREATE INDEX idx_medicines_alternate_lookup ON medicines(composition_key, is_discontinued, dosage_form, route, release_type)")
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


def row_to_record(row: dict, created_at: str) -> tuple:
    name = clean(row.get("name"))
    unit = clean(row.get("pack_size_label"))
    comp1 = clean(row.get("short_composition1"))
    comp2 = clean(row.get("short_composition2"))
    composition = " + ".join(part for part in (comp1, comp2) if part) or "Not specified"
    profile = build_medicine_profile({"name": name, "composition": composition, "unit": unit})
    return (
        name, unit, composition, "", "", "", clean(row.get("manufacturer_name")),
        0, 0, 0, parse_price(row.get("price(₹)")), parse_bool(row.get("Is_discontinued")),
        clean(row.get("type")), profile["composition_key"], profile["ingredient_key"],
        profile["dosage_form"], profile["route"], profile["release_type"],
        profile["formulation_variant"], created_at,
    )


def run_migration() -> None:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
    print("Connecting to SQLite database...")
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        create_schema(cursor)
        conn.commit()
        created_at = datetime.now(timezone.utc).isoformat()
        inserted = 0
        read = 0
        sql = """
            INSERT OR IGNORE INTO medicines (
                name, unit, composition, uses, side_effects, image_url, manufacturer,
                excellent_review_pct, average_review_pct, poor_review_pct, price,
                is_discontinued, medicine_type, composition_key, ingredient_key,
                dosage_form, route, release_type, formulation_variant, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        workers = min(8, max(2, os.cpu_count() or 2))
        print(f"Generating safety profiles with {workers} workers...")
        with ProcessPoolExecutor(max_workers=workers) as executor:
            for frame in pd.read_csv(CSV_PATH, dtype=str, chunksize=20000, keep_default_na=False):
                missing = REQUIRED_COLUMNS.difference(frame.columns)
                if missing:
                    raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
                rows = [row for row in frame.to_dict("records") if clean(row.get("name"))]
                records = list(executor.map(row_to_record, rows, repeat(created_at), chunksize=500))
                before = conn.total_changes
                cursor.executemany(sql, records)
                inserted += conn.total_changes - before
                read += len(frame)
                conn.commit()
                print(f"Processed {read:,} rows...", flush=True)
        total = cursor.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
        active = cursor.execute("SELECT COUNT(*) FROM medicines WHERE is_discontinued = 0").fetchone()[0]
        print(f"Import completed: {inserted:,} unique rows ({active:,} active; {total - active:,} discontinued).")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
