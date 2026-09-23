"""Shared FastAPI dependencies: auth guards."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login", auto_error=False
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exc
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exc
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_oauth2_scheme),
) -> User | None:
    """Like get_current_user, but returns None instead of 401 when anonymous."""
    if not token:
        return None
    token_data = decode_access_token(token)
    if token_data is None:
        return None
    return db.query(User).filter(User.id == token_data.user_id).first()
