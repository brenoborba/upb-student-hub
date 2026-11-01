from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class UserCreatedOut(UserOut):
    api_key: str


class SakaiCredentialIn(BaseModel):
    username: str
    password: str
    base_url: str = "https://virtual.ipb.pt"


class GoogleCredentialIn(BaseModel):
    refresh_token: str
    calendar_id: Optional[str] = None
    calendar_name: str = "IPB.Virtual"


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course: str
    title: str
    open_at: Optional[str] = None
    due_at: Optional[str] = None
    status: Optional[str] = None
    status_label: Optional[str] = None
    description_text: Optional[str] = None
    url: Optional[str] = None
    attachments: Optional[list] = None


class SyncRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    stats: Optional[dict] = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notif_id: Optional[int]
    event: str
    category: str
    title: Optional[str] = None
    site_id: Optional[str] = None
    site_title: Optional[str] = None
    from_user: Optional[str] = None
    from_display_name: Optional[str] = None
    url: Optional[str] = None
    ref: Optional[str] = None
    event_date: Optional[str] = None
    formatted_event_date: Optional[str] = None
    body: Optional[str] = None
    body_text: Optional[str] = None
    read: bool
    first_seen_at: datetime


class NotificationSyncOut(BaseModel):
    count: int
