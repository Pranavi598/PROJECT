import os
import sys

# IMPORTANT: Explicitly import the models module first.
# This ensures that the File and Tag classes are defined
# and registered with the Base.metadata object.
import filemeta.models # <--- THIS IS CRITICAL

# Now, import init_db and close_db_engine from database.py
# This will use the Base object that now has models registered.
from filemeta.database import init_db, close_db_engine

from sqlalchemy.exc import OperationalError

# Set the DATABASE_URL environment variable for this script's execution
# Ensure this matches your actual user and password
os.environ["DATABASE_URL"] = "postgresql://filemeta_user:your_strong_password@localhost/filemeta_db"
# IMPORTANT: Replace 'your_strong_password' with the real password for filemeta_user

if __name__ == "__main__":
    print("Attempting to initialize database directly...")
    try:
        init_db() # This function internally calls Base.metadata.create_all
        print("Database initialized successfully via direct script.")
    except OperationalError as e:
        print(f"Database connection error during direct initialization: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during direct database initialization: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        close_db_engine() # Ensure the engine is closed