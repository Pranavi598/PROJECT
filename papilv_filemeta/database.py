# #     # filemeta/database.py

# import os
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker, Session, declarative_base
# from sqlalchemy.exc import OperationalError, IntegrityError
# # from contextlib import contextmanager
# from typing import Optional

# # This is where 'Base' is defined ONCE for all your SQLAlchemy models.
# # It should ONLY be defined here.
# Base = declarative_base()

# # Retrieve DATABASE_URL from environment variable.
# # It's crucial this is set before running your app.
# DATABASE_URL = os.getenv("DATABASE_URL")

# # Raise an error if DATABASE_URL is not set, as it's essential for connection.
# if not DATABASE_URL:
#     raise ValueError("DATABASE_URL environment variable is not set. Please set it before running the application.")

# # Initialize engine and SessionLocal as None. They will be created on first access.
# engine = None
# SessionLocal = None

# def get_engine():
#     """
#     Ensures a single SQLAlchemy engine instance is created and returned globally.
#     This function handles the lazy initialization of the engine and the sessionmaker.
#     """
#     global engine, SessionLocal
#     if engine is None:
#         try:
#             # Attempt to create the engine. This is where connection issues might first appear.
#             engine = create_engine(DATABASE_URL)
#             # Test the connection immediately to catch OperationalError early
#             with engine.connect() as connection:
#                 connection.scalar(text("SELECT 1"))
#             # If connection is successful, set up the SessionLocal factory
#             SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#             print("Database engine and session factory initialized successfully.") # Added confirmation
#         except OperationalError as e:
#             # If connection fails, reset engine/SessionLocal and re-raise the error
#             engine = None
#             SessionLocal = None
#             print(f"Database connection failed: {e}")
#             print("Please ensure your PostgreSQL server is running and accessible, and DATABASE_URL is correct.")
#             raise # Re-raise to stop startup if DB isn't available
#         except Exception as e:
#             # Catch any other unexpected errors during engine creation
#             engine = None
#             SessionLocal = None
#             print(f"An unexpected error occurred during database engine creation: {e}")
#             raise # Re-raise the exception

#     return engine


# def get_db():
#     """
#     Provides a SQLAlchemy session for dependency injection in FastAPI endpoints.
#     It ensures a session is created and properly closed after use.
#     """
#     # Ensure the engine and SessionLocal are set up before creating a session
#     get_engine()
#     db = SessionLocal()
#     try:
#         yield db # Yield the session to the FastAPI endpoint
#     finally:
#         db.close() # Ensure the session is closed after the request is processed

# def init_db():
#     """
#     Initializes the database schema by creating all tables defined in your models.
#     This function should be called once on application startup.
#     It relies on your models (e.g., File, Tag, User) being imported elsewhere in your app
#     (like in api.py) so that Base.metadata knows about them.
#     """
#     print("Attempting to connect to database and create tables...")
#     try:
#         current_engine = get_engine() # Get the initialized engine
#         # Import models here to ensure they are registered with Base.metadata
#         # This explicit import ensures Base.metadata knows about all your models
#         from papilv_filemeta.models import User, File, Tag # Assuming this is the correct path to your models

#         Base.metadata.create_all(bind=current_engine) # Create tables based on Base.metadata
#         print("Database tables created successfully or already exist.")
#     except OperationalError as e:
#         print(f"Failed to create tables. Check database permissions or schema definitions: {e}")
#         raise
#     except Exception as e:
#         print(f"An unexpected error occurred during database initialization (create_all): {e}")
#         raise

# def close_db_engine():
#     """
#     Explicitly closes the database engine connection pool.
#     Useful for testing or clean application shutdown.
#     """
#     global engine, SessionLocal
#     if engine:
#         engine.dispose() # Dispose of all connections in the pool
#         engine = None
#         SessionLocal = None
#         print("Database engine connections closed.")

# # --- User Helper Functions ---
# # Import the User model here, after Base is defined, so it's available for these functions.
# from papilv_filemeta.models import User # Corrected absolute import path for User model

# def create_user(db: Session, username: str, hashed_password: str, role: str = "user") -> User:
#     """
#     Creates a new user in the database.
#     Raises ValueError if a user with the given username already exists.
#     """
#     existing_user = db.query(User).filter(User.username == username).first()
#     if existing_user:
#         raise ValueError(f"User with username '{username}' already exists.")
    
#     db_user = User(username=username, hashed_password=hashed_password, role=role)
#     try:
#         db.add(db_user)
#         db.commit()
#         db.refresh(db_user)
#         return db_user
#     except IntegrityError as e:
#         db.rollback()
#         # This handles cases where a unique constraint might be violated (e.g., username unique)
#         raise ValueError(f"Database integrity error during user creation: {e}")
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"Failed to create user due to an unexpected error: {e}")


# def get_user_by_username(db: Session, username: str) -> Optional[User]:
#     """
#     Retrieves a user from the database by their username.
#     """
#     print(f"DEBUG: Inside get_user_by_username. Type of 'db' is: {type(db)}") # ADD THIS LINE
#     return db.query(User).filter(User.username == username).first()
# # ...

# def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
#     """
#     Retrieves a user from the database by their ID.
#     """
#     return db.query(User).filter(User.id == user_id).first()

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager

# REMOVE THIS LINE: from sqlalchemy.ext.declarative import declarative_base # <--- DELETE THIS LINE

# IMPORT Base from models.py (which is where it's truly defined)
from .models import Base # <--- ADD THIS LINE

# Database URL from environment variable or default
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://filemeta_user:your_strong_password@34.131.63.35:5432/filemeta_db")
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://filemeta_user:your_strong_password@10.190.0.3:5432/filemeta_db")
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://filemeta_user:your_strong_password@localhost:5432/filemeta_db")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://filemeta_user:your_strong_password@localhost/filemeta_db")

# Global engine and SessionLocal variables, initialized to None
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
            # Attempt to create engine. This might raise OperationalError.
            engine = create_engine(DATABASE_URL)
            # Optional: Test connection immediately. This will raise OperationalError if fails.
            with engine.connect() as connection:
                connection.scalar(text("SELECT 1"))
            # If engine creation succeeds and test connection works, set up SessionLocal
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        except OperationalError:
            # Clean up engine if test connection fails, so it can be retried cleanly.
            engine = None
            SessionLocal = None
            raise # Re-raise the OperationalError
            
    return engine

@contextmanager
def get_db():
    """
    Dependency injection utility for database sessions.
    Handles session creation and closing.
    """
    # Ensure engine is created before trying to create a session
    get_engine() 
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database by creating all necessary tables.
    This function will rely on get_engine() to establish connection,
    and any OperationalError from get_engine() or create_all will propagate.
    """
    # Get the engine, which might raise OperationalError if connection fails
    current_engine = get_engine()
    print("DEBUG: Calling Base.metadata.create_all...", file=sys.stderr) # Keep this debug line
    Base.metadata.create_all(bind=current_engine)
    print("DEBUG: Base.metadata.create_all completed.", file=sys.stderr) # Keep this debug line
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