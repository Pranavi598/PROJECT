# filemeta/api/auth.py

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Corrected absolute imports for database functions and models
from papilv_filemeta.database import get_db, get_user_by_username, get_user_by_id
from papilv_filemeta.models import User # Corrected import path

# --- Configuration ---
# IMPORTANT: For production, load these from environment variables!
# Example: SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-jwt-key-replace-me-with-a-very-long-random-string")
SECRET_KEY = "your-super-secret-jwt-key-replace-me-with-a-very-long-random-string" # <--- IMPORTANT: CHANGE THIS TO A STRONG, RANDOM STRING!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # <--- DEFINE HERE (in minutes)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for dependency injection
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# --- Password Hashing Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- User Authentication and Retrieval (ADD THIS BLOCK IF MISSING) ---
def authenticate_user(db: Session, username: str, password: str):
    """Authenticates a user against the database."""
    user = get_user_by_username(db, username=username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# --- JWT Token Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decodes a JWT access token and returns its payload."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Ensure 'sub' (subject, typically username), 'user_id', and 'user_role' are present
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        user_role: str = payload.get("user_role")

        if username is None or user_id is None or user_role is None:
            raise credentials_exception

        return {"username": username, "user_id": user_id, "user_role": user_role}
    except JWTError:
        raise credentials_exception

# --- Dependency to get the current user from the token ---
async def get_current_user(
    db: Session = Depends(get_db), # Use the get_db dependency to get a session
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency function to get the current authenticated user from the JWT token.
    Raises HTTPException if the token is invalid or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token) # Reuse the decode_access_token function
        username = payload.get("username")
        user_id = payload.get("user_id") # We get user_id from payload as well
        user_role = payload.get("user_role")

        if username is None or user_id is None:
            raise credentials_exception
    except HTTPException: # Catch the HTTPException raised by decode_access_token
        raise # Re-raise it
    except JWTError: # This might also catch if decode_access_token had other issues, but HTTPException is usually covered
        raise credentials_exception

    # Use the session from get_db to query the user
    user = get_user_by_id(db, user_id=user_id) # Prefer user_id for lookup if available in token

    if user is None:
        raise credentials_exception

    # You might want to do a final check if user.username matches username from token
    # or if user.role matches user_role from token, for stricter validation
    if user.username != username or user.role != user_role:
        raise credentials_exception # Token data does not match DB user

    return user

# --- Dependency for current active user (can add checks for active status) ---
async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Dependency function to ensure the current user is active.
    Add more checks here if your User model has an 'is_active' or similar field.
    """
    # Example: if not current_user.is_active:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


# --- Optional: Role-based authorization dependency ---
def require_role(required_role: str):
    """
    Dependency factory to check if the current user has a specific role.
    Usage: Depends(require_role("admin"))
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized. Requires '{required_role}' role."
            )
        return current_user # Return the user if authorized
    return role_checker

# --- Optional: Permission-based authorization dependency ---
def require_permission(required_permission: str):
    """
    Dependency factory to check if the current user has a specific permission.
    (Assumes User model has a 'permissions' attribute, e.g., a list of strings)
    Usage: Depends(require_permission("file:write"))
    """
    def permission_checker(current_user: User = Depends(get_current_user)):
        # Assuming user.permissions is a list of strings or similar iterable
        # You'll need to ensure your User model has a 'permissions' attribute
        # and that it's populated correctly (e.g., from roles, or directly).
        if not hasattr(current_user, 'permissions') or required_permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized. Requires '{required_permission}' permission."
            )
        return current_user
    return permission_checker