import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'akhgam-herbals-secret-key-2026')
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # MySQL Database
    MYSQL_HOST = 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '7486')
    MYSQL_DB = 'akhgam_herbals'

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

    # Excel
    EXCEL_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
