from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, UserResponse, LoginResponse
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(register_data: UserRegister, db: Session = Depends(get_db)):
    """Registers a new student or examiner account."""
    user = auth_service.register_user(db, register_data)
    return user


@router.post("/login", response_model=LoginResponse)
def login(login_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticates credentials, sets HttpOnly access_token cookie, and returns safe user profile."""
    token, user = auth_service.login_user(db, login_data)
    
    # Set secure HttpOnly cookie for browser clients
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    return LoginResponse(
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
def logout(response: Response):
    """Clears the authentication HttpOnly cookie."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/"
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile information for the authenticated user."""
    return current_user
