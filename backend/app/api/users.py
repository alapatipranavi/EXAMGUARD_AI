from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.user_profile import (
    UserProfileResponse,
    UserProfileUpdate,
    UserPasswordChange,
    NotificationSettings,
)
from app.services.user_service import user_service

router = APIRouter()


@router.get("/me/profile", response_model=UserProfileResponse)
@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns detailed user profile including resolved academic and institutional information."""
    return user_service.get_profile(db, current_user)


@router.put("/me/profile", response_model=UserProfileResponse)
def update_current_user_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates editable personal profile details (first_name, last_name)."""
    return user_service.update_profile(db, current_user, payload)


@router.put("/me/password", status_code=status.HTTP_200_OK)
def change_current_user_password(
    payload: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Changes the authenticated user's password after verifying the current password."""
    user_service.change_password(db, current_user, payload)
    return {"message": "Password changed successfully."}


@router.get("/me/settings", response_model=NotificationSettings)
def get_current_user_settings(
    current_user: User = Depends(get_current_user),
):
    """Returns persistent notification preferences for the authenticated user."""
    return user_service.get_notification_settings(current_user)


@router.put("/me/settings", response_model=NotificationSettings)
def update_current_user_settings(
    payload: NotificationSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates persistent notification preferences for the authenticated user."""
    return user_service.update_notification_settings(db, current_user, payload)
