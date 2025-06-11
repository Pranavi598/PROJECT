# filemeta/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from .models import Base, User # Import Base and User
# REMOVE THIS LINE: from .api.auth import get_password_hash # This caused the circular import

# Database connection URL - CONSISTENT WITH PREVIOUS SETUP
DATABASE_URL = "postgresql://filemeta_user:your_strong_password@localhost/filemeta_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Creates all defined tables in the database."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created/checked.")


# --- User Management Functions ---
def create_user(db: Session, username: str, hashed_password: str, role: str = "user") -> User:
    """
    Creates a new user in the database.
    hashed_password is expected to be ALREADY HASHED by the caller.

    Args:
        db (Session): SQLAlchemy database session.
        username (str): The username for the new user.
        hashed_password (str): The HASHED password for the new user.
        role (str): The role of the user (e.g., "user", "admin").

    Returns:
        User: The newly created User object.

    Raises:
        ValueError: If a user with the given username already exists or other issues.
    """
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise ValueError(f"User with username '{username}' already exists.")

    new_user = User(username=username, hashed_password=hashed_password, role=role)
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Could not create user due to integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while creating user: {e}")

def get_user_by_username(db: Session, username: str) -> User | None:
    """Retrieves a user by their username."""
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Retrieves a user by their ID."""
    return db.query(User).filter(User.id == user_id).first()