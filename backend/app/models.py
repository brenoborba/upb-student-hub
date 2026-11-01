from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no timezone support)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SakaiCredential(Base):
    __tablename__ = "sakai_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255))
    password_enc: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(String(255), default="https://virtual.ipb.pt")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class GoogleCredential(Base):
    __tablename__ = "google_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    refresh_token_enc: Mapped[str] = mapped_column(Text)
    calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    calendar_name: Mapped[str] = mapped_column(String(255), default="IPB.Virtual")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stable_id: Mapped[str] = mapped_column(String(64), index=True)
    course: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512))
    open_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    due_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachments: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stats: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class SakaiNotification(Base):
    __tablename__ = "sakai_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    notif_id: Mapped[int] = mapped_column(index=True)
    event: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    site_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    from_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    from_display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_user: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    formatted_event_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
