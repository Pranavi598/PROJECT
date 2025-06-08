# filemeta/metadata_manager.py

from typing import Dict, Any, List
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from datetime import datetime
from sqlalchemy import func, or_ ,String # Add func and or_ for search queries

from .models import File, Tag
from .utils import infer_metadata, parse_tag_value
from .database import get_db # To get a session

def add_file_metadata(db: Session, filepath: str, custom_tags: Dict[str, Any]) -> File:
    """
    Adds a new metadata record for a file.

    Args:
        db (Session): SQLAlchemy database session.
        filepath (str): Absolute path to the file on the server.
        custom_tags (Dict[str, Any]): Dictionary of custom tags (key-value pairs).

    Returns:
        File: The newly created File object.

    Raises:
        FileNotFoundError: If the provided filepath does not exist.
        ValueError: If a file with the same filepath already exists in the database.
        Exception: For other database or internal errors.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found at: {filepath}")

    # Check if a file with this filepath already exists
    existing_file = db.query(File).filter(File.filepath == filepath).first()
    if existing_file:
        raise ValueError(f"Metadata for file '{filepath}' already exists (ID: {existing_file.id}). Use 'update' to modify.")

    # Infer automatic metadata
    inferred_data = infer_metadata(filepath)

    # Create File record
    file_record = File(
        filename=os.path.basename(filepath),
        filepath=filepath,
        owner=inferred_data.get('os_owner'), # Get from inferred_data
        created_by="system", # Or from a user context if implemented later
        inferred_tags=json.dumps(inferred_data) # Store inferred data as JSON string
    )
    db.add(file_record)
    db.flush() # Flush to get the file_record.id before committing

    # Add custom tags
    for key, value in custom_tags.items():
        # parse_tag_value handles value type detection and conversion
        typed_value, value_type = parse_tag_value(str(value)) # Ensure value is string for parsing
        tag_record = Tag(
            file_id=file_record.id,
            key=key,
            value=str(typed_value), # Store converted value as string
            value_type=value_type
        )
        db.add(tag_record)

    try:
        db.commit()
        db.refresh(file_record) # Refresh to get latest state including relationships if needed
        return file_record
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to add file metadata: {e}")

def get_file_metadata(db: Session, file_id: int) -> File:
    """
    Retrieves a specific File record and its associated Tag records.

    Args:
        db (Session): SQLAlchemy database session.
        file_id (int): The ID of the file record.

    Returns:
        File: The File object with associated tags.

    Raises:
        NoResultFound: If no file metadata record exists for the given ID.
    """
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise NoResultFound(f"No metadata found for file ID: {file_id}")
    return file_record

def list_files(db: Session) -> List[File]:
    """
    Retrieves all File records and their associated Tag records.

    Args:
        db (Session): SQLAlchemy database session.

    Returns:
        List[File]: A list of File objects.
    """
    return db.query(File).all()
# filemeta/metadata_manager.py (add this function)

# ... existing functions ...

def search_files(db: Session, keywords: List[str]) -> List[File]:
    """
    Searches for files based on keywords across various metadata fields.

    Args:
        db (Session): SQLAlchemy database session.
        keywords (List[str]): A list of keywords to search for.

    Returns:
        List[File]: A list of File objects matching the search criteria.
    """
    if not keywords:
        return []

    search_conditions = []
    for keyword in keywords:
        search_pattern = f"%{keyword.lower()}%" # Case-insensitive search pattern

        # Search in File table fields
        search_conditions.append(func.lower(File.filename).like(search_pattern))
        search_conditions.append(func.lower(File.filepath).like(search_pattern))
        search_conditions.append(func.lower(File.owner).like(search_pattern))

        # Search within inferred_tags (JSONB)
        # This converts JSONB to text and searches within it.
        # Note: For very large JSONB or complex searches, consider PostgreSQL's FTS.
        search_conditions.append(func.lower(File.inferred_tags.cast(String)).like(search_pattern))

        # Search in associated Tags table (key and value)
        # This joins with Tags and checks both key and value
        search_conditions.append(
            File.tags.any(
                or_(
                    func.lower(Tag.key).like(search_pattern),
                    func.lower(Tag.value).like(search_pattern)
                )
            )
        )

    # Combine all conditions with OR logic
    # Use .distinct() to avoid returning the same File multiple times if multiple tags match
    return db.query(File).filter(or_(*search_conditions)).distinct().all()
# filemeta/metadata_manager.py (add this function)

# ... existing functions (including search_files) ...

def update_file_tags(db: Session, file_id: int, new_tags: Dict[str, Any], overwrite: bool = False) -> File:
    """
    Updates or adds custom tags for a specific file.

    Args:
        db (Session): SQLAlchemy database session.
        file_id (int): The ID of the file metadata record to update.
        new_tags (Dict[str, Any]): A dictionary of new or updated custom tags.
        overwrite (bool): If True, all existing custom tags for the file will be deleted
                          before adding the new tags. If False, new tags are added,
                          and existing tags with matching keys are updated/replaced.

    Returns:
        File: The updated File object.

    Raises:
        NoResultFound: If no file metadata record exists for the given ID.
        Exception: For other database or internal errors.
    """
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise NoResultFound(f"No metadata found for file ID: {file_id}")

    try:
        if overwrite:
            # Delete all existing custom tags for this file
            db.query(Tag).filter(Tag.file_id == file_id).delete()
            db.flush() # Ensure deletions are processed before adding new ones
        else:
            # For each new tag, check if a tag with that key already exists.
            # If so, delete the old one.
            existing_tag_keys = {tag.key for tag in file_record.tags}
            for new_tag_key in new_tags.keys():
                if new_tag_key in existing_tag_keys:
                    db.query(Tag).filter(Tag.file_id == file_id, Tag.key == new_tag_key).delete()
                    db.flush() # Flush to ensure old tag is removed before potentially adding new with same key

        # Add/re-add the new custom tags
        for key, value in new_tags.items():
            typed_value, value_type = parse_tag_value(str(value)) # Ensure value is string for parsing
            tag_record = Tag(
                file_id=file_record.id,
                key=key,
                value=str(typed_value),
                value_type=value_type
            )
            db.add(tag_record)

        # Update the file's updated_at timestamp (handled by onupdate=datetime.now in model)
        # A simple attribute modification will trigger the onupdate listener
        file_record.updated_at = datetime.now() # Explicitly set to trigger update if no other attributes change

        db.commit()
        db.refresh(file_record) # Refresh to load updated tags
        return file_record
    except NoResultFound: # Re-raise if file_id is somehow lost during transaction (unlikely)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to update file tags for ID {file_id}: {e}")
