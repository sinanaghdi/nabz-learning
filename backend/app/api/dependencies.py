from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required or token is invalid.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized from None

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.isdigit():
        raise unauthorized

    user = db.get(User, int(subject))
    if user is None:
        raise unauthorized
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )
    return user


def assert_user_has_role(user: User, *allowed_roles: UserRole) -> User:
    """Enforce role checks without trusting role values sent by the client."""
    permitted = {role.value for role in allowed_roles}
    if user.role not in permitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
    return user


def require_roles(*allowed_roles: UserRole):
    """Create a FastAPI dependency that limits a route to the supplied roles."""

    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        return assert_user_has_role(current_user, *allowed_roles)

    return role_dependency
