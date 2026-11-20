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

# Interface language
LOCALE_MAX_LENGTH = 8
DEFAULT_LOCALE = "zh"
LOCALES = ("zh", "en")
LOCALE_COOKIE = "lang"
LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

# Permission groups
ROLE_MAX_LENGTH = 32
ROLE_GUEST = "guest"
ROLE_MEMBER = "member"
ROLE_ADMIN = "admin"
DEFAULT_ROLE = ROLE_MEMBER
ROLES = (ROLE_MEMBER, ROLE_ADMIN)
ADMIN_USERNAMES_ENV = "NOOOTE_ADMIN_USERNAMES"
PERMISSIONS = (
    "public.view",
    "auth.access",
    "auth.logout",
    "language.switch",
    "files.view",
    "note.read",
    "note.write",
    "note.publish",
    "note.delete",
    "attachment.read",
    "attachment.write",
    "attachment.delete",
    "settings.read",
    "settings.write",
    "manage.view",
    "manage.users.write",
)
GUEST_PERMISSIONS = frozenset(
    {"public.view", "auth.access", "language.switch", "files.view"}
)
MEMBER_PERMISSIONS = GUEST_PERMISSIONS | {
    "auth.logout",
    "note.read",
    "note.write",
    "note.publish",
    "note.delete",
    "attachment.read",
    "attachment.write",
    "attachment.delete",
    "settings.read",
    "settings.write",
}
ROLE_PERMISSIONS = {
    ROLE_GUEST: GUEST_PERMISSIONS,
    ROLE_MEMBER: frozenset(MEMBER_PERMISSIONS),
    ROLE_ADMIN: frozenset(PERMISSIONS),
}

# Console sidebar: entries beyond this count collapse into "More apps"
CONSOLE_NAV_VISIBLE_ITEMS = 6

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

# SQLite: writers wait this long for a lock before raising "database is locked"
SQLITE_BUSY_TIMEOUT_MS = 5000


class Config:
    """Default Flask configuration applied by the application factory."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    MAX_NOTE_BYTES = 256 * 1024
    MAX_UPLOAD_BYTES = 8 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
