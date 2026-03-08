import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Session security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # Security headers
    TALISMAN_FORCE_HTTPS = True
    TALISMAN_STRICT_TRANSPORT_SECURITY = True
    TALISMAN_CONTENT_SECURITY_POLICY = {
        'default-src': "'self'",
        'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
        'font-src': ["'self'", 'https://fonts.gstatic.com'],
        'img-src': ["'self'", 'data:', 'https://i.scdn.co'],
        'script-src': ["'self'"],
    }

class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP locally
    TALISMAN_FORCE_HTTPS = False

class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False

def get_config():
    """Return configuration based on FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()
