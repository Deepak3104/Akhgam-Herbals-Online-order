"""
Akhgam Herbals - Flask Application
Complete dynamic website with MySQL + Excel support
"""
import os
import time
import random
import math
import hmac
import hashlib
from datetime import datetime
from urllib.parse import quote
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Use PyMySQL as a drop-in replacement for MySQLdb on Windows
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

import MySQLdb
import MySQLdb.cursors

from flask_mail import Mail, Message as MailMessage
from config import Config

try:
    import razorpay
except ImportError:
    razorpay = None

# ============================================
# App Setup
# ============================================
app = Flask(__name__)
app.config.from_object(Config)
app.url_map.strict_slashes = False


@app.route('/favicon.ico')
def favicon():
    """Serve favicon with HTTP 200 even if no icon file exists yet."""
    favicon_path = os.path.join(app.static_folder, 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_file(favicon_path, mimetype='image/x-icon')
    return ('', 200)


@app.before_request
def disable_conditional_cache_headers():
    """Prevent conditional requests from returning 304 responses."""
    request.environ.pop('HTTP_IF_NONE_MATCH', None)
    request.environ.pop('HTTP_IF_MODIFIED_SINCE', None)


@app.after_request
def set_no_cache_headers(response):
    """Force fresh responses to avoid browser/proxy cache revalidation."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers.pop('ETag', None)
    response.headers.pop('Last-Modified', None)
    return response

# Initialize Flask-Mail
mail = Mail(app)

# Ensure upload folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'reviews'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'profiles'), exist_ok=True)
os.makedirs(app.config.get('EXCEL_FOLDER', 'data'), exist_ok=True)

PROFILE_UPLOAD_FOLDER = os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'profiles')


# ============================================
# Database Connection
# ============================================
from config import get_db





def ensure_address_columns():
    """Ensure state/district columns exist for users and orders."""
    columns = [
        ('users', 'state', "VARCHAR(100) DEFAULT NULL AFTER address"),
        ('users', 'district', "VARCHAR(100) DEFAULT NULL AFTER state"),
        ('users', 'dob', "DATE DEFAULT NULL AFTER age"),
        ('orders', 'shipping_state', "VARCHAR(100) NOT NULL DEFAULT '' AFTER shipping_address"),
        ('orders', 'shipping_district', "VARCHAR(100) NOT NULL DEFAULT '' AFTER shipping_state"),
    ]
    db = None
    try:
        db = get_db()
        cur = db.cursor()
        for table_name, col_name, col_def in columns:
            if app.config.get('DB_TYPE') == 'postgres':
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                    (table_name, col_name)
                )
                exists = cur.fetchone() is not None
            else:
                cur.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (col_name,))
                exists = cur.fetchone() is not None

            if not exists:
                clean_def = col_def.split(" AFTER ")[0].replace("DATETIME", "TIMESTAMP")
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {clean_def}")
        db.commit()
    except Exception as e:
        app.logger.warning(f'Address columns check failed: {e}')
    finally:
        if db:
            db.close()


ensure_address_columns()


def ensure_payment_method_column():
    """Allow modern payment method values in orders.payment_method."""
    if app.config.get('DB_TYPE') == 'postgres':
        return  # Handled by database_postgres.sql

    db = None
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SHOW COLUMNS FROM orders LIKE 'payment_method'")
        column = cur.fetchone()
        if not column:
            return

        col_type = (column.get('Type') or '').lower()
        required_values = ['cod', 'upi', 'bank_transfer', 'card', 'net_banking', 'razorpay']

        if col_type.startswith('enum('):
            if any(f"'{value}'" not in col_type for value in required_values):
                cur.execute("ALTER TABLE orders MODIFY payment_method VARCHAR(50) NOT NULL DEFAULT 'cod'")
                db.commit()
    except Exception as e:
        app.logger.warning(f'Payment method column check failed: {e}')
    finally:
        if db:
            db.close()


ensure_payment_method_column()


def ensure_payment_tracking_columns():
    """Ensure orders table has payment tracking fields for gateway reconciliation."""
    columns = [
        ('orders', 'payment_gateway_order_id', "VARCHAR(100) DEFAULT NULL AFTER payment_method"),
        ('orders', 'payment_gateway_payment_id', "VARCHAR(100) DEFAULT NULL AFTER payment_gateway_order_id"),
        ('orders', 'payment_gateway_signature', "VARCHAR(255) DEFAULT NULL AFTER payment_gateway_payment_id"),
        ('orders', 'payment_status', "VARCHAR(20) NOT NULL DEFAULT 'pending' AFTER payment_gateway_signature"),
        ('orders', 'paid_at', "DATETIME DEFAULT NULL AFTER payment_status"),
    ]

    db = None
    try:
        db = get_db()
        cur = db.cursor()
        for table_name, col_name, col_def in columns:
            if app.config.get('DB_TYPE') == 'postgres':
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                    (table_name, col_name)
                )
                exists = cur.fetchone() is not None
            else:
                cur.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (col_name,))
                exists = cur.fetchone() is not None

            if not exists:
                clean_def = col_def.split(" AFTER ")[0].replace("DATETIME", "TIMESTAMP")
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {clean_def}")
        db.commit()
    except Exception as e:
        app.logger.warning(f'Payment tracking columns check failed: {e}')
    finally:
        if db:
            db.close()



ensure_payment_tracking_columns()


# ============================================
# Helpers
# ============================================
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def allowed_media_file(filename):
    """Check if a file is an allowed image or video."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_MEDIA_EXTENSIONS']


def get_media_type(filename):
    """Return 'video' if file is a video, else 'image'."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return 'video' if ext in app.config.get('ALLOWED_VIDEO_EXTENSIONS', set()) else 'image'


def get_whatsapp_link(product_name, client_name='Customer'):
    msg = f"Hello Akhgam Herbals, I am {client_name}. I would like to order {product_name}. Please share more details."
    return f"https://wa.me/{app.config['WHATSAPP_NUMBER']}?text={quote(msg)}"


def get_razorpay_client():
    """Return a configured Razorpay client, or None when unavailable."""
    key_id = (app.config.get('RAZORPAY_KEY_ID') or '').strip()
    key_secret = (app.config.get('RAZORPAY_KEY_SECRET') or '').strip()
    if not key_id or not key_secret or razorpay is None:
        return None
    try:
        return razorpay.Client(auth=(key_id, key_secret))
    except Exception as e:
        app.logger.error(f'Razorpay client initialization failed: {e}')
        return None


def build_razorpay_checkout_data(total_amount, user=None):
    """Create Razorpay order payload used by checkout.js on the client."""
    client = get_razorpay_client()
    if client is None:
        return None

    amount_paise = int(round(float(total_amount) * 100))
    if amount_paise <= 0:
        return None

    currency = (app.config.get('RAZORPAY_CURRENCY') or 'INR').strip().upper() or 'INR'
    receipt = f"akhgam_{int(time.time())}"

    try:
        razorpay_order = client.order.create({
            'amount': amount_paise,
            'currency': currency,
            'receipt': receipt,
            'payment_capture': 1,
        })
    except Exception as e:
        app.logger.error(f'Razorpay order creation failed: {e}')
        return None

    prefill = {}
    if user:
        if user.get('name'):
            prefill['name'] = user['name']
        if user.get('email'):
            prefill['email'] = user['email']
        if user.get('phone'):
            prefill['contact'] = user['phone']

    return {
        'key_id': (app.config.get('RAZORPAY_KEY_ID') or '').strip(),
        'amount': amount_paise,
        'currency': currency,
        'order_id': razorpay_order.get('id'),
        'name': app.config.get('SITE_NAME', 'Akhgam Herbals'),
        'description': 'Secure order payment',
        'prefill': prefill,
        'theme': {'color': '#8b2d4f'},
    }


def verify_razorpay_webhook_signature(payload_bytes, received_signature):
    """Verify Razorpay webhook payload signature using HMAC SHA256."""
    secret = (app.config.get('RAZORPAY_WEBHOOK_SECRET') or '').strip()
    if not secret or not received_signature:
        return False

    generated = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(generated, received_signature)


def normalize_phone_variants(phone):
    """Generate phone number variants for lookup."""
    # Remove all non-digits
    digits = ''.join(ch for ch in phone if ch.isdigit())
    
    if not digits:
        return [phone]
    
    variants = [digits]
    
    # If it looks like an Indian number (10 digits), add variants with +91
    if len(digits) == 10:
        variants.append(f"+91{digits}")
        variants.append(f"91{digits}")
    
    # Add original format
    if phone not in variants:
        variants.append(phone)
    
    return variants


def lookup_user_by_identifier(cursor, identifier, admin_only=False):
    """Find a user by email or phone."""
    lookup_value = (identifier or '').strip()
    phone_variants = normalize_phone_variants(lookup_value)

    if '@' in lookup_value:
        if admin_only:
            cursor.execute(
                "SELECT id, name, email, phone, password, role, status, profile_image FROM users WHERE email=%s AND role='admin'",
                (lookup_value,)
            )
        else:
            cursor.execute(
                "SELECT id, name, email, phone, password, role, status, profile_image FROM users WHERE email=%s",
                (lookup_value,)
            )
        return cursor.fetchone()

    if admin_only:
        query = (
            "SELECT id, name, email, phone, password, role, status, profile_image FROM users "
            "WHERE role='admin' AND (phone=%s OR REPLACE(REPLACE(phone, ' ', ''), '-', '')=%s)"
        )
    else:
        query = (
            "SELECT id, name, email, phone, password, role, status, profile_image FROM users "
            "WHERE phone=%s OR REPLACE(REPLACE(phone, ' ', ''), '-', '')=%s"
        )
    primary_value = phone_variants[0]
    normalized_digits = ''.join(ch for ch in lookup_value if ch.isdigit())
    cursor.execute(query, (primary_value, normalized_digits))
    user = cursor.fetchone()

    if user:
        return user

    for variant in phone_variants[1:]:
        cursor.execute(query, (variant, normalized_digits))
        user = cursor.fetchone()
        if user:
            return user

    return None


def login_required(f):
    """Decorator: require login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def generate_stars(rating):
    """Generate star HTML for a given rating."""
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    stars = '<i class="fas fa-star"></i>' * full
    if half:
        stars += '<i class="fas fa-star-half-alt"></i>'
    return stars


def get_marketing_bestseller_ids(cursor, limit=8):
    """Return product IDs using admin picks + 50/50 sales strategy."""
    if limit <= 0:
        return []

    cursor.execute(
        "SELECT id FROM products WHERE status='active' AND featured=1 ORDER BY created_at DESC LIMIT %s",
        (limit,)
    )
    admin_pick_ids = [row['id'] for row in cursor.fetchall()]

    selected_ids = list(admin_pick_ids)
    remaining_slots = max(0, limit - len(selected_ids))
    if remaining_slots == 0:
        return selected_ids[:limit]

    cursor.execute("""
        SELECT
            p.id,
            p.reviews_count,
            COALESCE(s.sales_qty, 0) AS sales_qty
        FROM products p
        LEFT JOIN (
            SELECT oi.product_id, SUM(oi.quantity) AS sales_qty
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status IN ('confirmed', 'processing', 'shipped', 'delivered')
            GROUP BY oi.product_id
        ) s ON s.product_id = p.id
        WHERE p.status='active'
    """)
    candidates = cursor.fetchall()

    excluded = set(selected_ids)
    top_selling = [
        row for row in candidates
        if row['id'] not in excluded and (row.get('sales_qty') or 0) > 0
    ]
    top_selling.sort(
        key=lambda row: (
            -(row.get('sales_qty') or 0),
            -(row.get('reviews_count') or 0),
            -(row['id'] or 0)
        )
    )

    never_ordered = [
        row for row in candidates
        if row['id'] not in excluded and (row.get('sales_qty') or 0) == 0
    ]
    random.shuffle(never_ordered)

    top_slots = math.ceil(remaining_slots / 2)
    growth_slots = remaining_slots - top_slots

    for row in top_selling[:top_slots]:
        selected_ids.append(row['id'])
        excluded.add(row['id'])

    added_growth = 0
    for row in never_ordered:
        if added_growth >= growth_slots:
            break
        if row['id'] in excluded:
            continue
        selected_ids.append(row['id'])
        excluded.add(row['id'])
        added_growth += 1

    if len(selected_ids) < limit:
        fallback_rows = [row for row in candidates if row['id'] not in excluded]
        fallback_rows.sort(key=lambda row: (-(row.get('reviews_count') or 0), -(row['id'] or 0)))
        for row in fallback_rows:
            if len(selected_ids) >= limit:
                break
            selected_ids.append(row['id'])
            excluded.add(row['id'])

    return selected_ids[:limit]


# ============================================
# Context Processors (global template vars)
# ============================================
@app.context_processor
def inject_globals():
    # Fetch active offers
    offers = []
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id, label, description, icon FROM offers WHERE status='active' ORDER BY sort_order ASC")
        offers = cur.fetchall()
        db.close()
    except:
        # If there's any error, just use empty list
        offers = []
    
    return {
        'site_name': app.config['SITE_NAME'],
        'site_tagline': app.config['SITE_TAGLINE'],
        'site_email': app.config['SITE_EMAIL'],
        'site_phone': app.config['SITE_PHONE'],
        'site_address': app.config['SITE_ADDRESS'],
        'whatsapp_number': app.config['WHATSAPP_NUMBER'],
        'current_year': time.strftime('%Y'),
        'is_logged_in': 'user_id' in session,
        'is_admin': session.get('role') == 'admin',
        'user_name': session.get('username', ''),
        'user_email': session.get('user_email', ''),
        'user_profile_image': session.get('user_profile_image', ''),
        'get_whatsapp_link': get_whatsapp_link,
        'generate_stars': generate_stars,
        'offers': offers,
    }


# ============================================
# Template Filters
# ============================================
@app.template_filter('number_format')
def number_format_filter(value):
    try:
        return '{:,.0f}'.format(float(value))
    except (ValueError, TypeError):
        return value


@app.template_filter('quote_url')
def quote_url_filter(value):
    return quote(str(value))


# ============================================
# PUBLIC ROUTES
# ============================================

# ---------- Home ----------
@app.route('/')
def index():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM products WHERE status='active' ORDER BY created_at DESC")
    featured = cur.fetchall()

    bestseller_ids = get_marketing_bestseller_ids(cur, limit=8)
    bestsellers = []
    if bestseller_ids:
        placeholders = ','.join(['%s'] * len(bestseller_ids))
        cur.execute(f"SELECT * FROM products WHERE status='active' AND id IN ({placeholders})", tuple(bestseller_ids))
        bestseller_rows = cur.fetchall()
        product_map = {row['id']: row for row in bestseller_rows}
        bestsellers = [product_map[pid] for pid in bestseller_ids if pid in product_map]

    bestseller_id_set = set(bestseller_ids)
    for product in featured:
        product['is_bestseller'] = bool(product.get('featured')) or product['id'] in bestseller_id_set
    for product in bestsellers:
        product['is_bestseller'] = bool(product.get('featured')) or product['id'] in bestseller_id_set

    client_name = session.get('username', 'Customer')
    db.close()

    return render_template('index.html',
                           page_title='Home',
                           featured=featured,
                           bestsellers=bestsellers,
                           client_name=client_name)


# ---------- Products ----------
@app.route('/products')
def products():
    db = get_db()
    cur = db.cursor()

    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'newest').strip()

    where = "WHERE status='active'"
    params = []

    if category:
        where += " AND category=%s"
        params.append(category)

    if search:
        where += " AND (name LIKE %s OR description LIKE %s OR benefits LIKE %s OR category LIKE %s)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    order_map = {
        'price_low': 'ORDER BY price ASC',
        'price_high': 'ORDER BY price DESC',
        'rating': 'ORDER BY rating DESC',
        'popular': 'ORDER BY reviews_count DESC',
    }
    order = order_map.get(sort, 'ORDER BY created_at DESC')

    cur.execute(f"SELECT * FROM products {where} {order}", params)
    product_list = cur.fetchall()

    bestseller_ids = set(get_marketing_bestseller_ids(cur, limit=24))
    for product in product_list:
        product['is_bestseller'] = bool(product.get('featured')) or product['id'] in bestseller_ids

    cur.execute("SELECT DISTINCT category FROM products WHERE status='active' ORDER BY category")
    categories = cur.fetchall()

    client_name = session.get('username', 'Customer')
    db.close()

    return render_template('products.html',
                           page_title='Products',
                           products=product_list,
                           categories=categories,
                           category=category,
                           search=search,
                           sort=sort,
                           client_name=client_name)


# ---------- Product Details ----------
@app.route('/product/<int:product_id>')
def product_details(product_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM products WHERE id=%s AND status='active'", (product_id,))
    product = cur.fetchone()

    if not product:
        db.close()
        flash('Product not found.', 'error')
        return redirect(url_for('products'))

    cur.execute("SELECT * FROM products WHERE category=%s AND id!=%s AND status='active' LIMIT 4",
                (product['category'], product_id))
    related = cur.fetchall()

    # Fetch product media (multiple images & videos)
    cur.execute("SELECT * FROM product_media WHERE product_id=%s ORDER BY sort_order", (product_id,))
    product_media = cur.fetchall()

    # Fetch reviews with user names
    cur.execute("""SELECT r.*, u.name as user_name
                   FROM reviews r
                   JOIN users u ON r.user_id = u.id
                   WHERE r.product_id=%s AND r.status='active'
                   ORDER BY r.created_at DESC""", (product_id,))
    reviews = cur.fetchall()

    # Total sold quantity for this product (exclude cancelled and pending orders)
    cur.execute("""
                SELECT COALESCE(SUM(oi.quantity), 0) AS sold_count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id=%s
                    AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered')
        """, (product_id,))
    sold_count = cur.fetchone()['sold_count']

    # Check if current user already reviewed
    user_has_reviewed = False
    if 'user_id' in session:
        cur.execute("SELECT id FROM reviews WHERE product_id=%s AND user_id=%s", (product_id, session['user_id']))
        user_has_reviewed = cur.fetchone() is not None

    client_name = session.get('username', 'Customer')

    # Calculate savings
    savings = round(product['original_price'] - product['price']) if product['original_price'] else 0
    discount_pct = round((savings / float(product['original_price'])) * 100) if product['original_price'] and float(product['original_price']) > 0 else 0

    benefits = [b.strip() for b in (product['benefits'] or '').split(',') if b.strip()]
    bestseller_ids = set(get_marketing_bestseller_ids(cur, limit=24))
    is_bestseller = bool(product.get('featured')) or product_id in bestseller_ids

    db.close()

    return render_template('product_details.html',
                           page_title=product['name'],
                           product=product,
                           product_media=product_media,
                           related=related,
                           reviews=reviews,
                           sold_count=sold_count,
                           user_has_reviewed=user_has_reviewed,
                           client_name=client_name,
                           savings=savings,
                           discount_pct=discount_pct,
                           benefits=benefits,
                           is_bestseller=is_bestseller)


@app.route('/product/<int:product_id>/popup')
def product_details_popup(product_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM products WHERE id=%s AND status='active'", (product_id,))
    product = cur.fetchone()

    if not product:
        db.close()
        return jsonify({'success': False, 'message': 'Product not found.'}), 404

    cur.execute("""
        SELECT COALESCE(SUM(oi.quantity), 0) AS sold_count
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE oi.product_id=%s
            AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered')
    """, (product_id,))
    sold_count = cur.fetchone()['sold_count']

    savings = round(product['original_price'] - product['price']) if product['original_price'] else 0
    discount_pct = round((savings / float(product['original_price'])) * 100) if product['original_price'] and float(product['original_price']) > 0 else 0
    benefits = [b.strip() for b in (product['benefits'] or '').split(',') if b.strip()]
    bestseller_ids = set(get_marketing_bestseller_ids(cur, limit=24))
    is_bestseller = bool(product.get('featured')) or product_id in bestseller_ids

    image_url = None
    if product.get('image') and product['image'] != 'default.jpg':
        image_url = url_for('static', filename='uploads/products/' + product['image'])

    db.close()

    return jsonify({
        'success': True,
        'product': {
            'id': product['id'],
            'name': product['name'],
            'category': product['category'],
            'description': product['description'] or '',
            'price': float(product['price']) if product['price'] is not None else 0,
            'original_price': float(product['original_price']) if product['original_price'] is not None else None,
            'rating': float(product['rating']) if product['rating'] is not None else 0,
            'reviews_count': int(product['reviews_count'] or 0),
            'sold_count': int(sold_count or 0),
            'savings': int(savings),
            'discount_pct': int(discount_pct),
            'benefits': benefits,
            'featured': bool(product.get('featured')),
            'is_bestseller': bool(is_bestseller),
            'image_url': image_url,
            'product_url': url_for('product_details', product_id=product['id'])
        }
    })


# ---------- Submit Review ----------
@app.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def submit_review(product_id):
    db = get_db()
    cur = db.cursor()

    # Check product exists
    cur.execute("SELECT id FROM products WHERE id=%s AND status='active'", (product_id,))
    if not cur.fetchone():
        db.close()
        flash('Product not found.', 'error')
        return redirect(url_for('products'))

    # Check if user already reviewed
    cur.execute("SELECT id FROM reviews WHERE product_id=%s AND user_id=%s", (product_id, session['user_id']))
    if cur.fetchone():
        db.close()
        flash('You have already reviewed this product.', 'error')
        return redirect(url_for('product_details', product_id=product_id))

    rating_raw = request.form.get('rating', '5.0')
    comment = request.form.get('comment', '').strip()

    try:
        rating = round(float(rating_raw), 1)
    except (TypeError, ValueError):
        rating = 5.0

    if rating < 1 or rating > 5:
        rating = 5.0

    # Handle review image upload
    image_name = None
    file = request.files.get('review_image')
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        image_name = f"review_{session['user_id']}_{product_id}_{int(time.time())}.{ext}"
        reviews_folder = os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'reviews')
        os.makedirs(reviews_folder, exist_ok=True)
        file.save(os.path.join(reviews_folder, image_name))

    cur.execute(
        "INSERT INTO reviews (product_id, user_id, rating, comment, image) VALUES (%s, %s, %s, %s, %s)",
        (product_id, session['user_id'], rating, comment or None, image_name)
    )

    # Update product rating and review count
    cur.execute("""
        UPDATE products SET
            rating = (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE product_id=%s AND status='active'),
            reviews_count = (SELECT COUNT(*) FROM reviews WHERE product_id=%s AND status='active')
        WHERE id=%s
    """, (product_id, product_id, product_id))

    db.commit()
    db.close()

    flash('Your review has been submitted successfully!', 'success')
    return redirect(url_for('product_details', product_id=product_id))


# ---------- Delete Review ----------
@app.route('/review/<int:review_id>/delete')
@login_required
def delete_review(review_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM reviews WHERE id=%s", (review_id,))
    review = cur.fetchone()

    if not review:
        db.close()
        flash('Review not found.', 'error')
        return redirect(url_for('products'))

    # Only the author or admin can delete
    if review['user_id'] != session['user_id'] and session.get('role') != 'admin':
        db.close()
        flash('Unauthorized action.', 'error')
        return redirect(url_for('products'))

    product_id = review['product_id']

    # Delete review image if exists
    if review['image']:
        img_path = os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'reviews', review['image'])
        if os.path.exists(img_path):
            os.remove(img_path)

    cur.execute("DELETE FROM reviews WHERE id=%s", (review_id,))

    # Update product rating and review count
    cur.execute("SELECT COUNT(*) as cnt FROM reviews WHERE product_id=%s AND status='active'", (product_id,))
    cnt = cur.fetchone()['cnt']
    if cnt > 0:
        cur.execute("""
            UPDATE products SET
                rating = (SELECT ROUND(AVG(rating), 1) FROM reviews WHERE product_id=%s AND status='active'),
                reviews_count = %s
            WHERE id=%s
        """, (product_id, cnt, product_id))
    else:
        cur.execute("UPDATE products SET rating=0.0, reviews_count=0 WHERE id=%s", (product_id,))

    db.commit()
    db.close()

    flash('Review deleted successfully.', 'success')
    return redirect(url_for('product_details', product_id=product_id))


# ---------- About ----------
@app.route('/about')
def about():
    return render_template('about.html', page_title='About Us')


# ---------- Feedback ----------
@app.route('/feedback')
def feedback():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT
            u.name AS name,
            r.comment AS message,
            r.rating AS rating,
            r.created_at AS created_at,
            p.id AS product_id,
            p.name AS product_name
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        JOIN products p ON r.product_id = p.id
        WHERE r.status='active'
          AND p.status='active'
          AND r.comment IS NOT NULL
          AND TRIM(r.comment) != ''
        ORDER BY r.created_at DESC
    """)
    reviews = cur.fetchall()

    review_count = len(reviews)
    review_avg = 0.0
    if reviews:
        ratings = []
        for item in reviews:
            try:
                ratings.append(float(item.get('rating', 0) or 0))
            except (ValueError, TypeError):
                continue
        if ratings:
            review_avg = round(sum(ratings) / len(ratings), 1)

    db.close()
    return render_template('feedback.html',
                           page_title='Feedback',
                           reviews=reviews,
                           review_count=review_count,
                           review_avg=review_avg)


# ---------- Crafting Beauty ----------
@app.route('/crafting-beauty')
def crafting_beauty():
    # Update this path after uploading your production video.
    video_filename = 'uploads/crafting-beauty.mp4'
    return render_template('crafting_beauty.html',
                           page_title='Crafting Beauty',
                           video_filename=video_filename)


# ---------- Contact ----------
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    success = ''
    error = ''
    form_data = {}

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        form_data = {'name': name, 'email': email, 'phone': phone, 'subject': subject, 'message': message}

        if not name or not email or not message:
            error = 'Please fill in all required fields.'
        else:
            # Send email to admin
            try:
                subject_line = subject if subject else 'New Contact Form Message'
                email_body = f"""New message from Akhgam Herbals Contact Form

-------------------------------------------
Name:    {name}
Email:   {email}
Phone:   {phone or 'Not provided'}
Subject: {subject or 'Not specified'}
-------------------------------------------

Message:
{message}

-------------------------------------------
This email was sent from the Akhgam Herbals website contact form.
"""
                msg = MailMessage(
                    subject=f'[Contact Form] {subject_line}',
                    recipients=[app.config.get('CONTACT_RECEIVE_EMAIL', 'admin@akhgam.com')],
                    body=email_body,
                    reply_to=email
                )
                mail.send(msg)
                success = 'Thank you for contacting us! Your message has been sent successfully.'
            except Exception as e:
                app.logger.error(f'Contact form email error: {e}')
                success = 'Thank you for contacting us! We will get back to you soon.'
            form_data = {}

    return render_template('contact.html',
                           page_title='Contact Us',
                           success=success,
                           error=error,
                           form_data=form_data)


# ============================================
# AUTH ROUTES
# ============================================

# ---------- Register ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    error = ''
    form_data = {}

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        age = request.form.get('age', '').strip()
        dob = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()
        address = request.form.get('address', '').strip()
        state = request.form.get('state', '').strip()
        district = request.form.get('district', '').strip()
        pincode = request.form.get('pincode', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        form_data = {
            'name': name,
            'email': email,
            'phone': phone,
            'age': age,
            'dob': dob,
            'gender': gender,
            'address': address,
            'state': state,
            'district': district,
            'pincode': pincode,
        }
        phone_digits = ''.join(ch for ch in phone if ch.isdigit())
        stored_phone = phone_digits if phone_digits else phone

        if not name or not email or not phone or not password:
            error = 'Name, email, phone, and password are required.'
        elif not age or not dob:
            error = 'Age and date of birth are required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
            try:
                age_val = int(age)
                if age_val < 1 or age_val > 120:
                    raise ValueError
            except ValueError:
                error = 'Please enter a valid age between 1 and 120.'

            try:
                dob_val = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                error = 'Please provide a valid date of birth.'

        if not error:
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            existing_email = cur.fetchone()
            cur.execute(
                "SELECT id FROM users WHERE phone=%s OR REPLACE(REPLACE(phone, ' ', ''), '-', '')=%s",
                (stored_phone, phone_digits)
            )
            existing_phone = cur.fetchone()

            if existing_email:
                error = 'An account with this email already exists.'
            elif existing_phone:
                error = 'An account with this phone number already exists.'
            else:
                cur.execute(
                    """INSERT INTO users (name, email, phone, age, dob, gender, address, state, district, pincode, password, role, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'client', 'active')""",
                    (
                        name,
                        email,
                        stored_phone,
                        age_val,
                        dob_val,
                        gender if gender in ('male', 'female', 'other') else None,
                        address or None,
                        state or None,
                        district or None,
                        pincode or None,
                        generate_password_hash(password),
                    )
                )
                db.commit()
                db.close()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login', registered=1))
            
            db.close()

    return render_template('register.html',
                           page_title='Register',
                           error=error,
                           form_data=form_data)


# ---------- Login ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return products()

    error = ''
    registered = request.args.get('registered')
    identifier = ''

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            error = 'Please enter both your email or mobile number and password.'
        else:
            db = get_db()
            cur = db.cursor()
            user = lookup_user_by_identifier(cur, identifier)
            db.close()

            if user and check_password_hash(user['password'], password):
                if user['status'] == 'inactive':
                    error = 'Your account has been deactivated. Please contact support.'
                elif user['role'] == 'admin':
                    error = 'Admin accounts must login through the admin login page.'
                else:
                    session.clear()
                    session['user_id'] = user['id']
                    session['name'] = user['name']
                    session['email'] = user['email']
                    session['phone'] = user['phone']
                    session['username'] = user['name']
                    session['user_email'] = user['email']
                    session['user_phone'] = user['phone']
                    session['role'] = user.get('role', 'user')
                    session['profile_pic'] = ''
                    session['user_profile_image'] = user.get('profile_image', '') or ''
                    session.modified = True
                    flash(f'Welcome back, {user["name"]}!', 'success')
                    return products()
            else:
                error = 'Invalid credentials.'

    return render_template('login.html',
                           page_title='Login',
                           error=error,
                           registered=registered,
                           identifier=identifier)


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    flash('OTP verification is disabled.', 'error')
    return redirect(url_for('login'))


# ---------- Dashboard ----------
@app.route('/dashboard')
@login_required
def dashboard():
    # Redirect admin users to the admin dashboard
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()

    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE status='active'")
    product_count = cur.fetchone()['cnt']

    db.close()

    return render_template('dashboard.html',
                           page_title='My Dashboard',
                           user=user,
                           product_count=product_count)


# ---------- Update Profile ----------
@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    age = request.form.get('age', '').strip()
    dob = request.form.get('dob', '').strip()
    gender = request.form.get('gender', '').strip()
    address = request.form.get('address', '').strip()
    state = request.form.get('state', '').strip()
    district = request.form.get('district', '').strip()
    pincode = request.form.get('pincode', '').strip()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_new_password = request.form.get('confirm_new_password', '')

    if not name or not phone:
        flash('Name and phone are required.', 'error')
        return redirect(url_for('dashboard'))

    db = get_db()
    cur = db.cursor()

    # Handle password change if requested
    if current_password or new_password or confirm_new_password:
        if not current_password:
            flash('Please enter your current password to change it.', 'error')
            db.close()
            return redirect(url_for('dashboard'))

        cur.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],))
        user = cur.fetchone()
        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect.', 'error')
            db.close()
            return redirect(url_for('dashboard'))

        if len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'error')
            db.close()
            return redirect(url_for('dashboard'))

        if new_password != confirm_new_password:
            flash('New passwords do not match.', 'error')
            db.close()
            return redirect(url_for('dashboard'))

        hashed = generate_password_hash(new_password)
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, session['user_id']))

    # Handle profile image upload
    profile_img_name = None
    profile_file = request.files.get('profile_image')
    if profile_file and profile_file.filename and allowed_file(profile_file.filename):
        ext = profile_file.filename.rsplit('.', 1)[1].lower()
        profile_img_name = f"profile_{session['user_id']}_{int(time.time())}.{ext}"
        profile_file.save(os.path.join(PROFILE_UPLOAD_FOLDER, profile_img_name))
        # Delete old profile image if exists
        cur.execute("SELECT profile_image FROM users WHERE id=%s", (session['user_id'],))
        old_pi = cur.fetchone()
        if old_pi and old_pi['profile_image']:
            old_path = os.path.join(PROFILE_UPLOAD_FOLDER, old_pi['profile_image'])
            if os.path.exists(old_path):
                os.remove(old_path)
    elif profile_file and profile_file.filename:
        flash('Invalid image format. Allowed: JPG, PNG, GIF, WEBP.', 'error')
        db.close()
        return redirect(url_for('dashboard'))

    age_val = int(age) if age else None
    try:
        dob_val = datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
    except ValueError:
        flash('Please enter a valid date of birth.', 'error')
        db.close()
        return redirect(url_for('dashboard'))

    gender_val = gender if gender in ('male', 'female', 'other') else None

    if profile_img_name:
        cur.execute(
            """UPDATE users SET name=%s, phone=%s, age=%s, dob=%s, gender=%s, address=%s, state=%s, district=%s, pincode=%s, profile_image=%s
               WHERE id=%s""",
            (name, phone, age_val, dob_val, gender_val, address or None, state or None, district or None, pincode or None, profile_img_name, session['user_id'])
        )
    else:
        cur.execute(
            """UPDATE users SET name=%s, phone=%s, age=%s, dob=%s, gender=%s, address=%s, state=%s, district=%s, pincode=%s
               WHERE id=%s""",
            (name, phone, age_val, dob_val, gender_val, address or None, state or None, district or None, pincode or None, session['user_id'])
        )
    db.commit()

    # Update session
    session['username'] = name
    session['user_phone'] = phone
    if profile_img_name:
        session['user_profile_image'] = profile_img_name

    flash('Profile updated successfully!', 'success')
    db.close()
    return redirect(url_for('dashboard'))


# ---------- Delete Account ----------
@app.route('/delete-account', methods=['POST'])
def delete_account():
    if 'user_id' not in session or session.get('role') == 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'})

    password = request.form.get('password', '')
    if not password:
        return jsonify({'success': False, 'error': 'Password is required.'})

    db = get_db()
    cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT password, profile_image FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()

    if not user:
        return jsonify({'success': False, 'error': 'Account not found.'})

    if not check_password_hash(user['password'], password):
        return jsonify({'success': False, 'error': 'Incorrect password. Please try again.'})

    # Delete profile image if exists
    if user.get('profile_image'):
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'profiles', user['profile_image'])
        if os.path.exists(img_path):
            os.remove(img_path)

    # Delete user (cascades to orders, cart, reviews via FK)
    cur.execute("DELETE FROM users WHERE id=%s", (session['user_id'],))
    db.commit()
    db.close()

    session.clear()
    return jsonify({'success': True, 'redirect': url_for('index')})


# ---------- Logout ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ============================================
# ADMIN ROUTES
# ============================================

# ---------- Admin Login ----------
@app.route('/admin')
def admin_root():
    """Single entry point for admin section."""
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    error = ''

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = 'Please enter both email and password.'
        else:
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id, name, email, phone, password, role, status, profile_image FROM users WHERE email=%s AND role='admin'", (email,))
            user = cur.fetchone()
            db.close()

            if user and check_password_hash(user['password'], password):
                # Clear any existing session to prevent role confusion
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['name']
                session['user_email'] = user['email']
                session['user_phone'] = user['phone']
                session['role'] = user['role']
                session['user_profile_image'] = user.get('profile_image', '') or ''
                return redirect(url_for('admin_dashboard'))
            else:
                error = 'Invalid admin credentials.'

    return render_template('admin/login.html',
                           page_title='Admin Login',
                           error=error)


# ---------- Admin Dashboard ----------
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) as cnt FROM products")
    total_products = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE status='active'")
    active_products = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role='client'")
    total_users = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE featured=1")
    featured_products = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM orders")
    total_orders = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='pending'")
    pending_orders = cur.fetchone()['cnt']

    cur.execute("SELECT * FROM products ORDER BY created_at DESC LIMIT 5")
    recent_products = cur.fetchall()

    cur.execute("SELECT * FROM users WHERE role='client' ORDER BY created_at DESC LIMIT 5")
    recent_users = cur.fetchall()

    cur.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5")
    recent_orders = cur.fetchall()

    db.close()

    return render_template('admin/dashboard.html',
                           admin_page_title='Dashboard',
                           total_products=total_products,
                           active_products=active_products,
                           total_users=total_users,
                           featured_products=featured_products,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           recent_products=recent_products,
                           recent_users=recent_users,
                           recent_orders=recent_orders)


# ---------- Admin Profile ----------
@app.route('/admin/profile')
@admin_required
def admin_profile():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    admin_user = cur.fetchone()
    db.close()
    return render_template('admin/profile.html',
                           admin_page_title='My Profile',
                           admin_user=admin_user)


# ---------- Admin Update Profile ----------
@app.route('/admin/update-profile', methods=['POST'])
@admin_required
def admin_update_profile():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    age = request.form.get('age', '').strip()
    gender = request.form.get('gender', '').strip()
    address = request.form.get('address', '').strip()
    state = request.form.get('state', '').strip()
    district = request.form.get('district', '').strip()
    pincode = request.form.get('pincode', '').strip()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_new_password = request.form.get('confirm_new_password', '')

    if not name or not phone:
        flash('Name and phone are required.', 'error')
        return redirect(url_for('admin_profile'))

    db = get_db()
    cur = db.cursor()

    # Handle password change if requested
    if current_password or new_password or confirm_new_password:
        if not current_password:
            flash('Please enter your current password to change it.', 'error')
            db.close()
            return redirect(url_for('admin_profile'))

        cur.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],))
        user = cur.fetchone()
        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect.', 'error')
            db.close()
            return redirect(url_for('admin_profile'))

        if len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'error')
            db.close()
            return redirect(url_for('admin_profile'))

        if new_password != confirm_new_password:
            flash('New passwords do not match.', 'error')
            db.close()
            return redirect(url_for('admin_profile'))

        hashed = generate_password_hash(new_password)
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, session['user_id']))

    age_val = int(age) if age else None
    gender_val = gender if gender in ('male', 'female', 'other') else None

    cur.execute(
        """UPDATE users SET name=%s, phone=%s, age=%s, gender=%s, address=%s, state=%s, district=%s, pincode=%s
           WHERE id=%s""",
        (name, phone, age_val, gender_val, address or None, state or None, district or None, pincode or None, session['user_id'])
    )
    db.commit()

    session['username'] = name
    session['user_phone'] = phone

    flash('Profile updated successfully!', 'success')
    db.close()
    return redirect(url_for('admin_profile'))


# ---------- Admin Manage Products ----------
@app.route('/admin/products', methods=['GET', 'POST'])
@admin_required
def admin_manage_products():
    db = get_db()
    cur = db.cursor()
    error = ''
    success = ''
    action = request.args.get('action', 'list')
    edit_product = None
    edit_media = []

    # Handle Delete Media (AJAX)
    delete_media_id = request.args.get('delete_media', type=int)
    if delete_media_id:
        cur.execute("SELECT filename FROM product_media WHERE id=%s", (delete_media_id,))
        media_row = cur.fetchone()
        if media_row:
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], media_row['filename'])
            if os.path.exists(media_path):
                os.remove(media_path)
            cur.execute("DELETE FROM product_media WHERE id=%s", (delete_media_id,))
            db.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            db.close()
            return jsonify({'success': True})
        success = 'Media file removed.'

    # Handle Delete Product
    delete_id = request.args.get('delete', type=int)
    if delete_id:
        # Delete main image
        cur.execute("SELECT image FROM products WHERE id=%s", (delete_id,))
        old = cur.fetchone()
        if old and old['image'] != 'default.jpg':
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old['image'])
            if os.path.exists(old_path):
                os.remove(old_path)
        # Delete all media files
        cur.execute("SELECT filename FROM product_media WHERE product_id=%s", (delete_id,))
        media_files = cur.fetchall()
        for mf in media_files:
            mf_path = os.path.join(app.config['UPLOAD_FOLDER'], mf['filename'])
            if os.path.exists(mf_path):
                os.remove(mf_path)
        # Delete review images
        cur.execute("SELECT image FROM reviews WHERE product_id=%s AND image IS NOT NULL", (delete_id,))
        review_images = cur.fetchall()
        reviews_folder = os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'reviews')
        for ri in review_images:
            ri_path = os.path.join(reviews_folder, ri['image'])
            if os.path.exists(ri_path):
                os.remove(ri_path)
        cur.execute("DELETE FROM products WHERE id=%s", (delete_id,))
        db.commit()
        success = 'Product deleted successfully.'

    # Handle Toggle Status
    elif toggle_id := request.args.get('toggle', type=int):
        cur.execute("UPDATE products SET status=IF(status='active','inactive','active') WHERE id=%s", (toggle_id,))
        db.commit()
        success = 'Product status updated.'

    # Handle Add / Edit
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        benefits = request.form.get('benefits', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0) or 0)
        original_price = float(request.form.get('original_price', 0) or 0)
        status = request.form.get('status', 'active')
        featured = 1 if request.form.get('featured') else 0
        rating = float(request.form.get('rating', 0) or 0)
        reviews_count = int(request.form.get('reviews_count', 0) or 0)
        edit_id = int(request.form.get('edit_id', 0) or 0)

        if not name or price <= 0:
            error = 'Product name and price are required.'
        else:
            # Handle main image upload (thumbnail / primary image)
            image_name = 'default.jpg'
            file = request.files.get('image')
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                image_name = f"product_{int(time.time())}_{random.randint(1000, 9999)}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))
            elif file and file.filename:
                error = 'Invalid main image format. Allowed: JPG, PNG, GIF, WEBP.'

            if not error:
                if edit_id > 0:
                    if image_name != 'default.jpg':
                        cur.execute("SELECT image FROM products WHERE id=%s", (edit_id,))
                        old_img_row = cur.fetchone()
                        if old_img_row and old_img_row['image'] != 'default.jpg':
                            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_img_row['image'])
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        cur.execute("""UPDATE products SET name=%s, category=%s, benefits=%s, description=%s,
                                       price=%s, original_price=%s, image=%s, status=%s, featured=%s, rating=%s, reviews_count=%s
                                       WHERE id=%s""",
                                    (name, category, benefits, description, price, original_price,
                                     image_name, status, featured, rating, reviews_count, edit_id))
                    else:
                        cur.execute("""UPDATE products SET name=%s, category=%s, benefits=%s, description=%s,
                                       price=%s, original_price=%s, status=%s, featured=%s, rating=%s, reviews_count=%s
                                       WHERE id=%s""",
                                    (name, category, benefits, description, price, original_price,
                                     status, featured, rating, reviews_count, edit_id))
                    db.commit()
                    product_id_for_media = edit_id
                    success = 'Product updated successfully.'
                else:
                    cur.execute("""INSERT INTO products (name, category, benefits, description, price, original_price,
                                   image, status, featured, rating, reviews_count)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                (name, category, benefits, description, price, original_price,
                                 image_name, status, featured, rating, reviews_count))
                    db.commit()
                    product_id_for_media = cur.lastrowid
                    success = 'Product added successfully.'

                # Handle multiple media uploads (images + videos)
                media_files = request.files.getlist('media_files')
                media_error = False
                for idx, mf in enumerate(media_files):
                    if mf and mf.filename:
                        if allowed_media_file(mf.filename):
                            ext = mf.filename.rsplit('.', 1)[1].lower()
                            media_type = get_media_type(mf.filename)
                            media_name = f"media_{product_id_for_media}_{int(time.time())}_{random.randint(1000, 9999)}_{idx}.{ext}"
                            mf.save(os.path.join(app.config['UPLOAD_FOLDER'], media_name))
                            cur.execute("""INSERT INTO product_media (product_id, filename, media_type, sort_order)
                                           VALUES (%s, %s, %s, %s)""",
                                        (product_id_for_media, media_name, media_type, idx))
                        else:
                            media_error = True
                db.commit()
                if media_error:
                    flash(success + ' Some media files were skipped (invalid format).', 'success')
                else:
                    flash(success, 'success')
                db.close()
                return redirect(url_for('admin_manage_products'))

    # Fetch product for editing
    if action == 'edit':
        edit_id = request.args.get('id', type=int)
        if edit_id:
            cur.execute("SELECT * FROM products WHERE id=%s", (edit_id,))
            edit_product = cur.fetchone()
            if edit_product:
                cur.execute("SELECT * FROM product_media WHERE product_id=%s ORDER BY sort_order", (edit_id,))
                edit_media = cur.fetchall()
            else:
                error = 'Product not found.'
                action = 'list'

    # Fetch all products for list view
    all_products = []
    if action == 'list':
        cur.execute("SELECT * FROM products ORDER BY created_at DESC")
        all_products = cur.fetchall()

    db.close()

    return render_template('admin/manage_products.html',
                           admin_page_title='Manage Products',
                           action=action,
                           error=error,
                           success=success,
                           products=all_products,
                           edit_product=edit_product,
                           edit_media=edit_media)


# ---------- Admin Manage Users ----------
@app.route('/admin/users')
@admin_required
def admin_manage_users():
    db = get_db()
    cur = db.cursor()
    error = ''
    success = ''

    # Handle Delete
    delete_id = request.args.get('delete', type=int)
    if delete_id:
        if delete_id == session['user_id']:
            error = 'You cannot delete your own account.'
        else:
            cur.execute("DELETE FROM users WHERE id=%s AND role='client'", (delete_id,))
            if cur.rowcount > 0:
                db.commit()
                success = 'User deleted successfully.'
            else:
                error = 'Failed to delete user or user is an admin.'

    # Handle Toggle (only if no delete was processed)
    elif toggle_id := request.args.get('toggle', type=int):
        if toggle_id == session['user_id']:
            error = 'You cannot change your own status.'
        else:
            cur.execute("UPDATE users SET status=IF(status='active','inactive','active') WHERE id=%s AND role='client'", (toggle_id,))
            db.commit()
            success = 'User status updated.'

    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cur.fetchall()

    total_users = len(users)
    total_admins = sum(1 for u in users if u['role'] == 'admin')
    total_clients = total_users - total_admins
    active_users = sum(1 for u in users if u['status'] == 'active')
    inactive_users = total_users - active_users

    db.close()

    return render_template('admin/manage_users.html',
                           admin_page_title='Manage Users',
                           users=users,
                           total_users=total_users,
                           total_admins=total_admins,
                           total_clients=total_clients,
                           active_users=active_users,
                           inactive_users=inactive_users,
                           error=error,
                           success=success)


# ---------- Admin Manage Offers ----------
@app.route('/admin/offers', methods=['GET', 'POST'])
@admin_required
def admin_manage_offers():
    db = get_db()
    cur = db.cursor()
    error = ''
    success = ''
    action = request.args.get('action', 'list')
    edit_offer = None

    # Handle Delete
    delete_id = request.args.get('delete', type=int)
    if delete_id:
        cur.execute("DELETE FROM offers WHERE id=%s", (delete_id,))
        db.commit()
        success = 'Offer deleted successfully.'

    # Handle Toggle Status
    elif toggle_id := request.args.get('toggle', type=int):
        cur.execute("UPDATE offers SET status=IF(status='active','inactive','active') WHERE id=%s", (toggle_id,))
        db.commit()
        success = 'Offer status updated.'

    # Handle Add / Edit
    if request.method == 'POST':
        label = request.form.get('label', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-tag').strip()
        status = request.form.get('status', 'active')
        sort_order = int(request.form.get('sort_order', 0) or 0)
        edit_id = int(request.form.get('edit_id', 0) or 0)

        if not label or not description:
            error = 'Offer label and description are required.'
        else:
            if edit_id > 0:
                cur.execute("""UPDATE offers SET label=%s, description=%s, icon=%s, status=%s, sort_order=%s
                               WHERE id=%s""",
                            (label, description, icon, status, sort_order, edit_id))
                db.commit()
                success = 'Offer updated successfully.'
            else:
                cur.execute("""INSERT INTO offers (label, description, icon, status, sort_order)
                               VALUES (%s, %s, %s, %s, %s)""",
                            (label, description, icon, status, sort_order))
                db.commit()
                success = 'Offer added successfully.'
            action = 'list'

    # Get offer for edit
    if action == 'edit':
        edit_id = request.args.get('id', type=int)
        if edit_id:
            cur.execute("SELECT * FROM offers WHERE id=%s", (edit_id,))
            edit_offer = cur.fetchone()

    # Get all offers
    cur.execute("SELECT * FROM offers ORDER BY sort_order ASC, created_at DESC")
    offers = cur.fetchall()

    db.close()

    return render_template('admin/manage_offers.html',
                           admin_page_title='Manage Offers',
                           offers=offers,
                           edit_offer=edit_offer,
                           action=action,
                           error=error,
                           success=success)


# ---------- Admin Logout ----------
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


# ============================================
# CART & ORDER ROUTES
# ============================================

def generate_order_number():
    """Generate a unique order number like AKH-20260305-XXXX."""
    date_part = time.strftime('%Y%m%d')
    rand_part = random.randint(1000, 9999)
    return f"AKH-{date_part}-{rand_part}"


def get_cart_count():
    """Get the number of items in the current user's cart."""
    if 'user_id' not in session:
        return 0
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT SUM(quantity) as cnt FROM cart WHERE user_id=%s", (session['user_id'],))
        result = cur.fetchone()
        db.close()
        return result['cnt'] or 0
    except Exception:
        return 0


@app.context_processor
def inject_cart_and_wishlist():
    cart_count = get_cart_count()
    wishlist_ids = []
    
    # Get wishlisted product IDs for logged-in users
    if 'user_id' in session:
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT product_id FROM wishlist WHERE user_id=%s", (session['user_id'],))
            wishlist_items = cur.fetchall()
            wishlist_ids = [item['product_id'] for item in wishlist_items]
            db.close()
        except:
            wishlist_ids = []
    
    return {
        'cart_count': cart_count,
        'wishlist_ids': wishlist_ids,
    }


# ---------- Add to Cart ----------
@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    buy_now = request.form.get('buy_now') == '1'

    if not product_id or quantity < 1:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid product or quantity.'})
        flash('Invalid product or quantity.', 'error')
        return redirect(url_for('products'))

    db = get_db()
    cur = db.cursor()

    # Verify product exists and is active
    cur.execute("SELECT id, name, price FROM products WHERE id=%s AND status='active'", (product_id,))
    product = cur.fetchone()
    if not product:
        db.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Product not found.'})
        flash('Product not found.', 'error')
        return redirect(url_for('products'))

    # Insert or update cart item
    cur.execute("""INSERT INTO cart (user_id, product_id, quantity)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE quantity = quantity + %s""",
                (session['user_id'], product_id, quantity, quantity))
    db.commit()

    # Get updated cart count
    cur.execute("SELECT SUM(quantity) as cnt FROM cart WHERE user_id=%s", (session['user_id'],))
    cart_count = cur.fetchone()['cnt'] or 0
    db.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'{product["name"]} added to cart!', 'cart_count': cart_count})

    if buy_now:
        return redirect(url_for('checkout'))

    flash(f'{product["name"]} added to cart!', 'success')
    return redirect(request.referrer or url_for('products'))


# ---------- View Cart ----------
@app.route('/cart')
@login_required
def view_cart():
    db = get_db()
    cur = db.cursor()

    cur.execute("""SELECT c.id, c.quantity, p.id as product_id, p.name, p.price,
                          p.original_price, p.image, p.category
                   FROM cart c
                   JOIN products p ON c.product_id = p.id
                   WHERE c.user_id=%s AND p.status='active'
                   ORDER BY c.created_at DESC""", (session['user_id'],))
    cart_items = cur.fetchall()

    # Calculate totals
    subtotal = sum(float(item['price']) * item['quantity'] for item in cart_items)
    shipping = 0 if subtotal >= 300 else 50
    total = subtotal + shipping

    db.close()

    return render_template('cart.html',
                           page_title='Shopping Cart',
                           cart_items=cart_items,
                           subtotal=subtotal,
                           shipping=shipping,
                           total=total)


# ---------- Update Cart ----------
@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    cart_id = request.form.get('cart_id', type=int)
    quantity = request.form.get('quantity', type=int)

    if not cart_id or not quantity:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid request.'})
        flash('Invalid request.', 'error')
        return redirect(url_for('view_cart'))

    db = get_db()
    cur = db.cursor()

    if quantity <= 0:
        cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, session['user_id']))
    else:
        cur.execute("UPDATE cart SET quantity=%s WHERE id=%s AND user_id=%s",
                    (quantity, cart_id, session['user_id']))
    db.commit()

    # Get updated cart data
    cur.execute("""SELECT c.id, c.quantity, p.price
                   FROM cart c JOIN products p ON c.product_id = p.id
                   WHERE c.user_id=%s AND p.status='active'""", (session['user_id'],))
    items = cur.fetchall()
    subtotal = sum(float(i['price']) * i['quantity'] for i in items)
    shipping = 0 if subtotal >= 300 else 50
    total = subtotal + shipping
    cart_count = sum(i['quantity'] for i in items)
    db.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'subtotal': subtotal, 'shipping': shipping,
                        'total': total, 'cart_count': cart_count})

    flash('Cart updated.', 'success')
    return redirect(url_for('view_cart'))


# ---------- Remove from Cart ----------
@app.route('/cart/remove/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, session['user_id']))
    db.commit()
    db.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    flash('Item removed from cart.', 'success')
    return redirect(url_for('view_cart'))


# ---------- Add to Wishlist ----------
@app.route('/wishlist/add', methods=['POST'])
@login_required
def add_to_wishlist():
    product_id = request.form.get('product_id', type=int)

    if not product_id:
        return jsonify({'success': False, 'message': 'Invalid product.'})

    db = get_db()
    cur = db.cursor()

    # Verify product exists
    cur.execute("SELECT id FROM products WHERE id=%s AND status='active'", (product_id,))
    if not cur.fetchone():
        db.close()
        return jsonify({'success': False, 'message': 'Product not found.'})

    # Add to wishlist
    try:
        cur.execute("INSERT INTO wishlist (user_id, product_id) VALUES (%s, %s)",
                    (session['user_id'], product_id))
        db.commit()
        db.close()
        return jsonify({'success': True, 'message': 'Added to wishlist!'})
    except MySQLdb.IntegrityError:
        # Already in wishlist
        db.close()
        return jsonify({'success': False, 'message': 'Already in wishlist.'})
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'message': str(e)})


# ---------- Remove from Wishlist ----------
@app.route('/wishlist/remove', methods=['POST'])
@login_required
def remove_from_wishlist():
    product_id = request.form.get('product_id', type=int)

    if not product_id:
        return jsonify({'success': False, 'message': 'Invalid product.'})

    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM wishlist WHERE user_id=%s AND product_id=%s",
                (session['user_id'], product_id))
    db.commit()
    db.close()

    return jsonify({'success': True, 'message': 'Removed from wishlist!'})


# ---------- View Wishlist ----------
@app.route('/wishlist')
@login_required
def view_wishlist():
    db = get_db()
    cur = db.cursor()

    cur.execute("""SELECT w.id, p.id as product_id, p.name, p.price,
                          p.original_price, p.image, p.category, p.rating
                   FROM wishlist w
                   JOIN products p ON w.product_id = p.id
                   WHERE w.user_id=%s AND p.status='active'
                   ORDER BY w.created_at DESC""", (session['user_id'],))
    wishlist_items = cur.fetchall()

    db.close()

    return render_template('wishlist.html',
                           page_title='My Wishlist',
                           wishlist_items=wishlist_items)


# ---------- Checkout ----------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    db = get_db()
    cur = db.cursor()

    # Get cart items
    cur.execute("""SELECT c.id, c.quantity, p.id as product_id, p.name, p.price,
                          p.original_price, p.image, p.category
                   FROM cart c
                   JOIN products p ON c.product_id = p.id
                   WHERE c.user_id=%s AND p.status='active'""", (session['user_id'],))
    cart_items = cur.fetchall()

    if not cart_items:
        db.close()
        flash('Your cart is empty.', 'error')
        return redirect(url_for('products'))

    subtotal = sum(float(item['price']) * item['quantity'] for item in cart_items)
    shipping = 0 if subtotal >= 300 else 50
    total = subtotal + shipping

    # Get user info for pre-filling
    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()

    def render_checkout_page():
        checkout_payload = build_razorpay_checkout_data(total, user)
        return render_template('checkout.html',
                               page_title='Checkout',
                               cart_items=cart_items,
                               subtotal=subtotal,
                               shipping=shipping,
                               total=total,
                               user=user,
                               razorpay_checkout=checkout_payload,
                               razorpay_enabled=bool(checkout_payload))

    razorpay_checkout = build_razorpay_checkout_data(total, user)
    razorpay_enabled = bool(razorpay_checkout)

    if request.method == 'POST':
        shipping_name = request.form.get('shipping_name', '').strip()
        shipping_phone = request.form.get('shipping_phone', '').strip()
        shipping_email = request.form.get('shipping_email', '').strip()
        shipping_address = request.form.get('shipping_address', '').strip()
        shipping_state = request.form.get('shipping_state', '').strip()
        shipping_district = request.form.get('shipping_district', '').strip()
        shipping_pincode = request.form.get('shipping_pincode', '').strip()
        payment_method = request.form.get('payment_method', 'cod').strip()
        notes = request.form.get('notes', '').strip()

        # Collect payment metadata for operational clarity in admin/order emails.
        payment_method_map = {
            'cod': 'Cash on Delivery',
            'razorpay': 'Razorpay (Online)',
            'upi': 'UPI Payment',
            'card': 'Card Payment',
            'net_banking': 'Net Banking',
            'bank_transfer': 'Bank Transfer',
        }
        if payment_method not in payment_method_map:
            payment_method = 'cod'

        gateway_order_id = None
        gateway_payment_id = None
        gateway_signature = None
        payment_status_for_order = 'pending'

        payment_details = []
        if payment_method == 'razorpay':
            razorpay_order_id = request.form.get('razorpay_order_id', '').strip()
            razorpay_payment_id = request.form.get('razorpay_payment_id', '').strip()
            razorpay_signature = request.form.get('razorpay_signature', '').strip()

            if not razorpay_enabled:
                db.close()
                flash('Online payment is currently unavailable. Please choose another payment method.', 'error')
                return render_checkout_page()

            if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
                db.close()
                flash('Payment was not completed. Please try paying again.', 'error')
                return render_checkout_page()

            razorpay_client = get_razorpay_client()
            if razorpay_client is None:
                db.close()
                flash('Online payment setup is incomplete. Please contact support.', 'error')
                return render_checkout_page()

            try:
                razorpay_client.utility.verify_payment_signature({
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature,
                })
                payment_info = razorpay_client.payment.fetch(razorpay_payment_id)
            except Exception as e:
                app.logger.warning(f'Razorpay verification failed: {e}')
                db.close()
                flash('Payment verification failed. If amount was debited, contact support with payment ID.', 'error')
                return render_checkout_page()

            expected_amount = int(round(float(total) * 100))
            expected_currency = (app.config.get('RAZORPAY_CURRENCY') or 'INR').strip().upper() or 'INR'
            payment_amount = int(payment_info.get('amount') or 0)
            payment_currency = (payment_info.get('currency') or '').upper()
            payment_status = (payment_info.get('status') or '').lower()
            payment_order_id = payment_info.get('order_id')

            if payment_order_id != razorpay_order_id or payment_amount != expected_amount or payment_currency != expected_currency or payment_status not in ['captured', 'authorized']:
                db.close()
                flash('Payment details did not match order total. Please try again.', 'error')
                return render_checkout_page()

            gateway_order_id = razorpay_order_id
            gateway_payment_id = razorpay_payment_id
            gateway_signature = razorpay_signature
            payment_status_for_order = 'paid'

            payment_details.append(f'Gateway: Razorpay')
            payment_details.append(f'Razorpay Order ID: {razorpay_order_id}')
            payment_details.append(f'Razorpay Payment ID: {razorpay_payment_id}')
            payment_details.append(f'Razorpay Status: {payment_status}')
        elif payment_method == 'upi':
            upi_app = request.form.get('upi_app', '').strip()
            upi_id = request.form.get('upi_id', '').strip()
            if upi_app:
                payment_details.append(f'App: {upi_app}')
            if upi_id:
                payment_details.append(f'UPI ID: {upi_id}')
        elif payment_method == 'card':
            card_type = request.form.get('card_type', '').strip()
            card_network = request.form.get('card_network', '').strip()
            card_last4 = request.form.get('card_last4', '').strip()
            if card_type:
                payment_details.append(f'Type: {card_type}')
            if card_network:
                payment_details.append(f'Network: {card_network}')
            if card_last4:
                payment_details.append(f'Card ending: {card_last4}')
        elif payment_method == 'net_banking':
            nb_bank = request.form.get('net_banking_bank', '').strip()
            nb_tier = request.form.get('net_banking_tier', '').strip()
            if nb_bank:
                payment_details.append(f'Bank: {nb_bank}')
            if nb_tier:
                payment_details.append(f'Category: {nb_tier}')
        elif payment_method == 'bank_transfer':
            transfer_mode = request.form.get('transfer_mode', '').strip()
            transfer_bank = request.form.get('transfer_bank', '').strip()
            transfer_ref = request.form.get('transfer_reference', '').strip()
            if transfer_mode:
                payment_details.append(f'Mode: {transfer_mode}')
            if transfer_bank:
                payment_details.append(f'Bank: {transfer_bank}')
            if transfer_ref:
                payment_details.append(f'Reference: {transfer_ref}')

        payment_label = payment_method_map[payment_method]
        payment_meta_text = '; '.join(payment_details)
        full_notes = notes
        if payment_meta_text:
            full_notes = f'{notes}\n\nPayment Details: {payment_meta_text}'.strip()

        if not shipping_name or not shipping_phone or not shipping_address or not shipping_state or not shipping_district or not shipping_pincode:
            db.close()
            flash('Please fill in all required shipping fields.', 'error')
            return render_checkout_page()

        # Generate unique order number
        order_number = generate_order_number()

        # Create order
        paid_at_value = datetime.now() if payment_status_for_order == 'paid' else None

        cur.execute("""INSERT INTO orders (user_id, order_number, total_amount, shipping_name,
                                             shipping_phone, shipping_email, shipping_address, shipping_state,
                                             shipping_district, shipping_pincode, payment_method,
                                             payment_gateway_order_id, payment_gateway_payment_id,
                                             payment_gateway_signature, payment_status, paid_at, notes)
                                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (session['user_id'], order_number, total, shipping_name, shipping_phone,
                                         shipping_email or None, shipping_address, shipping_state,
                                         shipping_district, shipping_pincode, payment_method,
                                         gateway_order_id, gateway_payment_id,
                                         gateway_signature, payment_status_for_order,
                                         paid_at_value, full_notes or None))
        order_id = cur.lastrowid

        # Create order items
        for item in cart_items:
            item_subtotal = float(item['price']) * item['quantity']
            cur.execute("""INSERT INTO order_items (order_id, product_id, product_name,
                           product_price, quantity, subtotal)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (order_id, item['product_id'], item['name'],
                         item['price'], item['quantity'], item_subtotal))

        # Clear cart
        cur.execute("DELETE FROM cart WHERE user_id=%s", (session['user_id'],))
        db.commit()

        # Send order confirmation email
        try:
            email_body = f"""New Order Received!

Order Number: {order_number}
Customer: {shipping_name}
Phone: {shipping_phone}
Address: {shipping_address}, {shipping_district}, {shipping_state} - {shipping_pincode}
Payment: {payment_label}
Total: ₹{total:,.0f}

Items:
"""
            if payment_meta_text:
                email_body += f"Payment Details: {payment_meta_text}\n\n"
            for item in cart_items:
                email_body += f"  - {item['name']} x{item['quantity']} = ₹{float(item['price']) * item['quantity']:,.0f}\n"

            msg = MailMessage(
                subject=f'[New Order] {order_number} - {shipping_name}',
                recipients=[app.config.get('CONTACT_RECEIVE_EMAIL', 'admin@akhgam.com')],
                body=email_body
            )
            mail.send(msg)
        except Exception as e:
            app.logger.error(f'Order email error: {e}')

        db.close()
        flash(f'Order placed successfully! Your order number is {order_number}.', 'success')
        return redirect(url_for('order_confirmation', order_number=order_number))

    db.close()
    return render_template('checkout.html',
                           page_title='Checkout',
                           cart_items=cart_items,
                           subtotal=subtotal,
                           shipping=shipping,
                           total=total,
                           user=user,
                           razorpay_checkout=razorpay_checkout,
                           razorpay_enabled=razorpay_enabled)


@app.route('/webhooks/razorpay', methods=['POST'])
def razorpay_webhook():
    """Receive and verify Razorpay webhooks, then update order payment status."""
    payload = request.get_data()
    signature = request.headers.get('X-Razorpay-Signature', '')

    if not verify_razorpay_webhook_signature(payload, signature):
        return jsonify({'success': False, 'message': 'Invalid webhook signature'}), 400

    event = request.json or {}
    event_type = event.get('event', '')
    payment_entity = ((event.get('payload') or {}).get('payment') or {}).get('entity') or {}

    gateway_payment_id = (payment_entity.get('id') or '').strip()
    gateway_order_id = (payment_entity.get('order_id') or '').strip()
    gateway_status = (payment_entity.get('status') or '').strip().lower()

    if not gateway_payment_id and not gateway_order_id:
        return jsonify({'success': True, 'message': 'No relevant payment identifiers'}), 200

    if event_type in ['payment.captured', 'payment.authorized']:
        mapped_status = 'paid'
    elif event_type in ['payment.failed']:
        mapped_status = 'failed'
    elif event_type in ['refund.processed', 'refund.created']:
        mapped_status = 'refunded'
    else:
        mapped_status = 'pending'

    db = None
    try:
        db = get_db()
        cur = db.cursor()

        if gateway_payment_id:
            cur.execute(
                """UPDATE orders
                   SET payment_gateway_order_id = COALESCE(payment_gateway_order_id, %s),
                       payment_gateway_payment_id = %s,
                       payment_status = %s,
                       paid_at = CASE WHEN %s='paid' AND paid_at IS NULL THEN NOW() ELSE paid_at END
                   WHERE payment_gateway_payment_id = %s OR payment_gateway_order_id = %s""",
                (gateway_order_id or None, gateway_payment_id, mapped_status, mapped_status, gateway_payment_id, gateway_order_id or None),
            )
        else:
            cur.execute(
                """UPDATE orders
                   SET payment_status = %s,
                       paid_at = CASE WHEN %s='paid' AND paid_at IS NULL THEN NOW() ELSE paid_at END
                   WHERE payment_gateway_order_id = %s""",
                (mapped_status, mapped_status, gateway_order_id),
            )

        if cur.rowcount == 0 and gateway_order_id:
            cur.execute(
                """UPDATE orders
                   SET payment_gateway_order_id = %s,
                       payment_gateway_payment_id = COALESCE(%s, payment_gateway_payment_id),
                       payment_status = %s,
                       paid_at = CASE WHEN %s='paid' AND paid_at IS NULL THEN NOW() ELSE paid_at END
                   WHERE notes LIKE %s""",
                (gateway_order_id, gateway_payment_id or None, mapped_status, mapped_status, f"%{gateway_order_id}%"),
            )

        db.commit()
    except Exception as e:
        if db:
            db.rollback()
        app.logger.error(f'Razorpay webhook processing failed: {e}')
        return jsonify({'success': False, 'message': 'Webhook processing error'}), 500
    finally:
        if db:
            db.close()

    app.logger.info(f'Razorpay webhook processed: event={event_type}, payment_id={gateway_payment_id}, order_id={gateway_order_id}, status={gateway_status}')
    return jsonify({'success': True}), 200


# ---------- Order Confirmation ----------
@app.route('/order/confirmation/<order_number>')
@login_required
def order_confirmation(order_number):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM orders WHERE order_number=%s AND user_id=%s",
                (order_number, session['user_id']))
    order = cur.fetchone()

    if not order:
        db.close()
        flash('Order not found.', 'error')
        return redirect(url_for('my_orders'))

    cur.execute("SELECT * FROM order_items WHERE order_id=%s", (order['id'],))
    items = cur.fetchall()
    db.close()

    return render_template('order_confirmation.html',
                           page_title='Order Confirmed',
                           order=order,
                           items=items)


# ---------- My Orders ----------
@app.route('/my-orders')
@login_required
def my_orders():
    db = get_db()
    cur = db.cursor()

    cur.execute("""SELECT o.*, COUNT(oi.id) as item_count
                   FROM orders o
                   LEFT JOIN order_items oi ON o.id = oi.order_id
                   WHERE o.user_id=%s
                   GROUP BY o.id
                   ORDER BY o.created_at DESC""", (session['user_id'],))
    orders = cur.fetchall()
    db.close()

    return render_template('my_orders.html',
                           page_title='My Orders',
                           orders=orders)


# ---------- Order Detail ----------
@app.route('/order/<order_number>')
@login_required
def order_detail(order_number):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM orders WHERE order_number=%s AND user_id=%s",
                (order_number, session['user_id']))
    order = cur.fetchone()

    if not order:
        db.close()
        flash('Order not found.', 'error')
        return redirect(url_for('my_orders'))

    cur.execute("""SELECT oi.*, p.image
                   FROM order_items oi
                   LEFT JOIN products p ON oi.product_id = p.id
                   WHERE oi.order_id=%s""", (order['id'],))
    items = cur.fetchall()
    db.close()

    return render_template('order_detail.html',
                           page_title=f'Order {order_number}',
                           order=order,
                           items=items)


# ---------- Cancel Order (Client) ----------
@app.route('/order/<order_number>/cancel', methods=['POST'])
@login_required
def cancel_order(order_number):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT id, status FROM orders WHERE order_number=%s AND user_id=%s",
                (order_number, session['user_id']))
    order = cur.fetchone()

    if not order:
        db.close()
        flash('Order not found.', 'error')
        return redirect(url_for('my_orders'))

    if order['status'] != 'pending':
        db.close()
        flash('This order cannot be cancelled because it has already been accepted by admin.', 'error')
        return redirect(url_for('order_detail', order_number=order_number))

    cur.execute("UPDATE orders SET status='cancelled' WHERE id=%s", (order['id'],))
    db.commit()
    db.close()

    flash('Order cancelled successfully.', 'success')
    return redirect(url_for('my_orders'))


# ---------- Admin: Manage Orders ----------
@app.route('/admin/orders')
@admin_required
def admin_orders():
    db = get_db()
    cur = db.cursor()

    status_filter = request.args.get('status', '').strip()

    where = ""
    params = []
    if status_filter:
        where = "WHERE o.status=%s"
        params.append(status_filter)

    cur.execute(f"""SELECT o.*, u.name as customer_name, u.email as customer_email,
                           COUNT(oi.id) as item_count
                    FROM orders o
                    JOIN users u ON o.user_id = u.id
                    LEFT JOIN order_items oi ON o.id = oi.order_id
                    {where}
                    GROUP BY o.id
                    ORDER BY o.created_at DESC""", params)
    orders = cur.fetchall()

    # Get order stats
    cur.execute("SELECT COUNT(*) as cnt FROM orders")
    total_orders = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='pending'")
    pending_orders = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='delivered'")
    delivered_orders = cur.fetchone()['cnt']
    cur.execute("SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE status != 'cancelled'")
    total_revenue = cur.fetchone()['total']

    db.close()

    return render_template('admin/admin_orders.html',
                           admin_page_title='Manage Orders',
                           orders=orders,
                           status_filter=status_filter,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           delivered_orders=delivered_orders,
                           total_revenue=total_revenue)


# ---------- Admin: Update Order Status ----------
@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    new_status = request.form.get('status', '').strip()
    valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']

    if new_status not in valid_statuses:
        flash('Invalid status.', 'error')
        return redirect(url_for('admin_orders'))

    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE orders SET status=%s WHERE id=%s", (new_status, order_id))
    db.commit()
    db.close()

    flash(f'Order status updated to {new_status}.', 'success')
    return redirect(url_for('admin_orders'))


# ---------- Admin: View Order Detail ----------
@app.route('/admin/order/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""SELECT o.*, u.name as customer_name, u.email as customer_email,
                          u.phone as customer_phone
                   FROM orders o
                   JOIN users u ON o.user_id = u.id
                   WHERE o.id=%s""", (order_id,))
    order = cur.fetchone()

    if not order:
        db.close()
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))

    cur.execute("""SELECT oi.*, p.image
                   FROM order_items oi
                   LEFT JOIN products p ON oi.product_id = p.id
                   WHERE oi.order_id=%s""", (order_id,))
    items = cur.fetchall()
    db.close()

    return render_template('admin/admin_order_detail.html',
                           admin_page_title=f'Order {order["order_number"]}',
                           order=order,
                           items=items)


# ============================================
# EXCEL ROUTES
# ============================================

@app.route('/admin/export/products')
@admin_required
def export_products_excel():
    """Export all products to Excel file."""
    from excel_handler import export_products
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM products ORDER BY created_at DESC")
    products_data = cur.fetchall()
    db.close()

    filepath = export_products(products_data, app.config.get('EXCEL_FOLDER', 'data'))
    return send_file(filepath, as_attachment=True, download_name='akhgam_products.xlsx')


@app.route('/admin/export/users')
@admin_required
def export_users_excel():
    """Export all clients to Excel file."""
    from excel_handler import export_users
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, name, email, phone, age, gender, address, state, district, pincode, role, status, created_at FROM users WHERE role='client' ORDER BY created_at DESC")
    users_data = cur.fetchall()
    db.close()

    filepath = export_users(users_data, app.config.get('EXCEL_FOLDER', 'data'))
    return send_file(filepath, as_attachment=True, download_name='akhgam_users.xlsx')


@app.route('/admin/import/products', methods=['POST'])
@admin_required
def import_products_excel():
    """Import products from uploaded Excel file."""
    from excel_handler import import_products
    file = request.files.get('excel_file')
    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        flash('Please upload a valid Excel file (.xlsx).', 'error')
        return redirect(url_for('admin_manage_products'))

    filepath = os.path.join(app.config.get('EXCEL_FOLDER', 'data'), 'import_products.xlsx')
    file.save(filepath)

    db = get_db()
    cur = db.cursor()
    count = import_products(filepath, cur, db)
    db.close()

    flash(f'Successfully imported {count} products from Excel.', 'success')
    return redirect(url_for('admin_manage_products'))


@app.route('/admin/import/users', methods=['POST'])
@admin_required
def import_users_excel():
    """Import users from uploaded Excel file."""
    from excel_handler import import_users
    file = request.files.get('excel_file')
    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        flash('Please upload a valid Excel file (.xlsx).', 'error')
        return redirect(url_for('admin_manage_users'))

    filepath = os.path.join(app.config.get('EXCEL_FOLDER', 'data'), 'import_users.xlsx')
    file.save(filepath)

    db = get_db()
    cur = db.cursor()
    count = import_users(filepath, cur, db)
    db.close()

    flash(f'Successfully imported {count} users from Excel.', 'success')
    return redirect(url_for('admin_manage_users'))


# ============================================
# Run
# ============================================
if __name__ == '__main__':
    print('Admin login URL: http://127.0.0.1:5000/admin/login')
    #print('Admin dashboard URL: http://127.0.0.1:5000/admin/dashboard')
    app.run(debug=True, port=5000)
