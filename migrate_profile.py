"""Add profile_image column to users table."""
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

import MySQLdb

from config import Config, get_db

db = get_db()
cur = db.cursor()

# Check if column already exists
if Config.DB_TYPE == 'postgres':
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'profile_image'"
    )
    exists = cur.fetchone() is not None
else:
    cur.execute("SHOW COLUMNS FROM users LIKE 'profile_image'")
    exists = cur.fetchone() is not None

if exists:
    print("profile_image column already exists.")
else:
    if Config.DB_TYPE == 'postgres':
        cur.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) DEFAULT NULL")
    else:
        cur.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) DEFAULT NULL AFTER password")
    db.commit()
    print("profile_image column added successfully!")

db.close()

