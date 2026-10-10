from typing import Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.schemas.auth import UserRegister, UserLogin
from app.repositories.user_repository import user_repository
from app.repositories.academic_repository import academic_repository
from app.core.security import hash_password, verify_password, create_access_token


class AuthService:
    @staticmethod
    def register_user(db: Session, register_data: UserRegister) -> User:
        """Registers a new user (STUDENT only for public registration). Validates academic fields."""
        if register_data.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only student self-registration is allowed."
            )
        
        existing_user = user_repository.get_by_email(db, register_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered."
            )

        # Validate Academic Details
        if register_data.college_id:
            college = academic_repository.get_college_by_id(db, register_data.college_id)
            if not college or not college.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or inactive college selected."
                )

        if register_data.department_id:
            if not register_data.college_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="College must be specified when department is selected."
                )
            dept = academic_repository.get_department_by_id(db, register_data.department_id)
            if not dept or not dept.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or inactive department selected."
                )
            if dept.college_id != register_data.college_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Department does not belong to selected college."
                )

        if register_data.year_of_study is not None:
            if register_data.year_of_study < 1 or register_data.year_of_study > 4:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Year of study must be between 1 and 4."
                )

        if register_data.section_id:
            if not register_data.department_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Department must be specified when section is selected."
                )
            sec = academic_repository.get_section_by_id(db, register_data.section_id)
            if not sec or not sec.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or inactive section selected."
                )
            if sec.department_id != register_data.department_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Section does not belong to selected department."
                )
            if register_data.year_of_study and sec.year_of_study != register_data.year_of_study:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Section does not belong to selected year of study."
                )
        
        hashed_pwd = hash_password(register_data.password)
        
        user = user_repository.create_user(
            db=db,
            email=register_data.email,
            password_hash=hashed_pwd,
            first_name=register_data.first_name,
            last_name=register_data.last_name,
            role=register_data.role,
            college_id=register_data.college_id,
            department_id=register_data.department_id,
            year_of_study=register_data.year_of_study,
            section_id=register_data.section_id,
        )
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        """Authenticates user credentials against stored Argon2 hash."""
        user = user_repository.get_by_email(db, email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def login_user(db: Session, login_data: UserLogin) -> Tuple[str, User]:
        """Logs in user, issues JWT access token, and returns (token, user)."""
        user = AuthService.authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = create_access_token({
            "sub": str(user.id),
            "role": user.role.value
        })
        return token, user


auth_service = AuthService()
