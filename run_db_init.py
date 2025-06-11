# run_db_init.py
import sys
import os

# Add the project root to the sys.path so filemeta can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from filemeta.database import create_tables

if __name__ == "__main__":
    print("Attempting to create database tables...")
    create_tables()
    print("Database table creation process completed.")
