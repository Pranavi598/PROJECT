# filemeta/api/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Corrected absolute imports for database functions, models, and auth functions
from papilv_filemeta.database import get_db, get_user_by_id # Corrected import path
from papilv_filemeta.models import User # Corrected import path
from papilv_filemeta.api.auth import decode_access_token # Corrected import path to auth.py

# OAuth2 scheme for dependency injection
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login") # Changed to /login for consistency

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
        payload = decode_access_token(token) # decode_access_token from auth.py already raises HTTPException for JWTError
        user_id: int = payload.get("user_id")
        
        if user_id is None:
            # This specific check for None user_id from payload might be redundant if decode_access_token ensures it
            # but it's safe to keep.
            raise credentials_exception
            
        user = get_user_by_id(db, user_id)
        if user is None:
            raise credentials_exception
            
        # Optional: Add a check if the username from the token payload matches the user retrieved from DB
        # This adds an extra layer of validation.
        username_from_token = payload.get("username")
        if username_from_token and user.username != username_from_token:
            raise credentials_exception

        # Optional: Add a check if the user_role from the token payload matches the user retrieved from DB
        user_role_from_token = payload.get("user_role")
        if user_role_from_token and user.role != user_role_from_token:
            raise credentials_exception
        
        return user
    except HTTPException:
        # If decode_access_token already raised an HTTPException, re-raise it
        raise
    except Exception as e:
        # Catch-all for any other unexpected errors during DB lookup or token processing
        # This ensures a consistent 401 response for authentication failures.
        print(f"Error in get_current_user: {e}") # Log the actual error for debugging
        raise credentials_exception

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

# You can also define other role-based or permission-based dependencies here
# For example, if you wanted a "manager" role:
# async def get_current_manager_user(current_user: User = Depends(get_current_user)) -> User:
#     if current_user.role not in ["admin", "manager"]:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized. Manager or Admin privileges required.",
#         )
#     return current_user
