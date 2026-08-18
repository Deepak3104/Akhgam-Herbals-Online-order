#!/usr/bin/env python3
"""
Script to verify and create missing database tables
"""
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from config import Config, get_db

try:
    conn = get_db()
    cur = conn.cursor()
    
    # Create wishlist table if it doesn't exist
    if Config.DB_TYPE == 'postgres':
        create_wishlist_sql = """
        CREATE TABLE IF NOT EXISTS wishlist (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_wishlist_item UNIQUE (user_id, product_id)
        );
        """
    else:
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
    print("Wishlist table verified/created successfully.")
    
    # Check both tables
    if Config.DB_TYPE == 'postgres':
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'offers'")
        offers_exists = cur.fetchone() is not None
        
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'wishlist'")
        wishlist_exists = cur.fetchone() is not None
    else:
        cur.execute("SHOW TABLES LIKE 'offers'")
        offers_exists = cur.fetchone() is not None
        
        cur.execute("SHOW TABLES LIKE 'wishlist'")
        wishlist_exists = cur.fetchone() is not None
    
    print("\nDatabase Tables Status:")
    print(f"  {'[OK]' if offers_exists else '[MISSING]'} offers table")
    print(f"  {'[OK]' if wishlist_exists else '[MISSING]'} wishlist table")
    
    if offers_exists:
        cur.execute("SELECT COUNT(*) as count FROM offers")
        count = cur.fetchone()
        # count is fetched as dict because cursor is DictCursor wrapper for postgres
        if isinstance(count, dict):
            print(f"\nOffers count: {count['count']}")
        else:
            print(f"\nOffers count: {count[0]}")
    
    cur.close()
    conn.close()
    
    print("\nAll required tables are in place.")
    
except Exception as e:
    print(f"Error: {e}")
