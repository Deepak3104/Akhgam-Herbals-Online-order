USE akhgam_herbals;

CREATE TABLE IF NOT EXISTS offers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    label VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(50) DEFAULT 'fas fa-tag',
    status ENUM('active', 'inactive') DEFAULT 'active',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO offers (label, description, icon, status, sort_order) VALUES
('Free Shipping', '🌿 Free shipping on orders above ₹300', 'fas fa-truck', 'active', 1),
('HERBAL10', 'Get 10% off on your order', 'fas fa-tag', 'active', 2),
('NEW5', 'New users get extra 5% off', 'fas fa-star', 'active', 3),
('BUY2GET1', 'Buy 2 get 1 free on select combos', 'fas fa-box-open', 'active', 4),
('Gift Offer', 'Free gift on orders above ₹999', 'fas fa-gift', 'active', 5);

SELECT * FROM offers;
