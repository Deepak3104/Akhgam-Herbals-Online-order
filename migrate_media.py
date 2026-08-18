"""Create product_media table for multiple images/videos per product."""
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

import MySQLdb

from config import Config, get_db

db = get_db()
cur = db.cursor()

if Config.DB_TYPE == 'postgres':
    create_sql = """
    CREATE TABLE IF NOT EXISTS product_media (
        id SERIAL PRIMARY KEY,
        product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        filename VARCHAR(255) NOT NULL,
        media_type VARCHAR(50) DEFAULT 'image',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
else:
    create_sql = """
    CREATE TABLE IF NOT EXISTS product_media (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        filename VARCHAR(255) NOT NULL,
        media_type ENUM('image', 'video') DEFAULT 'image',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """

cur.execute(create_sql)
db.commit()
print("product_media table verified/created successfully!")
db.close()

