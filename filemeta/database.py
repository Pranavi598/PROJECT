# filemeta/database.py
from sqlalchemy import create_engine, text # Add 'text' here
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager
import os
import sys
import click

# Import Base from models
from .models import Base

# Database URL from environment variable or default to SQLite for dev
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://filemeta_user:your_strong_password@localhost/filemeta_db") # CHANGE THIS for your PostgreSQL setup or use SQLite

# For SQLite during development, uncomment this and comment the PostgreSQL line:
# DATABASE_URL = "sqlite:///./filemeta.db"

engine = None # Initialize engine to None

def get_engine():
    """Ensures a single engine instance is created and returned."""
    global engine
    if engine is None:
        try:
            engine = create_engine(DATABASE_URL)
            # Test connection (optional, but good for early error detection)
            with engine.connect() as connection:
                connection.scalar(text("SELECT 1")) # Use text() for raw SQL query
            click.echo(f"Database engine created successfully for: {DATABASE_URL}")
        except OperationalError as e:
            click.echo(f"Error connecting to the database: {e}", err=True)
            click.echo("Please ensure PostgreSQL is running and credentials are correct, or check DATABASE_URL.", err=True)
            sys.exit(1) # Exit if cannot connect
        except Exception as e:
            click.echo(f"An unexpected error occurred during database engine creation: {e}", err=True)
            sys.exit(1)
    return engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

@contextmanager
def get_db():
    """Dependency injection utility for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Creates all tables defined in models.py."""
    click.echo("Initializing database...")
    try:
        Base.metadata.create_all(bind=get_engine())
        click.echo("Database initialized successfully.")
    except OperationalError as e:
        click.echo(f"Error initializing database: {e}", err=True)
        click.echo("Please ensure the database server is running and accessible.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred during database initialization: {e}", err=True)
        sys.exit(1)

# Function to explicitly close engine connection (useful for testing/cleanup)
def close_db_engine():
    global engine
    if engine:
        engine.dispose()
        engine = None
        click.echo("Database engine connection disposed.")