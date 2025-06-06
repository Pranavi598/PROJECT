# filemeta/metadata_manager.py
from typing import Dict, Any, List
import os
import json # For handling JSONB in Python
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from datetime import datetime

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