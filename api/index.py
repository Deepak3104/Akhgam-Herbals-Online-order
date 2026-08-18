from vercel_wsgi import make_wsgi_handler
from app import app

# Create Vercel WSGI handler for the Flask app
handler = make_wsgi_handler(app)
