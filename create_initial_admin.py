# create_initial_admin.py
import os
from dotenv import load_dotenv
from filemeta.database import get_db, create_user, get_user_by_username
from filemeta.api.auth import get_password_hash # Import from the new location

load_dotenv() # Load environment variables

if __name__ == "__main__":
    with get_db() as db:
        admin_username = os.getenv("INITIAL_ADMIN_USERNAME", "adminuser")
        admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "adminpass") # CHANGE THIS IN PRODUCTION

        existing_admin = get_user_by_username(db, admin_username)
        if not existing_admin:
            hashed_password = get_password_hash(admin_password)
            try:
                create_user(db, admin_username, hashed_password, "admin")
                print(f"Initial admin user '{admin_username}' created successfully.")
            except ValueError as e:
                print(f"Error creating admin user: {e}")
        else:
            print(f"Admin user '{admin_username}' already exists. Skipping creation.")
