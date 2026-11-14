from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .config import (
    ATTACHMENT_ID_MAX_LENGTH,
    CONTENT_TYPE_MAX_LENGTH,
    DISPLAY_NAME_MAX_LENGTH,
    FILENAME_MAX_LENGTH,
    NOTE_ID_MAX_LENGTH,
    PASSWORD_HASH_MAX_LENGTH,
    THEME_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    USER_ID_MAX_LENGTH,
)
from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(USER_ID_MAX_LENGTH), primary_key=True)
    username: Mapped[str] = mapped_column(
        String(USERNAME_MAX_LENGTH), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(PASSWORD_HASH_MAX_LENGTH), nullable=False
    )
    display_name: Mapped[str] = mapped_column(
        String(DISPLAY_NAME_MAX_LENGTH), nullable=False, default=""
    )
    default_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    theme: Mapped[str] = mapped_column(
        String(THEME_MAX_LENGTH), nullable=False, default="auto"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class Attachment(db.Model):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(ATTACHMENT_ID_MAX_LENGTH), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(USER_ID_MAX_LENGTH), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(
        String(FILENAME_MAX_LENGTH), nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        String(CONTENT_TYPE_MAX_LENGTH), nullable=False
    )
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )


class Note(db.Model):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(NOTE_ID_MAX_LENGTH), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(USER_ID_MAX_LENGTH), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow, index=True
    )
