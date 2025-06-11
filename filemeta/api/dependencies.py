# filemeta/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import get_db, get_user_by_id
from ..models import User # Import the User model
from .auth import decode_access_token # Import the decoding function

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current authenticated user.
    Raises HTTPException if the token is invalid or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        
        user = get_user_by_id(db, user_id)
        if user is None:
            raise credentials_exception
        
        return user
    except Exception as e:
        # Re-raise the original HTTPException or wrap other exceptions
        if isinstance(e, HTTPException):
            raise
        raise credentials_exception # Catch-all for any decoding or DB lookup issues

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current authenticated user and check if they are an admin.
    Raises HTTPException if the user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource. Admin privileges required.",
        )
    return current_user