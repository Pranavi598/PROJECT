# filemeta/metadata_manager.py
from typing import Dict, Any, List, Optional
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from datetime import datetime
from sqlalchemy import func, or_, String

from .models import File, Tag
from .utils import infer_metadata, parse_tag_value

def add_file_metadata(db: Session, filepath: str, custom_tags: Dict[str, Any], owner_id: int) -> File:
    """
    Adds a new metadata record for a file, associating it with a specific owner.

    Args:
        db (Session): SQLAlchemy database session.
        filepath (str): Absolute path to the file on the server.
        custom_tags (Dict[str, Any]): Dictionary of custom tags (key-value pairs).
        owner_id (int): The ID of the user who owns this file metadata record.

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
    # 'owner' and 'created_by' now use the provided owner_id
    file_record = File(
        filename=os.path.basename(filepath),
        filepath=filepath,
        owner=str(owner_id), # Store owner ID as a string in the owner column
        created_by=str(owner_id), # Assign created_by to the owner ID
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
        # More specific error message for duplicate filepath if it's the unique constraint
        if "UNIQUE constraint failed" in str(e) or "duplicate key value violates unique constraint" in str(e):
            # If the file already exists, grab its ID for a clearer error message
            existing_file_after_rollback = db.query(File).filter(File.filepath == filepath).first()
            existing_id_msg = f" (ID: {existing_file_after_rollback.id})" if existing_file_after_rollback else ""
            raise ValueError(f"Metadata for file '{filepath}' already exists{existing_id_msg}. Use 'update' to modify.")
        else:
            raise Exception(f"Database integrity error: {e}. Check database constraints.") # More specific general integrity error
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while adding file metadata: {e}") # Clarified message

def get_file_by_id(db: Session, file_id: int) -> Optional[File]:
    """
    Retrieves a specific File record by its ID.
    Returns None if not found, instead of raising an exception,
    allowing the API layer to handle 404 responses.

    Args:
        db (Session): SQLAlchemy database session.
        file_id (int): The ID of the file record.

    Returns:
        Optional[File]: The File object if found, otherwise None.
    """
    return db.query(File).filter(File.id == file_id).first()

def get_all_files_for_listing(db: Session) -> List[File]:
    """
    Retrieves all File records and their associated Tag records.
    Used when no ownership filtering is applied (e.g., for admin users).

    Args:
        db (Session): SQLAlchemy database session.

    Returns:
        List[File]: A list of File objects.
    """
    return db.query(File).all()

def search_files_by_criteria(db: Session, keywords: List[str], owner_id: Optional[int] = None) -> List[File]:
    """
    Searches for files based on keywords across various metadata fields,
    optionally filtering by owner.

    Args:
        db (Session): SQLAlchemy database session.
        keywords (List[str]): A list of keywords to search for.
        owner_id (Optional[int]): If provided, search will be restricted to files
                                   owned by this user ID.

    Returns:
        List[File]: A list of File objects matching the search criteria.
    """
    query = db.query(File)

    if keywords:
        search_conditions = []
        for keyword in keywords:
            search_pattern = f"%{keyword.lower()}%" # Case-insensitive search pattern

            # Search in File table fields
            search_conditions.append(func.lower(File.filename).like(search_pattern))
            search_conditions.append(func.lower(File.filepath).like(search_pattern))
            search_conditions.append(func.lower(File.owner).like(search_pattern))

            # Search within inferred_tags (JSONB)
            search_conditions.append(func.lower(File.inferred_tags.cast(String)).like(search_pattern))

            # Search in associated Tags table (key and value)
            search_conditions.append(
                File.tags.any(
                    or_(
                        func.lower(Tag.key).like(search_pattern),
                        func.lower(Tag.value).like(search_pattern)
                    )
                )
            )
        query = query.filter(or_(*search_conditions))

    # Apply owner filter if owner_id is provided
    if owner_id is not None:
        query = query.filter(File.owner == str(owner_id))

    # Use .distinct() to avoid returning the same File multiple times if multiple tags match
    return query.distinct().all()

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
        raise NoResultFound(f"No metadata found for file ID: {file_id}") # API layer will catch this

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
        raise Exception(f"An unexpected error occurred while updating file tags for ID {file_id}: {e}")

def delete_file_metadata(db: Session, file_id: int) -> bool:
    """
    Deletes a file metadata record and its associated custom tags from the database.
    Returns True on successful deletion, False if the file record was not found.

    Args:
        db (Session): SQLAlchemy database session.
        file_id (int): The ID of the file metadata record to delete.

    Returns:
        bool: True if the record was successfully deleted, False if it was not found.

    Raises:
        Exception: For other database or internal errors.
    """
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        return False # Indicate that no record was found for deletion

    try:
        # Due to 'cascade="all, delete-orphan"' in File.tags relationship
        # in models.py, deleting the File will automatically delete its associated Tags.
        db.delete(file_record)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while deleting metadata for file ID {file_id}: {e}")