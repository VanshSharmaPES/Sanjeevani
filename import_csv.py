import sqlite3
import pandas as pd
import os
import sys
import io

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

db_path = os.path.join(os.path.dirname(__file__), "sanjeevani.db")
csv_path = os.path.join(os.path.dirname(__file__), "A_Z_medicines_dataset_of_India.csv")

def run_migration():
    if not os.path.exists(csv_path):
        print(f"Error: CSV not found at {csv_path}")
        return

    print("🌿 Connecting to SQLite database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop table to ensure clean import of the new A-Z database
    print("🌿 Resetting medicines table...")
    cursor.execute("DROP TABLE IF EXISTS medicines")
    
    # 1. Create medicines table
    print("🌿 Creating medicines table and indexes...")
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

    # 2. Add role column to users if not present
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if "role" not in columns:
        print("🌿 Adding role column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'patient'")

    conn.commit()

    # 3. Read and clean CSV
    print("🌿 Reading new A-Z CSV data...")
    # Use chunksize or low_memory to optimize loading of ~32MB CSV
    df = pd.read_csv(csv_path, dtype=str)
    print(f"🌿 Read {len(df)} rows from CSV.")
    
    # Replace NaN with empty strings
    df = df.fillna("")

    print("🌿 Preparing records for bulk insertion...")
    records = []
    for _, row in df.iterrows():
        name = row['name'].strip()
        unit = row['pack_size_label'].strip()
        manufacturer = row['manufacturer_name'].strip()
        
        # Combine composition 1 and 2
        comp1 = row['short_composition1'].strip()
        comp2 = row['short_composition2'].strip()
        
        if comp1 and comp2:
            composition = f"{comp1} + {comp2}"
        elif comp1:
            composition = comp1
        elif comp2:
            composition = comp2
        else:
            composition = "Not specified"

        # Map to identical database schema (backward-compatible)
        records.append((
            name,
            unit,
            composition,
            "", # uses
            "", # side_effects
            "", # image_url
            manufacturer,
            0,  # excellent_review_pct
            0,  # average_review_pct
            0   # poor_review_pct
        ))

    # 4. Bulk insert
    print(f"🌿 Bulk-inserting {len(records)} medicines into SQLite...")
    cursor.executemany("""
        INSERT OR IGNORE INTO medicines (
            name, unit, composition, uses, side_effects, image_url, manufacturer,
            excellent_review_pct, average_review_pct, poor_review_pct
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    inserted = cursor.rowcount
    conn.commit()

    # Verify count
    cursor.execute("SELECT COUNT(*) FROM medicines")
    total_db = cursor.fetchone()[0]
    print(f"✅ Migration completed successfully.")
    print(f"✅ Rowcount updated/inserted in this batch: {inserted}")
    print(f"✅ Total medicines now in SQLite DB: {total_db}")
    
    conn.close()

if __name__ == "__main__":
    run_migration()
