import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.academic import College, Department, Section
from app.core.security import verify_password, hash_password
from app.schemas.user_profile import (
    UserProfileResponse,
    UserProfileUpdate,
    UserPasswordChange,
    NotificationSettings,
)


class UserService:
    def get_profile(self, db: Session, user: User) -> UserProfileResponse:
        """Retrieves authenticated user profile with resolved academic & institutional details."""
        college_name = None
        college_code = None
        if user.college_id:
            college = db.query(College).filter(College.id == user.college_id).first()
            if college:
                college_name = college.name
                college_code = college.code

        department_name = None
        department_code = None
        if user.department_id:
            dept = db.query(Department).filter(Department.id == user.department_id).first()
            if dept:
                department_name = dept.name
                department_code = dept.code

        section_name = None
        section_code = None
        if user.section_id:
            sec = db.query(Section).filter(Section.id == user.section_id).first()
            if sec:
                section_name = sec.name
                section_code = sec.code

        return UserProfileResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            is_active=user.is_active,
            is_face_registered=user.is_face_registered,
            face_registered_at=user.face_registered_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            college_id=user.college_id,
            college_name=college_name,
            college_code=college_code,
            department_id=user.department_id,
            department_name=department_name,
            department_code=department_code,
            year_of_study=user.year_of_study,
            section_id=user.section_id,
            section_name=section_name,
            section_code=section_code,
        )

    def update_profile(
        self, db: Session, user: User, update_data: UserProfileUpdate
    ) -> UserProfileResponse:
        """Safely updates personal profile information (first_name, last_name only)."""
        user.first_name = update_data.first_name
        user.last_name = update_data.last_name
        db.commit()
        db.refresh(user)
        return self.get_profile(db, user)

    def change_password(
        self, db: Session, user: User, password_data: UserPasswordChange
    ) -> None:
        """Verifies current password and updates with securely hashed new password."""
        if not verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

        if len(password_data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long.",
            )

        user.password_hash = hash_password(password_data.new_password)
        db.commit()

    def get_notification_settings(self, user: User) -> NotificationSettings:
        """Retrieves user notification preferences or default settings."""
        if user.notification_preferences and isinstance(user.notification_preferences, dict):
            return NotificationSettings(
                exam_reminders=user.notification_preferences.get("exam_reminders", True),
                result_notifications=user.notification_preferences.get("result_notifications", True),
                integrity_alerts=user.notification_preferences.get("integrity_alerts", True),
                system_updates=user.notification_preferences.get("system_updates", True),
            )
        return NotificationSettings()

    def update_notification_settings(
        self, db: Session, user: User, settings_data: NotificationSettings
    ) -> NotificationSettings:
        """Persists updated user notification preferences."""
        prefs = settings_data.model_dump()
        user.notification_preferences = prefs
        db.commit()
        db.refresh(user)
        return self.get_notification_settings(user)


user_service = UserService()
