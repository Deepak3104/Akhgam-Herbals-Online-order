"""Create product_media table for multiple images/videos per product."""
import MySQLdb

db = MySQLdb.connect(
    host='localhost',
    user='root',
    passwd='7486',
    db='akhgam_herbals',
    charset='utf8mb4'
)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS product_media (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    media_type ENUM('image', 'video') DEFAULT 'image',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB
""")

db.commit()
print("product_media table created successfully!")
db.close()
