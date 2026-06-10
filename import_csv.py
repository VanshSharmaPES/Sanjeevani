import sqlite3
import pandas as pd
import os

db_path = os.path.join(os.path.dirname(__file__), "sanjeevani.db")
csv_path = os.path.join(os.path.dirname(__file__), "Medicine_Details_revised_new.csv")

def run_migration():
    if not os.path.exists(csv_path):
        print(f"Error: CSV not found at {csv_path}")
        return

    print("🌿 Connecting to database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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
    print("🌿 Reading CSV data...")
    df = pd.read_csv(csv_path)
    print(f"🌿 Read {len(df)} rows from CSV.")
    
    # Replace NaN with empty strings
    df = df.fillna("")

    records = []
    for _, row in df.iterrows():
        try:
            exc = int(float(row['Excellent Review %'])) if row['Excellent Review %'] != "" else 0
        except ValueError:
            exc = 0
        try:
            avg = int(float(row['Average Review %'])) if row['Average Review %'] != "" else 0
        except ValueError:
            avg = 0
        try:
            poor = int(float(row['Poor Review %'])) if row['Poor Review %'] != "" else 0
        except ValueError:
            poor = 0

        records.append((
            row['Medicine Name'].strip(),
            row['Unit'].strip(),
            row['Composition'].strip(),
            row['Uses'].strip(),
            row['Side_effects'].strip(),
            row['Image URL'].strip(),
            row['Manufacturer'].strip(),
            exc,
            avg,
            poor
        ))

    # 4. Bulk insert
    print("🌿 Inserting records in bulk (this might take a few seconds)...")
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
