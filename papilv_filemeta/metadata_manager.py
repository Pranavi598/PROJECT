# # metadata_manager.py

# from typing import Dict, Any, List, Optional
# import os
# import json
# from sqlalchemy.orm import Session, joinedload
# from sqlalchemy.exc import IntegrityError, NoResultFound
# from datetime import datetime
# from sqlalchemy import func, or_, String, Integer, cast # Import Integer for casting, func for lower() etc.

# from .models import File, Tag, User # Import User model to reference its ID
# from .utils import infer_metadata, parse_tag_value

# # Important: This file (metadata_manager.py) should NOT import
# # 'engine', 'Base', or 'get_db' from '.database'.
# # Its functions receive a 'Session' object directly via FastAPI's Depends (or CLI context).

# def add_file_metadata(
#     db: Session,
#     filepath: str,
#     custom_tags: Dict[str, Any],
#     owner_id: Optional[int] = None, # New: Accept owner_id
#     created_by: Optional[str] = None # New: Accept created_by username
# ) -> File:
#     """
#     Adds new file metadata and associated custom tags to the database.
#     Associates the file with the provided owner_id and created_by user.
#     """
#     if not os.path.exists(filepath):
#         raise FileNotFoundError(f"File not found at: {filepath}")

#     # Check for existing file by filepath *before* creating the record
#     existing_file = db.query(File).filter(File.filepath == filepath).first()
#     if existing_file:
#         raise ValueError(f"Metadata for file '{filepath}' already exists (ID: {existing_file.id}). Use 'update' to modify.")

#     # Validate owner_id if provided and not null (if owner column is NOT NULL)
#     if owner_id is not None:
#         user_exists = db.query(User).filter(User.id == owner_id).first()
#         if not user_exists:
#             raise ValueError(f"User with ID {owner_id} does not exist. Cannot assign file owner.")
    
#     # If owner is required by DB (nullable=False), then owner_id cannot be None
#     # Add a check here if owner cannot be null in your File model:
#     # if owner_id is None and File.owner.nullable is False: # This check directly on model might not work at runtime easily
#     #     raise ValueError("File owner is required but no owner_id was provided.")

#     inferred_data = infer_metadata(filepath)

#     file_record = File(
#         filename=os.path.basename(filepath),
#         filepath=filepath,
#         owner=owner_id, # Assign owner_id directly
#         created_by=created_by if created_by else "system", # Use provided created_by or default
#         created_at=datetime.now(),
#         updated_at=datetime.now(),
#         inferred_tags=inferred_data # JSONB handles dicts directly
#     )
#     db.add(file_record)
#     db.flush() # Flush to get the file_record.id before adding tags

#     # Add custom tags
#     for key, value in custom_tags.items():
#         # parse_tag_value should return a string for 'value' and its type
#         typed_value_str, value_type = parse_tag_value(str(value)) 

#         tag_record = Tag(
#             file_id=file_record.id,
#             key=key,
#             value=typed_value_str, # Ensure value is stored as string in DB
#             value_type=value_type
#         )
#         db.add(tag_record)

#     try:
#         db.commit()
#         # Eager load the tags directly before returning.
#         # file_record is still attached after commit, but refreshing ensures relations are loaded.
#         db.refresh(file_record) # Refresh the file_record to load relationship data
#         # Now, file_record.tags should be populated, no need for separate query unless detached.
#         # If you were to detach the object then re-query with joinedload, that would be needed.
#         # For object still in session after commit, refresh often suffices.
#         return file_record
#     except IntegrityError as e:
#         db.rollback()
#         error_msg = str(e.orig) # Get original error message for more detail
        
#         if "duplicate key value violates unique constraint" in error_msg.lower():
#             if "_file_key_uc" in error_msg: # Unique constraint on (file_id, key) for Tag
#                 raise ValueError("Duplicate custom tag key for this file.")
#             elif "file_filepath_key" in error_msg or "unique_filepath" in error_msg: # Assuming your File model has this unique constraint name
#                 existing_file_on_error = db.query(File).filter(File.filepath == filepath).first()
#                 existing_id_msg = f"(ID: {existing_file_on_error.id})" if existing_file_on_error else ""
#                 raise ValueError(f"Metadata for file '{filepath}' already exists {existing_id_msg}. Use 'update' to modify.")
        
#         if "null value in column \"owner\" violates not-null constraint" in error_msg.lower() and owner_id is None:
#             raise ValueError("File owner is a required field. Please ensure 'owner_id' is provided.")
        
#         raise Exception(f"Database integrity error: {error_msg}")
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"An unexpected error occurred while adding file metadata: {e}")

# def get_file_metadata(db: Session, file_id: int) -> File:
#     """
#     Retrieves file metadata by its ID, eager loading tags.
#     """
#     # Use .first() after .options(joinedload(File.tags))
#     file_record = db.query(File).options(joinedload(File.tags)).filter(File.id == file_id).first()
#     if not file_record:
#         raise NoResultFound(f"No metadata found for file ID: {file_id}")
#     return file_record

# def list_files(db: Session, owner_id: Optional[int] = None) -> List[File]:
#     """
#     Lists all file metadata records in the database, eager loading tags.
#     Additionally, eager loads the owner relationship for efficient access to owner details.
#     Optionally filters by owner_id.
#     """
#     query = db.query(File).options(joinedload(File.tags), joinedload(File.owner_rel)) # Eager load owner_rel too
#     if owner_id is not None:
#         query = query.filter(File.owner == owner_id) # Filter by owner if provided
#     return query.all()

# def search_files(db: Session, keywords: List[str], owner_id: Optional[int] = None) -> List[File]:
#     """
#     Searches for files based on keywords across various fields, eager loading tags and owner.
#     Optionally filters by owner_id.
#     """
#     query = db.query(File).options(joinedload(File.tags), joinedload(File.owner_rel)) # Eager load tags and owner

#     if keywords: # Only apply keyword search conditions if keywords are provided
#         search_conditions = []
#         for keyword in keywords:
#             search_pattern = f"%{keyword.lower()}%"

#             search_conditions.append(func.lower(File.filename).like(search_pattern))
#             search_conditions.append(func.lower(File.filepath).like(search_pattern))
#             search_conditions.append(func.lower(File.created_by).like(search_pattern))

#             # Search within inferred_tags (JSONB) - Casting to String for LIKE operator
#             # This will search values within the JSONB.
#             search_conditions.append(func.lower(cast(File.inferred_tags, String)).like(search_pattern))

#             # Search within custom tags (key and value)
#             search_conditions.append(
#                 File.tags.any(
#                     or_(
#                         func.lower(Tag.key).like(search_pattern),
#                         func.lower(Tag.value).like(search_pattern)
#                     )
#                 )
#             )
#         query = query.filter(or_(*search_conditions))
        
#     # Apply owner_id filter if provided
#     if owner_id is not None:
#         query = query.filter(File.owner == owner_id)

#     # Use distinct to avoid duplicate File records if a file matches multiple tag search conditions
#     return query.distinct().all()


# def update_file_tags(
#     db: Session,
#     file_id: int,
#     tags_to_add_modify: Optional[Dict[str, Any]] = None,
#     tags_to_remove: Optional[List[str]] = None,
#     new_filepath: Optional[str] = None,
#     overwrite_existing: bool = False
# ) -> File:
#     """
#     Updates metadata (tags and/or filepath) for a specific file.
#     """
#     # Eager load tags here too, as they might be needed for modification or removal logic
#     file_record = db.query(File).options(joinedload(File.tags)).filter(File.id == file_id).first()
#     if not file_record:
#         raise NoResultFound(f"No metadata found for file ID: {file_id}")

#     try:
#         # 1. Handle File Path Update
#         if new_filepath:
#             if not os.path.exists(new_filepath):
#                 raise ValueError(f"New file path '{new_filepath}' does not exist on the filesystem. Cannot update path.")
            
#             # Check for existing file with the new_filepath to prevent unique constraint violation
#             existing_file_at_new_path = db.query(File).filter(File.filepath == new_filepath, File.id != file_id).first()
#             if existing_file_at_new_path:
#                 raise ValueError(f"File metadata for '{new_filepath}' already exists (ID: {existing_file_at_new_path.id}). Cannot update path due to conflict.")
            
#             file_record.filepath = new_filepath
#             file_record.filename = os.path.basename(new_filepath) # Update filename if path changes

#         # 2. Handle Tag Removals/Overwrites
#         if overwrite_existing:
#             # If overwrite is true, delete ALL existing custom tags for this file
#             # This is more efficient than iterating through file_record.tags and calling delete on each.
#             db.query(Tag).filter(Tag.file_id == file_id).delete(synchronize_session=False)
#             db.flush() # Ensure deletions are processed before adding new ones
#         elif tags_to_remove: # Only process specific removals if not overwriting
#             # Ensure tags_to_remove only contains strings (keys)
#             db.query(Tag).filter(
#                 Tag.file_id == file_id,
#                 Tag.key.in_(tags_to_remove)
#             ).delete(synchronize_session=False)
#             db.flush() # Flush to ensure these are removed before potential re-add/update

#         # 3. Handle Tags to Add/Modify
#         if tags_to_add_modify:
#             for key, value in tags_to_add_modify.items():
#                 existing_tag = db.query(Tag).filter(Tag.file_id == file_id, Tag.key == key).first()
#                 typed_value_str, value_type = parse_tag_value(str(value)) # Always parse value for type

#                 if existing_tag:
#                     # Modify existing tag's value and type
#                     existing_tag.value = typed_value_str
#                     existing_tag.value_type = value_type
#                 else:
#                     # Add new tag
#                     tag_record = Tag(
#                         file_id=file_record.id,
#                         key=key,
#                         value=typed_value_str,
#                         value_type=value_type
#                     )
#                     db.add(tag_record)

#         # 4. Update the file's updated_at timestamp
#         file_record.updated_at = datetime.now()

#         db.add(file_record) # Mark the file_record as modified if changes were made
#         db.commit()
#         # Refresh the file_record to load relationship data after commit
#         db.refresh(file_record) 
#         # No need for a separate query with joinedload here as refresh should update current object
#         # but if you need to ensure ALL relationships are loaded, re-query with joinedload.
#         # For simplicity and given the file_record is already in session, refresh is usually enough
#         # assuming 'tags' relationship is correctly mapped in File model.
#         # If your CLI/API still shows stale tags, you might need to re-query with joinedload explicitly.
#         # file_record_with_tags = db.query(File).options(joinedload(File.tags)).filter(File.id == file_record.id).first()
#         return file_record
#     except NoResultFound:
#         db.rollback()
#         raise
#     except IntegrityError as e: # Catch IntegrityError specifically for unique constraint violations
#         db.rollback()
#         error_msg = str(e.orig)
#         if "duplicate key value violates unique constraint" in error_msg.lower() and "_file_key_uc" in error_msg:
#             raise ValueError("Cannot add duplicate tag key for this file.")
#         elif "file_filepath_key" in error_msg or "unique_filepath" in error_msg:
#             raise ValueError(f"Cannot update filepath to '{new_filepath}' as it already exists for another file.")
#         raise Exception(f"Database integrity error during update: {error_msg}")
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"An unexpected error occurred while updating file metadata for ID {file_id}: {e}")

# def delete_file_metadata(db: Session, file_id: int):
#     """
#     Deletes file metadata and its associated tags from the database.
#     Because of 'cascade="all, delete-orphan"' on the 'files' relationship in User model
#     and 'cascade="all, delete-orphan"' on the 'tags' relationship in File model,
#     deleting a File record will automatically delete its associated tags.
#     """
#     file_record = db.query(File).filter(File.id == file_id).first()
#     if not file_record:
#         raise NoResultFound(f"No metadata found for file ID: {file_id}")

#     try:
#         db.delete(file_record)
#         db.commit()
#     except NoResultFound: # This might not be hit if .first() already raised it
#         db.rollback()
#         raise
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"An unexpected error occurred while deleting metadata for file ID {file_id}: {e}")

from typing import Dict, Any, List
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from datetime import datetime
from sqlalchemy import func, or_, String

from .models import File, Tag
from .utils import infer_metadata, parse_tag_value
# >>> CRITICAL CHANGE HERE: Import get_engine, NOT engine directly
from .database import Base, get_db, get_engine 

# --- init_db function ---
def init_db():
    """Initializes the database schema by creating all necessary tables."""
    # >>> CRITICAL CHANGE HERE: Call get_engine() to ensure it's initialized
    current_engine = get_engine() 
    # Use the returned engine object
    Base.metadata.create_all(current_engine)
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