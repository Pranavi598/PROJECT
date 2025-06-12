# main.py
import os
from papilv_filemeta.database import init_db, get_db
from papilv_filemeta.metadata_manager import add_file_metadata, list_files, get_file_metadata, search_files, update_file_tags, delete_file_metadata
from sqlalchemy.exc import IntegrityError, NoResultFound

def run_project_example():
    print("--- Initializing Database ---")
    init_db() # Call this to create your database tables

    # Get a database session
    with get_db() as db:
        print("\n--- Adding Example File Metadata ---")
        # IMPORTANT: Replace '/path/to/your/test_file.txt' with an actual path on your server
        # For demonstration, let's create a dummy file if it doesn't exist
        test_filepath = "test_document.txt"
        if not os.path.exists(test_filepath):
            with open(test_filepath, "w") as f:
                f.write("This is a test file for metadata.")
            print(f"Created dummy file: {test_filepath}")

        try:
            # Add metadata for the test file
            file_record = add_file_metadata(
                db,
                test_filepath,
                {"project": "demo", "status": "testing"}
            )
            print(f"Added metadata for '{file_record.filename}' (ID: {file_record.id})")

            # Retrieve and print its details
            retrieved_file = get_file_metadata(db, file_record.id)
            print(f"Retrieved: ID={retrieved_file.id}, Path='{retrieved_file.filepath}', CustomTags={retrieved_file.tags[0].key}:{retrieved_file.tags[0].value}")

        except FileNotFoundError as e:
            print(f"Error: {e}")
        except ValueError as e:
            print(f"Warning: {e}") # File might already exist in DB
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


        print("\n--- Listing All Files in Database ---")
        files = list_files(db)
        if files:
            for f in files:
                print(f"ID: {f.id}, Name: {f.filename}, Path: {f.filepath}, Owner: {f.owner}")
                for tag in f.tags:
                    print(f"  Tag: {tag.key}={tag.value} ({tag.value_type})")
        else:
            print("No files found in the database.")

if __name__ == "__main__":
    run_project_example()
