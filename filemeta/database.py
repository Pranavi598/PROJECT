# # filemeta/database.py
# from sqlalchemy import create_engine,func, Numeric
# from sqlalchemy.orm import sessionmaker, Session
# from sqlalchemy.exc import IntegrityError
# from contextlib import contextmanager
# from typing import List, Optional, Dict, Any # <--- ADD List, Optional, Dict, Any

# from .models import Base, User # Import Base and User
# # REMOVE THIS LINE: from .api.auth import get_password_hash # This caused the circular import

# # Database connection URL - CONSISTENT WITH PREVIOUS SETUP
# DATABASE_URL = "postgresql://filemeta_user:your_strong_password@localhost/filemeta_db"

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# def get_db():
#     """Dependency to get a database session."""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
# @contextmanager # <--- This one IS a context manager for CLI direct 'with' usage
# def get_cli_db():
#     """Context manager to get a database session for CLI tools."""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
# def create_tables():
#     """Creates all defined tables in the database."""
#     Base.metadata.create_all(bind=engine)
#     print("Database tables created/checked.")


# # --- User Management Functions ---
# def create_user(db: Session, username: str, hashed_password: str, role: str = "user") -> User:
#     """
#     Creates a new user in the database.
#     hashed_password is expected to be ALREADY HASHED by the caller.

#     Args:
#         db (Session): SQLAlchemy database session.
#         username (str): The username for the new user.
#         hashed_password (str): The HASHED password for the new user.
#         role (str): The role of the user (e.g., "user", "admin").

#     Returns:
#         User: The newly created User object.

#     Raises:
#         ValueError: If a user with the given username already exists or other issues.
#     """
#     existing_user = db.query(User).filter(User.username == username).first()
#     if existing_user:
#         raise ValueError(f"User with username '{username}' already exists.")

#     new_user = User(username=username, hashed_password=hashed_password, role=role)
#     try:
#         db.add(new_user)
#         db.commit()
#         db.refresh(new_user)
#         return new_user
#     except IntegrityError as e:
#         db.rollback()
#         raise ValueError(f"Could not create user due to integrity error: {e}")
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"An unexpected error occurred while creating user: {e}")

# def get_user_by_username(db: Session, username: str) -> User | None:
#     """Retrieves a user by their username."""
#     return db.query(User).filter(User.username == username).first()

# def get_user_by_id(db: Session, user_id: int) -> User | None:
#     """Retrieves a user by their ID."""
#     return db.query(User).filter(User.id == user_id).first()

# def close_db_engine():
#     """Closes the database engine."""
#     global _engine, _SessionLocal
#     if _engine:
#         _engine.dispose()
#         _engine = None
#     _SessionLocal = None
#     print("Database engine closed.")
# filemeta/database.py
# filemeta/database.py
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager

from .models import Base 

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://filemeta_user:your_strong_password@localhost/filemeta_db")

engine = None
SessionLocal = None

def get_engine():
    """
    Ensures a single engine instance is created and returned.
    Raises OperationalError if connection fails, allowing CLI to handle.
    """
    global engine, SessionLocal
    if engine is None:
        try:
            # Set echo=False to suppress SQLAlchemy's INFO-level SQL query logging
            engine = create_engine(DATABASE_URL, echo=False) 
            with engine.connect() as connection:
                connection.scalar(text("SELECT 1"))
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        except OperationalError:
            engine = None
            SessionLocal = None
            raise
            
    return engine

@contextmanager
def get_db():
    get_engine() 
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database by creating all necessary tables.
    """
    current_engine = get_engine()
    print("DEBUG: Calling Base.metadata.create_all...", file=sys.stderr)
    Base.metadata.create_all(bind=current_engine)
    print("DEBUG: Base.metadata.create_all completed.", file=sys.stderr)
    print("Database schema created or updated.")

def close_db_engine():
    """
    Explicitly closes the database engine connection.
    Useful for testing or application shutdown.
    """
    global engine, SessionLocal
    if engine:
            engine.dispose()
            engine = None
            SessionLocal = None
