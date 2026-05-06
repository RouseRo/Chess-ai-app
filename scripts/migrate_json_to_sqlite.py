#!/usr/bin/env python3
"""Migrate users from JSON files to SQLite database."""

import json
import os
import sqlite3
import bcrypt
from datetime import datetime, timezone

# Paths
JSON_PROFILES_DIR = "user_data/users/profiles"
SQLITE_DB_PATH = "data/users.db"


def init_db(db_path: str):
    """Initialize SQLite database."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            is_verified BOOLEAN DEFAULT 0,
            verification_token TEXT,
            games_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    return conn


def migrate_user(cursor, user_data: dict) -> bool:
    """Migrate a single user to SQLite."""
    username = user_data.get("username", "")
    email = user_data.get("email", "")
    password_hash = user_data.get("password_hash", "")
    is_admin = user_data.get("is_admin", False)
    is_verified = user_data.get("is_verified", False)
    games_count = user_data.get("games_count", 0)
    created_at = user_data.get("created_at", datetime.now(timezone.utc).isoformat())
    
    # Check if password needs to be converted to bcrypt
    if not password_hash.startswith("$2"):
        # It's a SHA256 hash with salt - we need to reset it
        print(f"  Warning: {username} has legacy password hash, setting to 'changeme123'")
        password_hash = bcrypt.hashpw(b"changeme123", bcrypt.gensalt()).decode()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username.lower(),))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing user
            cursor.execute('''
                UPDATE users 
                SET email = ?, password_hash = ?, is_admin = ?, is_verified = ?, games_count = ?
                WHERE username = ?
            ''', (email, password_hash, is_admin, is_verified, games_count, username.lower()))
            print(f"  Updated existing user")
        else:
            # Insert new user
            cursor.execute('''
                INSERT INTO users 
                (username, email, password_hash, is_admin, is_verified, games_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username.lower(), email, password_hash, is_admin, is_verified, games_count, created_at))
        return True
    except sqlite3.IntegrityError as e:
        print(f"  Error migrating {username}: {e}")
        return False


def create_default_admin(cursor):
    """Create default admin if not exists."""
    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin, is_verified)
            VALUES (?, ?, ?, ?, ?)
        ''', ("admin", "admin@chess.local", password_hash, True, True))
        print("Created default admin user (password: admin123)")


def main():
    print("=== JSON to SQLite User Migration ===\n")
    
    # Initialize database
    print(f"Database: {SQLITE_DB_PATH}")
    conn = init_db(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # Get existing users in SQLite
    cursor.execute("SELECT username FROM users")
    existing_users = {row[0] for row in cursor.fetchall()}
    print(f"Existing SQLite users: {existing_users}\n")
    
    # Check JSON profiles directory
    if not os.path.exists(JSON_PROFILES_DIR):
        print(f"Warning: {JSON_PROFILES_DIR} not found, creating default admin only")
        create_default_admin(cursor)
        conn.commit()
    else:
        # Migrate each JSON profile
        migrated = 0
        skipped = 0
        
        for filename in os.listdir(JSON_PROFILES_DIR):
            if not filename.endswith('.json'):
                continue
            
            profile_path = os.path.join(JSON_PROFILES_DIR, filename)
            username = filename.replace('.json', '')
            
            print(f"Processing: {username}")
            
            try:
                with open(profile_path, 'r') as f:
                    user_data = json.load(f)
                
                if migrate_user(cursor, user_data):
                    migrated += 1
                    print(f"  ✓ Migrated successfully")
                else:
                    skipped += 1
                    
            except (json.JSONDecodeError, IOError) as e:
                print(f"  ✗ Error reading file: {e}")
                skipped += 1
        
        # Ensure default admin exists
        create_default_admin(cursor)
        
        conn.commit()
        print(f"\n=== Migration Complete ===")
        print(f"Migrated: {migrated}")
        print(f"Skipped:  {skipped}")
    
    # List all users in SQLite
    cursor.execute("SELECT username, email, is_admin, is_verified FROM users")
    print(f"\nUsers in SQLite database:")
    print("-" * 60)
    for row in cursor.fetchall():
        admin = "✓" if row[2] else " "
        verified = "✓" if row[3] else " "
        print(f"  {row[0]:15} | {row[1]:25} | admin={admin} | verified={verified}")
    
    conn.close()
    print(f"\nDatabase saved to: {SQLITE_DB_PATH}")


if __name__ == "__main__":
    main()