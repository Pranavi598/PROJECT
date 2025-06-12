# dependencies.py
from typing import Generator
from sqlalchemy.orm import Session
from filemeta.database import get_db

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a SQLAlchemy database session.
    """
    with get_db() as db:
        yield db
