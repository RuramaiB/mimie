# ==============================================================
#  Apache Superset Custom Configuration (superset_config.py)
# ==============================================================
import os

# Secret key for encrypting passwords and sessions in metadata database
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', '9a7c36a4f91048b3b4d45d8b725c8397a6e191d918c5e3faef625a62bc2b88dc')

# Enable CORS for frontend integration
ENABLE_CORS = True
CORS_OPTIONS = {
    'supports_credentials': True,
    'allow_headers': ['*'],
    'resources': ['*'],
    'origins': ['*']
}

# --------------------------------------------------------------
#  SECURITY: Disable Talisman & CSRF Blocks for Local HTTP Dev
# --------------------------------------------------------------
# WTF_CSRF_ENABLED controls Flask-WTF CSRF protection
WTF_CSRF_ENABLED = False

# Talisman blocks non-HTTPS headers and strictly controls CSPs by default.
# Relaxing these settings avoids the common HTTP 500 session error.
TALISMAN_CONFIG = {
    "content_security_policy": None,
    "force_https": False,
    "session_cookie_secure": False,
    "session_cookie_http_only": True,
    "session_cookie_samesite": None,
    "frame_options": "ALLOWALL"
}

# Allow iframe embedding if dashboard integration is needed
HTTP_HEADERS = {'X-Frame-Options': 'ALLOWALL'}

# Set the row limit for SQL Lab and charting
ROW_LIMIT = 5000

# SQLite metadata DB configuration (default fallback)
# Note: For production use, PostgreSQL is highly recommended.
SQL_MAX_CONNECTIONS = 30
SQL_SELECT_LIMIT = 5000
