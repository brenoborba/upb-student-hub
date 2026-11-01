from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import security
from ..db import get_db
from ..models import (
    Assignment,
    GoogleCredential,
    SakaiCredential,
    SakaiNotification,
    SyncRun,
    User,
)
from ..schemas import (
    AssignmentOut,
    GoogleCredentialIn,
    NotificationOut,
    NotificationSyncOut,
    SakaiCredentialIn,
    SyncRunOut,
    UserCreate,
    UserCreatedOut,
)
from ..services import notifications as notifications_service
from ..services.sync import run_sync

router = APIRouter(prefix="/api")


def _current_user(
    x_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


def _require_owner(user: User, user_id: int) -> None:
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/users", response_model=UserCreatedOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, api_key=security.generate_api_key())
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserCreatedOut(
        id=user.id, email=user.email, created_at=user.created_at, api_key=user.api_key
    )


@router.put("/users/{user_id}/sakai-credentials", status_code=204)
def set_sakai_credentials(
    user_id: int,
    payload: SakaiCredentialIn,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    cred = db.query(SakaiCredential).filter_by(user_id=user_id).first()
    if cred is None:
        cred = SakaiCredential(user_id=user_id)
        db.add(cred)
    cred.username = payload.username
    cred.password_enc = security.encrypt(payload.password)
    cred.base_url = payload.base_url
    db.commit()


@router.put("/users/{user_id}/google-token", status_code=204)
def set_google_token(
    user_id: int,
    payload: GoogleCredentialIn,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    cred = db.query(GoogleCredential).filter_by(user_id=user_id).first()
    if cred is None:
        cred = GoogleCredential(user_id=user_id)
        db.add(cred)
    cred.refresh_token_enc = security.encrypt(payload.refresh_token)
    cred.calendar_id = payload.calendar_id
    cred.calendar_name = payload.calendar_name
    db.commit()


@router.post("/users/{user_id}/sync", response_model=SyncRunOut)
def trigger_sync(
    user_id: int,
    include_past: bool = False,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    if db.query(SakaiCredential).filter_by(user_id=user_id).first() is None:
        raise HTTPException(status_code=400, detail="No Sakai credentials set for this user")
    return run_sync(db, user, include_past=include_past, force=True)


@router.get("/users/{user_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(
    user_id: int,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    return db.query(Assignment).filter_by(user_id=user_id).order_by(Assignment.due_at).all()


@router.get("/users/{user_id}/sync-runs", response_model=list[SyncRunOut])
def list_sync_runs(
    user_id: int,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    return (
        db.query(SyncRun)
        .filter_by(user_id=user_id)
        .order_by(SyncRun.started_at.desc())
        .limit(20)
        .all()
    )


@router.post("/users/{user_id}/notifications/sync", response_model=NotificationSyncOut)
def sync_notifications(
    user_id: int,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    if db.query(SakaiCredential).filter_by(user_id=user_id).first() is None:
        raise HTTPException(status_code=400, detail="No Sakai credentials set for this user")
    count = notifications_service.sync_notifications(db, user)
    return NotificationSyncOut(count=count)


@router.get("/users/{user_id}/notifications", response_model=list[NotificationOut])
def list_notifications(
    user_id: int,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    return (
        db.query(SakaiNotification)
        .filter_by(user_id=user_id)
        .order_by(SakaiNotification.notif_id.desc())
        .all()
    )


@router.post("/users/{user_id}/notifications/{notif_id}/read", status_code=204)
def mark_notification_read(
    user_id: int,
    notif_id: int,
    user: User = Depends(_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(user, user_id)
    row = (
        db.query(SakaiNotification)
        .filter_by(user_id=user_id, notif_id=notif_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notifications_service.mark_read(db, user, row)
