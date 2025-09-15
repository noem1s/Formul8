# formul8/database.py
# Handles all SQLite database operations, including setup and migration.

import sqlite3
import json
import os
import shutil
from datetime import datetime, timedelta


def get_db_path(filename="formul8.db"):
    """Returns the full path to the user's database file."""
    app_name = "Formul8"
    app_data_dir = os.path.join(os.getenv('APPDATA'), app_name)
    os.makedirs(app_data_dir, exist_ok=True)
    return os.path.join(app_data_dir, filename)


def create_connection(db_file):
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # Use Row factory to get dictionary-like results
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    return conn


def create_tables(conn):
    """Create the necessary tables for the application."""
    try:
        c = conn.cursor()
        # Ingredients table
        c.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL DEFAULT 'raw',
                concentration REAL,
                diluent TEXT,
                brand TEXT,
                chemical_name TEXT,
                vendor TEXT,
                cost REAL,
                note_type TEXT,
                primary_category TEXT,
                secondary_category TEXT,
                notes TEXT,
                date_added TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
            );
        """)

        # Formulations table
        c.execute("""
            CREATE TABLE IF NOT EXISTS formulations (
                name TEXT PRIMARY KEY,
                unit TEXT,
                is_accord INTEGER NOT NULL DEFAULT 0
            );
        """)

        # Formulation Entries table
        c.execute("""
            CREATE TABLE IF NOT EXISTS formulation_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                formulation_name TEXT NOT NULL,
                ingredient_name TEXT NOT NULL,
                quantity REAL,
                unit TEXT,
                highlight_color TEXT,
                FOREIGN KEY (formulation_name) REFERENCES formulations (name) ON DELETE CASCADE
            );
        """)

        # Settings key-value table
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Table Creation Error: {e}")


def _run_migrations(conn):
    """Checks for and applies necessary schema and data changes to an existing database."""
    try:
        cursor = conn.cursor()
        # --- Schema Migration: Add 'date_added' column (Migration #1) ---
        cursor.execute("PRAGMA table_info(ingredients)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'date_added' not in columns:
            print("Running schema migration: Adding 'date_added' column to ingredients...")
            cursor.execute("ALTER TABLE ingredients ADD COLUMN date_added TEXT NOT NULL DEFAULT '1970-01-01T00:00:00'")
            conn.commit()
            print("Schema migration successful.")

        # --- Data Migration: Flip existing ingredient order (Migration #2) ---
        cursor.execute("SELECT value FROM settings WHERE key = 'v1_order_flip_migration_complete'")
        migration_flag = cursor.fetchone()
        if not migration_flag:
            print("Running one-time data migration: Reversing order of existing ingredients...")
            try:
                # 1. Fetch all ingredients, sorted alphabetically to get a stable original order
                cursor.execute("SELECT name FROM ingredients ORDER BY name ASC")
                all_ingredient_names = [row['name'] for row in cursor.fetchall()]

                # 2. Iterate backwards and assign new, sequential timestamps
                current_time = datetime.now()
                for i, name in enumerate(reversed(all_ingredient_names)):
                    # Decrement the timestamp for each item to create a reverse chronological order
                    new_timestamp = (current_time - timedelta(seconds=i)).isoformat()
                    cursor.execute("UPDATE ingredients SET date_added = ? WHERE name = ?", (new_timestamp, name))

                # 3. Set the flag in the settings table so this doesn't run again
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                               ('v1_order_flip_migration_complete', 'true'))

                conn.commit()
                print("Ingredient order reversal successful.")
            except sqlite3.Error as e:
                print(f"Error during ingredient order reversal migration: {e}")
                conn.rollback()  # Rollback on error

    except sqlite3.Error as e:
        print(f"Database migration error: {e}")


def migrate_from_json(conn, json_path):
    """One-time migration from the old JSON file to the new SQLite DB."""
    print(f"Migrating data from {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Could not load JSON file for migration. Starting with a fresh database.")
        return

    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()

    # Migrate ingredients
    for ing in data.get('ingredients', []):
        ing.setdefault('type', 'raw' if not ing.get('is_accord') else 'accord')
        cursor.execute("""
            INSERT OR REPLACE INTO ingredients (name, type, concentration, diluent, brand, chemical_name, vendor, cost, note_type, primary_category, secondary_category, notes, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ing.get('name'), ing.get('type'), ing.get('concentration'), ing.get('diluent'), ing.get('brand'),
            ing.get('chemical_name'), ing.get('vendor'), ing.get('cost'), ing.get('note_type'),
            ing.get('primary_category'), ing.get('secondary_category'), ing.get('notes'),
            now_iso
        ))

    # Migrate formulations and their entries
    for form in data.get('formulations', []):
        cursor.execute("""
            INSERT OR REPLACE INTO formulations (name, unit, is_accord) VALUES (?, ?, ?)
        """, (form.get('name'), form.get('unit'), form.get('is_accord', False)))
        for entry in form.get('entries', []):
            cursor.execute("""
                INSERT INTO formulation_entries (formulation_name, ingredient_name, quantity, unit, highlight_color)
                VALUES (?, ?, ?, ?, ?)
            """, (
                form.get('name'), entry.get('ingredient_name'), entry.get('quantity'),
                entry.get('unit'), entry.get('highlight_color')
            ))

    # Migrate settings
    settings = data.get('settings', {})
    for key, value in settings.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))

    conn.commit()
    print("Migration successful.")
    # Rename the old file to prevent re-migration
    try:
        shutil.move(json_path, f"{json_path}.migrated")
        print(f"Renamed old data file to {json_path}.migrated")
    except Exception as e:
        print(f"Could not rename old data file: {e}")


def initialize_database():
    """Main function to set up the database, creating it and migrating if needed."""
    db_file = get_db_path()
    json_file = get_db_path("perfume_data.json")

    db_exists = os.path.exists(db_file)

    conn = create_connection(db_file)
    if conn is not None:
        if not db_exists:
            print(f"Database not found at {db_file}. Creating...")
            create_tables(conn)
            if os.path.exists(json_file):
                migrate_from_json(conn, json_file)
        else:
            # If DB exists, run migrations to check for schema updates
            _run_migrations(conn)

    return conn