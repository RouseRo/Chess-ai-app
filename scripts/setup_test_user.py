#!/usr/bin/env python3
"""Create or reset test users with known passwords."""

import sqlite3
import os
import bcrypt

DB_PATH = "data/users.db"


def main():
    print(f"Database: {DB_PATH}\n")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table if not exists
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
    
    # Users to create/update
    users = [
        ("admin", "admin@chess.local", "admin123", True, True),
        ("johndoe", "john@example.com", "password123", False, True),
    ]
    
    for username, email, password, is_admin, is_verified in users:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Delete existing user first (to avoid constraint issues)
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        
        # Insert fresh
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin, is_verified)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, is_admin, is_verified))
        
        print(f"✓ {username} / {password} (admin={is_admin}, verified={is_verified})")
    
    conn.commit()
    
    # Verify
    print("\n=== Database Contents ===")
    cursor.execute("SELECT username, email, is_admin, is_verified, substr(password_hash, 1, 10) FROM users")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} | admin={row[2]} | verified={row[3]} | hash={row[4]}...")
    
    conn.close()
    print("\n✓ Done! Restart auth service: docker-compose restart chess-auth-service")


if __name__ == "__main__":
    main()