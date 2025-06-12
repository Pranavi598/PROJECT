# auth.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import os # Import os for SECRET_KEY

from schemas import TokenData, User # Import Pydantic User model

# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-that-should-be-random-and-long")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for getting token from request headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- In-memory "User Database" (for demonstration purposes only) ---
FAKE_USERS_DB: Dict[str, User] = {}


# --- Password Hashing Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- User Authentication and Retrieval ---
def get_user(db_users: Dict[str, User], username: str) -> Optional[User]:
    """Retrieves a user from the in-memory database by username."""
    return db_users.get(username)

def authenticate_user(db_users: Dict[str, User], username: str, password: str) -> Optional[User]:
    """Authenticates a user against the in-memory database."""
    user = get_user(db_users, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# --- JWT Token Functions ---
def create_access_token(data: Dict[str, Union[str, int]], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    `data` should contain payload, e.g., {"sub": username, "role": "admin"}
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """
    Verifies a JWT token and returns the decoded payload.
    Raises HTTPException if token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_role: str = payload.get("role")
        if username is None or user_role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=user_role)
    except JWTError:
        raise credentials_exception
    return token_data

# --- FastAPI Dependencies for Authentication and Authorization ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the currently authenticated user based on the JWT token.
    """
    token_data = verify_token(token)
    user = get_user(FAKE_USERS_DB, token_data.username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure the current user has 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation forbidden: Admin privileges required"
        )
    return current_user
