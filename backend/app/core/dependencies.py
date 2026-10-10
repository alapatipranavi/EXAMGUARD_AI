import uuid
from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository

# Optional Bearer scheme for Swagger UI integration
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency extracting & validating JWT from HttpOnly cookie or Bearer header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token: Optional[str] = None
    
    # 1. First check HttpOnly cookie
    if settings.COOKIE_NAME in request.cookies:
        token = request.cookies.get(settings.COOKIE_NAME)
    
    # 2. Fall back to Authorization Bearer header (for Swagger UI / API clients)
    elif bearer and bearer.credentials:
        token = bearer.credentials
        
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = user_repository.get_by_id(db, user_id)
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account."
        )

    return user


def get_current_user_optional(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional user dependency returning User if authenticated, else None."""
    try:
        return get_current_user(request, bearer, db)
    except HTTPException:
        return None


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Factory creating an RBAC authorization dependency checking user role."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{current_user.role.value}' is not authorized."
            )
        return current_user
    return role_checker


# Specific role dependencies
require_student = require_roles(UserRole.STUDENT)
require_examiner = require_roles(UserRole.EXAMINER)
require_admin = require_roles(UserRole.ADMIN)
