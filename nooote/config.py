"""Application configuration and shared constants."""

import re
from datetime import timedelta

# Application metadata
SERVICE_NAME = "Nooote"
DEFAULT_DATABASE_URI = "sqlite:///notes.db"
UPLOAD_FOLDER_NAME = "uploads"
SECRET_KEY_FILE = "secret_key"

# Identity and settings
USER_ID_BYTES = 16
USER_ID_MAX_LENGTH = 64
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_HASH_MAX_LENGTH = 255
DISPLAY_NAME_MAX_LENGTH = 64
THEME_MAX_LENGTH = 16
DEFAULT_THEME = "auto"
THEMES = ("auto", "light", "dark")

# Notes
NOTE_ID_BYTES = 6
NOTE_ID_MAX_LENGTH = 128
RECENT_NOTES_LIMIT = 12

# Attachments
ATTACHMENT_ID_BYTES = 18
ATTACHMENT_ID_MIN_LENGTH = 16
ATTACHMENT_ID_MAX_LENGTH = 64
FILENAME_MAX_LENGTH = 255
CONTENT_TYPE_MAX_LENGTH = 128
ATTACHMENT_CACHE_SECONDS = 60 * 60 * 24 * 365

# Identifier and content-type rules shared by routes and validation
NOTE_ID_RE = re.compile(rf"^[\w.-]{{1,{NOTE_ID_MAX_LENGTH}}}$")
USERNAME_RE = re.compile(
    rf"^[\w.-]{{{USERNAME_MIN_LENGTH},{USERNAME_MAX_LENGTH}}}$"
)
ATTACHMENT_ID_RE = re.compile(
    rf"^[A-Za-z0-9_-]{{{ATTACHMENT_ID_MIN_LENGTH},{ATTACHMENT_ID_MAX_LENGTH}}}$"
)
CONTENT_TYPE_RE = re.compile(r"[\w.+-]+/[\w.+-]+")

# Image extensions that are safe to render inline; everything else downloads.
IMAGE_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
}
INLINE_IMAGE_TYPES = frozenset(IMAGE_CONTENT_TYPES.values())

# Retry count when generating unique random identifiers
ID_GENERATION_ATTEMPTS = 10

SECRET_KEY_BYTES = 32


class Config:
    """Default Flask configuration applied by the application factory."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    MAX_NOTE_BYTES = 256 * 1024
    MAX_UPLOAD_BYTES = 8 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
