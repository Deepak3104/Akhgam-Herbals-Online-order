-- ============================================
-- Akhgam Herbals Database (Flask Version)
-- ============================================

CREATE DATABASE IF NOT EXISTS akhgam_herbals CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE akhgam_herbals;

-- ============================================
-- Users Table
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL,
    age INT DEFAULT NULL,
    gender ENUM('male', 'female', 'other') DEFAULT NULL,
    address TEXT DEFAULT NULL,
    state VARCHAR(100) DEFAULT NULL,
    district VARCHAR(100) DEFAULT NULL,
    pincode VARCHAR(10) DEFAULT NULL,
    password VARCHAR(512) NOT NULL,
    profile_image VARCHAR(255) DEFAULT NULL,
    role ENUM('client', 'admin') DEFAULT 'client',
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- Products Table
-- ============================================
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) DEFAULT 'General',
    benefits TEXT,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2) DEFAULT NULL,
    image VARCHAR(255) DEFAULT 'default.jpg',
    status ENUM('active', 'inactive') DEFAULT 'active',
    featured TINYINT(1) DEFAULT 0,
    rating DECIMAL(2,1) DEFAULT 0.0,
    reviews_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- Product Media Table (Multiple Images & Videos)
-- ============================================
CREATE TABLE IF NOT EXISTS product_media (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    media_type ENUM('image', 'video') DEFAULT 'image',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- Categories Table
-- ============================================
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50) DEFAULT 'fas fa-leaf',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- Testimonials Table
-- ============================================
CREATE TABLE IF NOT EXISTS testimonials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    rating INT DEFAULT 5,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- Reviews Table
-- ============================================
CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    rating DECIMAL(2,1) NOT NULL DEFAULT 5.0,
    comment TEXT,
    image VARCHAR(255) DEFAULT NULL,
    status ENUM('active', 'hidden') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- Cart Table
-- ============================================
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_cart_item (user_id, product_id)
) ENGINE=InnoDB;

-- ============================================
-- Wishlist Table
-- ============================================
CREATE TABLE IF NOT EXISTS wishlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_wishlist_item (user_id, product_id)
) ENGINE=InnoDB;

-- ============================================
-- Orders Table
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
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
) ENGINE=InnoDB;

-- ============================================
-- Order Items Table
-- ============================================
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    product_price DECIMAL(10, 2) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================
-- Offers Table
-- ============================================
CREATE TABLE IF NOT EXISTS offers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    label VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(50) DEFAULT 'fas fa-tag',
    status ENUM('active', 'inactive') DEFAULT 'active',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================
-- Insert Default Admin
-- Werkzeug scrypt hash for password: "password"
-- ============================================
INSERT INTO users (name, email, phone,age,gender,address, password, role) VALUES
('Admin', 'admin@akhgam.com', '8270664493','21','Male','5/56, Kudi Street,Unjapalayam(Post),Mohanur(T.K),Namakkal(D.T)', 'scrypt:32768:8:1$V8H1i9lHNpL06Sia$aa259bcc2d1f24310c47fe94fc86fb2104c808dd85bec26e93230c8288b24d5e1311ce3e5e8cc0340a6c40282f27070df2a7b3e3dc61540872c3706dcd7c9ef9', 'admin');
-- Default password: password

-- ============================================
-- Insert Default Categories
-- ============================================
INSERT INTO categories (name, description, icon) VALUES
('Skin Care', 'Natural skin care products for glowing skin', 'fas fa-spa'),
('Hair Care', 'Herbal hair care solutions', 'fas fa-cut'),
('Bath & Body', 'Natural bath and body products', 'fas fa-bath'),
('Face Care', 'Ayurvedic face care range', 'fas fa-smile'),
('Wellness', 'Herbal wellness products', 'fas fa-heartbeat'),
('Essential Oils', 'Pure essential oils', 'fas fa-tint');

-- ============================================
-- Insert Default Offers
-- ============================================
INSERT INTO offers (label, description, icon, status, sort_order) VALUES
('Free Shipping', '🌿 Free shipping on orders above ₹300', 'fas fa-truck', 'active', 1),
('HERBAL10', 'Get 10% off on your order', 'fas fa-tag', 'active', 2),
('NEW5', 'New users get extra 5% off', 'fas fa-star', 'active', 3),
('BUY2GET1', 'Buy 2 get 1 free on select combos', 'fas fa-box-open', 'active', 4),
('Gift Offer', 'Free gift on orders above ₹999', 'fas fa-gift', 'active', 5);

-- ============================================
-- Insert Sample Products
-- ============================================
INSERT INTO products (name, category, benefits, description, price, original_price, image, status, featured, rating, reviews_count) VALUES
('Kumkumadi Brightening Face Oil', 'Face Care', 'Brightens skin, reduces dark spots, improves complexion', 'A luxurious Ayurvedic face oil infused with Kumkumadi Tailam, saffron, and 16 powerful herbs. This golden elixir works overnight to brighten your skin and reduce pigmentation naturally.', 599.00, 899.00, 'default.jpg', 'active', 1, 4.6, 342),
('Bhringraj Anti-Hairfall Oil', 'Hair Care', 'Reduces hairfall, strengthens roots, promotes growth', 'Traditional Bhringraj hair oil enriched with Amla, Brahmi, and coconut oil. Clinically proven to reduce hairfall by 8x from the first use. Nourishes scalp and promotes thick, lustrous hair.', 449.00, 649.00, 'default.jpg', 'active', 1, 4.7, 528),
('Aloe Vera & Turmeric Face Wash', 'Skin Care', 'Deep cleansing, anti-inflammatory, brightening', 'A gentle yet effective face wash combining the soothing power of Aloe Vera with the brightening properties of Turmeric. Removes impurities without stripping natural oils. Suitable for all skin types.', 349.00, 499.00, 'default.jpg', 'active', 1, 4.5, 215),
('Rose Water Hydrating Toner', 'Face Care', 'Hydrates, tones, refreshes skin', 'Pure steam-distilled rose water toner that deeply hydrates and balances your skin pH. Infused with Hyaluronic Acid and Witch Hazel for added moisture retention and pore tightening.', 299.00, 450.00, 'default.jpg', 'active', 1, 4.8, 672),
('Neem & Tea Tree Anti-Acne Cream', 'Skin Care', 'Fights acne, reduces inflammation, prevents breakouts', 'A powerful anti-acne formulation with Neem, Tea Tree Oil, and Salicylic Acid. Targets active acne while preventing future breakouts. Non-comedogenic and suitable for oily skin.', 399.00, 599.00, 'default.jpg', 'active', 0, 4.4, 189),
('Ashwagandha Body Lotion', 'Bath & Body', 'Deep moisturizing, anti-aging, skin rejuvenation', 'A rich, creamy body lotion powered by Ashwagandha root extract and Shea butter. Provides 24-hour moisture while fighting signs of aging. Absorbs quickly without leaving a greasy residue.', 499.00, 745.00, 'default.jpg', 'active', 0, 4.6, 301),
('Saffron & Malai Night Cream', 'Face Care', 'Anti-aging, skin repair, brightening', 'A luxurious night cream infused with Kashmiri Saffron and fresh Malai (cream). Works while you sleep to repair, rejuvenate, and brighten your skin. Wake up to visibly younger-looking skin.', 699.00, 999.00, 'default.jpg', 'active', 1, 4.7, 445),
('Herbal Hair Conditioner', 'Hair Care', 'Smoothens hair, reduces frizz, adds shine', 'A deep-conditioning formula with Rosemary, Amla, and 14 Ayurvedic herbs. Detangles and smoothens hair without weighing it down. Perfect for dry, damaged, and frizzy hair.', 399.00, 550.00, 'default.jpg', 'active', 0, 4.5, 267),
('Sandalwood & Saffron Face Pack', 'Face Care', 'Brightens, tightens pores, removes tan', 'A premium face pack with pure Sandalwood powder and Saffron threads. Provides instant brightness and glow. Regular use helps fade tan, dark spots, and uneven skin tone.', 449.00, 650.00, 'default.jpg', 'active', 0, 4.3, 156),
('Coconut & Almond Body Milk', 'Bath & Body', 'Nourishes, softens, protects skin', 'A lightweight body milk enriched with Virgin Coconut Oil and Sweet Almond Oil. Provides intense nourishment without the heaviness. Perfect for daily use in all seasons.', 379.00, 545.00, 'default.jpg', 'active', 0, 4.7, 198),
('Tulsi & Neem Face Serum', 'Face Care', 'Purifies, detoxifies, prevents acne', 'A potent face serum combining Tulsi (Holy Basil) and Neem extracts with Vitamin C. Targets impurities at the cellular level while boosting collagen production for firm, clear skin.', 549.00, 799.00, 'default.jpg', 'active', 1, 4.6, 312),
('Amla & Shikakai Shampoo', 'Hair Care', 'Cleanses, strengthens, adds volume', 'A sulfate-free herbal shampoo with Amla, Shikakai, and Reetha. Gently cleanses while nourishing hair from root to tip. Adds natural volume and bounce to lifeless hair.', 349.00, 499.00, 'default.jpg', 'active', 0, 4.5, 423);

-- ============================================
-- Insert Sample Testimonials
-- ============================================
INSERT INTO testimonials (name, message, rating) VALUES
('Priya Sharma', 'I have been using Akhgam Herbals products for 3 months now and the results are amazing! My skin has never felt better. The Kumkumadi face oil is a game changer!', 5),
('Rahul Verma', 'The Bhringraj hair oil actually works! I noticed significantly less hairfall within just 2 weeks. Highly recommend their hair care range.', 5),
('Anita Desai', 'Finally found a brand that uses genuine Ayurvedic ingredients. The Saffron night cream has transformed my skin. No more dull mornings!', 4),
('Vikram Singh', 'Great quality products at reasonable prices. The packaging is eco-friendly too. Love the Aloe Vera face wash - so refreshing!', 5),
('Meera Patel', 'As someone with sensitive skin, I was skeptical. But Akhgam Herbals products are so gentle yet effective. The Rose Water toner is my holy grail!', 5);
