# create_initial_user.py
import os
import sys
from contextlib import contextmanager # <-- ADD THIS IMPORT

# Add your project root to the path so imports work correctly
# Assuming create_initial_user.py is in the project root:
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ensure these imports are correct relative to your project structure
from papilv_filemeta.database import init_db, get_db, create_user
from papilv_filemeta.api.auth import get_password_hash
from sqlalchemy.exc import IntegrityError

# Define a context manager wrapper for get_db specifically for this script
@contextmanager
def get_db_for_script():
    db_session_generator = get_db() # Call the original generator function from database.py
    db = next(db_session_generator) # Get the yielded session
    try:
        yield db # Yield the session to the 'with' block in this script
    finally:
        # After the 'with' block exits, try to advance the generator
        # to its end, which should trigger the 'finally' block in the
        # original get_db to close the session.
        try:
            next(db_session_generator)
        except StopIteration:
            pass # This is expected when the generator is exhausted
        except Exception as e:
            print(f"Warning: Error during get_db_for_script cleanup: {e}")


def create_initial_admin():
    print("Ensuring database is initialized...")
    try:
        init_db() # This will ensure tables exist and connect to the DB
        print("Database initialization check complete.")
    except Exception as e:
        print(f"Error during database initialization: {e}")
        print("Please ensure your DATABASE_URL is correct and PostgreSQL is running.")
        sys.exit(1) # Exit if DB init fails

    username = "testuser" # Use a distinct username
    password = "testpassword123" # Use a simple, known password for testing
    role = "admin" # Give it admin role for full access

    print(f"Attempting to create user: {username}")
    hashed_password = get_password_hash(password)

    try:
        # Use the new context manager wrapper here
        with get_db_for_script() as db: # <-- IMPORTANT: Use get_db_for_script here
            user = create_user(db, username=username, hashed_password=hashed_password, role=role)
            print(f"Successfully created user '{user.username}' with role '{user.role}'.")
            print(f"You can now log in with username: {username}, password: {password}")
    except ValueError as e:
        print(f"Error creating user: {e}")
        if "already exists" in str(e):
            print(f"User '{username}' already exists. If you want to reset password, do it via SQL directly.")
    except IntegrityError as e:
        print(f"Database integrity error during user creation: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during user creation: {e}")


if __name__ == "__main__":
    create_initial_admin()
