"""routes/api/__init__.py — REST API v1 for React frontend.

All endpoints return JSON. Authentication is session-based (same Flask session).
CORS is enabled in app.py for the React dev server.
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from . import auth, jobs, profile, applications, employer, admin, push, cron  # noqa: F401, E402
