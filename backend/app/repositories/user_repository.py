import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User, UserRole


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Fetches a user entity by primary key UUID."""
        statement = select(User).where(User.id == user_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Fetches a user entity by normalized email address."""
        statement = select(User).where(User.email == email.lower().strip())
        return db.scalar(statement)

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.STUDENT,
        college_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        year_of_study: Optional[int] = None,
        section_id: Optional[uuid.UUID] = None,
    ) -> User:
        """Persists a new user entity to PostgreSQL."""
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            college_id=college_id,
            department_id=department_id,
            year_of_study=year_of_study,
            section_id=section_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


user_repository = UserRepository()
