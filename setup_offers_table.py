#!/usr/bin/env python3
"""
Script to create the 'offers' table in the akhgam_herbals database
"""
import MySQLdb
import sys

try:
    # Connect to MySQL
    conn = MySQLdb.connect(
        host='localhost',
        user='root',
        passwd='7486',
        db='akhgam_herbals'
    )
    
    cur = conn.cursor()
    
    # Create offers table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS offers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        label VARCHAR(50) NOT NULL,
        description TEXT NOT NULL,
        icon VARCHAR(50) DEFAULT 'fas fa-tag',
        status ENUM('active', 'inactive') DEFAULT 'active',
        sort_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """
    
    cur.execute(create_table_sql)
    print("✅ Offers table created successfully!")
    
    # Insert default offers
    insert_offers_sql = """
    INSERT INTO offers (label, description, icon, status, sort_order) VALUES
    ('Free Shipping', '🌿 Free shipping on orders above ₹300', 'fas fa-truck', 'active', 1),
    ('HERBAL10', 'Get 10% off on your order', 'fas fa-tag', 'active', 2),
    ('NEW5', 'New users get extra 5% off', 'fas fa-star', 'active', 3),
    ('BUY2GET1', 'Buy 2 get 1 free on select combos', 'fas fa-box-open', 'active', 4),
    ('Gift Offer', 'Free gift on orders above ₹999', 'fas fa-gift', 'active', 5)
    """
    
    cur.execute(insert_offers_sql)
    conn.commit()
    print("✅ Default offers inserted successfully!")
    
    # Verify
    cur.execute("SELECT * FROM offers")
    offers = cur.fetchall()
    print(f"\n📊 Total offers in database: {len(offers)}")
    for offer in offers:
        print(f"  - {offer[1]}: {offer[2][:50]}...")
    
    cur.close()
    conn.close()
    print("\n✅ Database setup complete! You can now access the offers page.")
    sys.exit(0)
    
except MySQLdb.Error as e:
    print(f"❌ Database Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
