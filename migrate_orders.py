"""Create cart, orders, and order_items tables."""
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
    # PostgreSQL DDL
    cur.execute("""CREATE TABLE IF NOT EXISTS cart (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        quantity INT NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_cart_item UNIQUE (user_id, product_id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        order_number VARCHAR(20) NOT NULL UNIQUE,
        total_amount DECIMAL(10, 2) NOT NULL,
        shipping_name VARCHAR(100) NOT NULL,
        shipping_phone VARCHAR(15) NOT NULL,
        shipping_email VARCHAR(100) DEFAULT NULL,
        shipping_address TEXT NOT NULL,
        shipping_state VARCHAR(100) NOT NULL,
        shipping_district VARCHAR(100) NOT NULL,
        shipping_pincode VARCHAR(10) NOT NULL,
        payment_method VARCHAR(50) DEFAULT 'cod',
        status VARCHAR(50) DEFAULT 'pending',
        notes TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        product_name VARCHAR(200) NOT NULL,
        product_price DECIMAL(10, 2) NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        subtotal DECIMAL(10, 2) NOT NULL
    )""")
else:
    # MySQL DDL
    cur.execute("""CREATE TABLE IF NOT EXISTS cart (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
        UNIQUE KEY unique_cart_item (user_id, product_id)
    ) ENGINE=InnoDB""")

    cur.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        order_number VARCHAR(20) NOT NULL UNIQUE,
        total_amount DECIMAL(10, 2) NOT NULL,
        shipping_name VARCHAR(100) NOT NULL,
        shipping_phone VARCHAR(15) NOT NULL,
        shipping_email VARCHAR(100) DEFAULT NULL,
        shipping_address TEXT NOT NULL,
        shipping_state VARCHAR(100) NOT NULL,
        shipping_district VARCHAR(100) NOT NULL,
        shipping_pincode VARCHAR(10) NOT NULL,
        payment_method ENUM('cod', 'upi', 'bank_transfer') DEFAULT 'cod',
        status ENUM('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
        notes TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB""")

    cur.execute("""CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NOT NULL,
        product_id INT NOT NULL,
        product_name VARCHAR(200) NOT NULL,
        product_price DECIMAL(10, 2) NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        subtotal DECIMAL(10, 2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    ) ENGINE=InnoDB""")

db.commit()
print('All tables verified/created successfully!')
db.close()

