import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hms-dev-secret-key-change-me')
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    DATABASE_URL = (
        os.environ.get('POSTGRES_URL') or
        os.environ.get('DATABASE_URL') or
        os.environ.get('POSTGRES_URL_NON_POOLING') or
        os.environ.get('POSTGRES_PRISMA_URL')
    )
    DATABASE = (
        os.environ.get('DATABASE_FILE') or
        ('/tmp/hms.db' if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') else os.path.join(os.path.dirname(__file__), 'hms.db'))
    )
