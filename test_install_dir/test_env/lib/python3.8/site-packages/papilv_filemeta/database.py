# filemeta/database.py
import os
import sys # Keep sys for potential use, but won't sys.exit from here for OPE
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base # Re-add Base from here
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager

# Base is defined here for declarative models, as it's typically tied to the engine/metadata
Base = declarative_base()

# Database URL from environment variable or default to PostgreSQL for dev
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
        # Attempt to create engine. This might raise OperationalError.
        engine = create_engine(DATABASE_URL)
        # If engine creation succeeds, set up SessionLocal
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Optional: Test connection immediately. This will raise OperationalError if fails.
        # This is commented out by default as `create_all` or first session use will also test.
        # try:
        #     with engine.connect() as connection:
        #         connection.scalar(text("SELECT 1"))
        # except OperationalError:
        #     # Clean up engine if test connection fails, so it can be retried cleanly.
        #     engine = None
        #     SessionLocal = None
        #     raise # Re-raise the OperationalError
            
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
    Base.metadata.create_all(bind=current_engine)

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