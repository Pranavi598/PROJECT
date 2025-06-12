# filemeta/metadata_manager.py - (Only the corrected function is shown for clarity)

from typing import Dict, Any, List
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from datetime import datetime
from sqlalchemy import func, or_, String

from .models import File, Tag
from .utils import infer_metadata, parse_tag_value
from .database import engine, Base, get_db

# --- init_db function (as previously discussed, ensure it's present) ---
def init_db():
    """Initializes the database schema by creating all necessary tables."""
    Base.metadata.create_all(engine)
    print("Database schema created or updated.")

# --- add_file_metadata (no changes needed) ---
def add_file_metadata(db: Session, filepath: str, custom_tags: Dict[str, Any]) -> File:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found at: {filepath}")

    existing_file = db.query(File).filter(File.filepath == filepath).first()
    if existing_file:
        raise ValueError(f"Metadata for file '{filepath}' already exists (ID: {existing_file.id}). Use 'update' to modify.")

    inferred_data = infer_metadata(filepath)

    file_record = File(
        filename=os.path.basename(filepath),
        filepath=filepath,
        owner=inferred_data.get('os_owner'),
        created_by="system",
        inferred_tags=json.dumps(inferred_data)
    )
    db.add(file_record)
    db.flush()

    for key, value in custom_tags.items():
        typed_value, value_type = parse_tag_value(str(value))
        tag_record = Tag(
            file_id=file_record.id,
            key=key,
            value=str(typed_value),
            value_type=value_type
        )
        db.add(tag_record)

    try:
        db.commit()
        db.refresh(file_record)
        return file_record
    except IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed" in str(e) or "duplicate key value violates unique constraint" in str(e):
            existing_file_on_error = db.query(File).filter(File.filepath == filepath).first()
            existing_id_msg = f"(ID: {existing_file_on_error.id})" if existing_file_on_error else ""
            raise ValueError(f"Metadata for file '{filepath}' already exists {existing_id_msg}. Use 'update' to modify.")
        else:
            raise Exception(f"Database integrity error: {e}. Check database constraints.")
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while adding file metadata: {e}")

# --- get_file_metadata (no changes needed) ---
def get_file_metadata(db: Session, file_id: int) -> File:
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise NoResultFound(f"No metadata found for file ID: {file_id}")
    return file_record

# --- list_files (no changes needed) ---
def list_files(db: Session) -> List[File]:
    return db.query(File).all()

# --- search_files (no changes needed) ---
def search_files(db: Session, keywords: List[str]) -> List[File]:
    if not keywords:
        return []

    search_conditions = []
    for keyword in keywords:
        search_pattern = f"%{keyword.lower()}%"

        search_conditions.append(func.lower(File.filename).like(search_pattern))
        search_conditions.append(func.lower(File.filepath).like(search_pattern))
        search_conditions.append(func.lower(File.owner).like(search_pattern))
        search_conditions.append(func.lower(File.created_by).like(search_pattern))

        search_conditions.append(func.lower(File.inferred_tags.cast(String)).like(search_pattern))

        search_conditions.append(
            File.tags.any(
                or_(
                    func.lower(Tag.key).like(search_pattern),
                    func.lower(Tag.value).like(search_pattern)
                )
            )
        )

    return db.query(File).filter(or_(*search_conditions)).distinct().all()

# --- CORRECTED: update_file_tags function ---
def update_file_tags(
    db: Session,
    file_id: int,
    tags_to_add_modify: Dict[str, Any] = None,
    tags_to_remove: List[str] = None,
    new_filepath: str = None,
    overwrite_existing: bool = False
) -> File:
    """
    Updates metadata (tags and/or filepath) for a specific file.

    Args:
        db (Session): SQLAlchemy database session.
        file_id (int): The ID of the file metadata record to update.
        tags_to_add_modify (Dict[str, Any], optional): Dictionary of tags to add or update (key: value).
                                                       Defaults to None.
        tags_to_remove (List[str], optional): List of tag keys to remove. Defaults to None.
        new_filepath (str, optional): New file path to update. Defaults to None.
        overwrite_existing (bool): If True, all existing custom tags for the file will be deleted
                                   before adding the `tags_to_add_modify`.

    Returns:
        File: The updated File object.

    Raises:
        NoResultFound: If no file metadata record exists for the given ID.
        ValueError: If the new_filepath does not exist on the filesystem.
        Exception: For other database or internal errors.
    """
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise NoResultFound(f"No metadata found for file ID: {file_id}")

    try:
        # 1. Handle File Path Update
        if new_filepath:
            if not os.path.exists(new_filepath):
                raise ValueError(f"New file path '{new_filepath}' does not exist on the filesystem. Cannot update path.")
            file_record.filepath = new_filepath
            file_record.filename = os.path.basename(new_filepath) # Update filename if path changes

        # 2. Handle Tag Removals/Overwrites
        if overwrite_existing:
            # If overwrite is true, delete ALL existing tags
            db.query(Tag).filter(Tag.file_id == file_id).delete(synchronize_session=False)
            db.flush() # Ensure deletions are processed before adding new ones
        else:
            # If not overwriting, handle specific tag removals
            if tags_to_remove:
                db.query(Tag).filter(
                    Tag.file_id == file_id,
                    Tag.key.in_(tags_to_remove)
                ).delete(synchronize_session=False)
                db.flush() # Flush to ensure these are removed before potential re-add/update

        # 3. Handle Tags to Add/Modify
        # THIS BLOCK IS NOW OUTSIDE THE 'if overwrite_existing / else' structure.
        # It runs AFTER any deletions (either full overwrite or specific removals).
        if tags_to_add_modify:
            for key, value in tags_to_add_modify.items():
                existing_tag = db.query(Tag).filter(Tag.file_id == file_id, Tag.key == key).first()
                typed_value, value_type = parse_tag_value(str(value)) # Always parse value for type

                if existing_tag:
                    # Modify existing tag's value and type
                    existing_tag.value = str(typed_value)
                    existing_tag.value_type = value_type
                else:
                    # Add new tag
                    tag_record = Tag(
                        file_id=file_record.id,
                        key=key,
                        value=str(typed_value),
                        value_type=value_type
                    )
                    db.add(tag_record)

        # 4. Update the file's last_modified_at timestamp
        file_record.last_modified_at = datetime.now()

        db.commit()
        db.refresh(file_record) # Refresh to load updated tags and file data
        return file_record
    except NoResultFound:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while updating file metadata for ID {file_id}: {e}")

# --- delete_file_metadata (no changes needed) ---
def delete_file_metadata(db: Session, file_id: int):
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise NoResultFound(f"No metadata found for file ID: {file_id}")

    try:
        db.delete(file_record)
        db.commit()
    except NoResultFound:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while deleting metadata for file ID {file_id}: {e}")