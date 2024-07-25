import sqlite3
from contextlib import contextmanager
from config import DEFAULT_NEGATIVE_PROMPT

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('users.db')
    try:
        yield conn
    finally:
        conn.close()

def initialize_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            prompt TEXT,
            negative_prompt TEXT,
            style TEXT,
            width INTEGER,
            height INTEGER,
            guidance_scale REAL,
            seed INTEGER
        )
        ''')
        conn.commit()

def get_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return cursor.fetchone()

def create_user(user_id, username):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO users 
        (id, username, negative_prompt, style, width, height, guidance_scale, seed) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, DEFAULT_NEGATIVE_PROMPT, "3840 x 2160", 2048, 2048, 20.0, -1))
        conn.commit()

def update_user_data(user_id, field, value):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
        conn.commit()