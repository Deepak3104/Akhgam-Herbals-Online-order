import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'akhgam-herbals-secret-key-2026')
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # Database Connection Settings
    MYSQL_URL = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
    DB_TYPE = 'mysql'

    if MYSQL_URL:
        from urllib.parse import urlparse, unquote
        parsed = urlparse(MYSQL_URL)
        if parsed.scheme in ('postgres', 'postgresql'):
            DB_TYPE = 'postgres'
        MYSQL_HOST = parsed.hostname
        MYSQL_PORT = parsed.port or (5432 if DB_TYPE == 'postgres' else 3306)
        MYSQL_USER = parsed.username
        MYSQL_PASSWORD = parsed.password
        if MYSQL_PASSWORD:
            MYSQL_PASSWORD = unquote(MYSQL_PASSWORD)
        MYSQL_DB = parsed.path.lstrip('/')
    else:
        DB_TYPE = os.environ.get('DB_TYPE', 'mysql').lower()
        MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
        MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 5432 if DB_TYPE == 'postgres' else 3306))
        MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '7486')
        MYSQL_DB = os.environ.get('MYSQL_DB', 'postgres' if DB_TYPE == 'postgres' else 'akhgam_herbals')

    MYSQL_SSL = os.environ.get('MYSQL_SSL', 'false').lower() == 'true'



    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'products')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max upload (for videos)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi'}
    ALLOWED_MEDIA_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov', 'avi'}

    # Site Settings
    SITE_NAME = 'Akhgam Herbals'
    SITE_TAGLINE = 'Modern Ayurveda, Beautiful You'
    SITE_EMAIL = 'admin@akhgam.com'
    SITE_PHONE = '+91 8270664493'
    SITE_ADDRESS = '5/47, Unjapalayam, Mohanur, Namakkal - 638182'
    WHATSAPP_NUMBER = '918270664493'

    # Email / SMTP Settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'admin@akhgam.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '16205482')  # Set your app password here or via env var
    MAIL_DEFAULT_SENDER = ('Akhgam Herbals', 'admin@akhgam.com')
    CONTACT_RECEIVE_EMAIL = 'admin@akhgam.com'

    # Razorpay
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_CURRENCY = os.environ.get('RAZORPAY_CURRENCY', 'INR')
    RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')

    # Excel
    EXCEL_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


# ============================================
# Database connection and PG8000/MySQL Wrappers
# ============================================
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

import MySQLdb
import MySQLdb.cursors
import pg8000.dbapi

class PostgresDictCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.description = None
        self.lastrowid = None

    def execute(self, query, params=None):
        if params is not None:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        self.description = self._cursor.description

        # Try to get the last inserted sequence value for lastrowid compatibility
        query_upper = query.strip().upper()
        if query_upper.startswith("INSERT "):
            try:
                old_desc = self.description
                self._cursor.execute("SELECT lastval()")
                res = self._cursor.fetchone()
                self.lastrowid = res[0] if res else None
                self.description = old_desc
            except Exception:
                self.lastrowid = None

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        columns = [col[0] for col in self.description]
        return dict(zip(columns, row))

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        columns = [col[0] for col in self.description]
        return [dict(zip(columns, row)) for row in rows]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PostgresDictCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

def get_db():
    """Get a database connection (MySQL or PostgreSQL)."""
    db_type = Config.DB_TYPE
    if db_type == 'postgres':
        conn = pg8000.dbapi.connect(
            host=Config.MYSQL_HOST,
            port=int(Config.MYSQL_PORT),
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        return PostgresConnectionWrapper(conn)
    else:
        conn_args = {
            'host': Config.MYSQL_HOST,
            'port': int(Config.MYSQL_PORT),
            'user': Config.MYSQL_USER,
            'passwd': Config.MYSQL_PASSWORD,
            'db': Config.MYSQL_DB,
            'charset': 'utf8mb4',
            'cursorclass': MySQLdb.cursors.DictCursor
        }
        if Config.MYSQL_SSL:
            conn_args['ssl'] = {}
        return MySQLdb.connect(**conn_args)

