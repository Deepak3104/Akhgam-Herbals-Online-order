"""Add profile_image column to users table."""
import MySQLdb

db = MySQLdb.connect(
    host='localhost',
    user='root',
    passwd='7486',
    db='akhgam_herbals',
    charset='utf8mb4'
)
cur = db.cursor()

# Check if column already exists
cur.execute("SHOW COLUMNS FROM users LIKE 'profile_image'")
if cur.fetchone():
    print("profile_image column already exists.")
else:
    cur.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) DEFAULT NULL AFTER password")
    db.commit()
    print("profile_image column added successfully!")

db.close()
