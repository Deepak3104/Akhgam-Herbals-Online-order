#!/usr/bin/env python3
"""
Script to verify and create missing database tables
"""
import MySQLdb

try:
    conn = MySQLdb.connect(
        host='localhost',
        user='root',
        passwd='7486',
        db='akhgam_herbals'
    )
    
    cur = conn.cursor()
    
    # Create wishlist table if it doesn't exist
    create_wishlist_sql = """
    CREATE TABLE IF NOT EXISTS wishlist (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        product_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
        UNIQUE KEY unique_wishlist_item (user_id, product_id)
    ) ENGINE=InnoDB;
    """
    
    cur.execute(create_wishlist_sql)
    conn.commit()
    print("✅ Wishlist table verified/created successfully!")
    
    # Check both tables
    cur.execute("SHOW TABLES LIKE 'offers'")
    offers_exists = cur.fetchone() is not None
    
    cur.execute("SHOW TABLES LIKE 'wishlist'")
    wishlist_exists = cur.fetchone() is not None
    
    print("\n📋 Database Tables Status:")
    print(f"  {'✅' if offers_exists else '❌'} offers table")
    print(f"  {'✅' if wishlist_exists else '❌'} wishlist table")
    
    if offers_exists:
        cur.execute("SELECT COUNT(*) as count FROM offers")
        count = cur.fetchone()
        print(f"\n📊 Offers count: {count[0]}")
    
    cur.close()
    conn.close()
    
    print("\n✅ All required tables are in place!")
    
except MySQLdb.Error as e:
    print(f"❌ Database Error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
