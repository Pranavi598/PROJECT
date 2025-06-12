# # filemeta/metadata_manager.py
# import os
# import hashlib
# import json
# from datetime import datetime
# from typing import Dict, Any, List, Optional

# from sqlalchemy.orm import Session
# from sqlalchemy import or_

# from .models import File, User # Import User for owner validation

# # Helper function to calculate file checksum
# def calculate_checksum(filepath: str, algorithm: str = "sha256") -> str:
#     hasher = hashlib.new(algorithm)
#     with open(filepath, 'rb') as f:
#         while chunk := f.read(8192):
#             hasher.update(chunk)
#     return hasher.hexdigest()

# # Helper function to infer tags (e.g., file extension, common keywords)
# def infer_tags_from_filepath(filepath: str) -> dict:
#     inferred = {}
#     filename = os.path.basename(filepath)
#     name, ext = os.path.splitext(filename)

#     inferred['extension'] = ext.lstrip('.').lower()
#     inferred['filename_base'] = name

#     # Example: Infer 'type' tag
#     if ext.lower() in ['.txt', '.md', '.log']:
#         inferred['type'] = 'document'
#     elif ext.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
#         inferred['type'] = 'image'
#     elif ext.lower() in ['.mp3', '.wav']:
#         inferred['type'] = 'audio'
#     elif ext.lower() in ['.mp4', '.avi']:
#         inferred['type'] = 'video'
#     elif ext.lower() in ['.pdf']:
#         inferred['type'] = 'pdf'
#     elif ext.lower() in ['.doc', '.docx']:
#         inferred['type'] = 'word_document'
#     elif ext.lower() in ['.xls', '.xlsx']:
#         inferred['type'] = 'spreadsheet'
#     elif ext.lower() in ['.ppt', '.pptx']:
#         inferred['type'] = 'presentation'
#     elif ext.lower() in ['.zip', '.tar', '.gz']:
#         inferred['type'] = 'archive'

#     # Add more sophisticated inference logic here (e.g., regex for dates, project names)
#     if 'report' in name.lower():
#         inferred['category'] = 'report'
#     if 'backup' in name.lower():
#         inferred['category'] = 'backup'
#     if 'project' in name.lower():
#         inferred['category'] = 'project'

#     return inferred

# def add_file_metadata(db: Session, filepath: str, custom_tags: Dict[str, str], owner_id: int) -> File:
#     """Adds metadata for a file, checking for existence and updating if file content changed."""
#     filepath = os.path.abspath(filepath)
#     if not os.path.exists(filepath):
#         raise FileNotFoundError(f"File not found at: {filepath}")
#     if not os.path.isfile(filepath):
#         raise ValueError(f"Path is not a regular file: {filepath}")

#     # Check if owner_id exists
#     owner = db.query(User).filter(User.id == owner_id).first()
#     if not owner:
#         raise ValueError(f"Owner with ID {owner_id} does not exist.")

#     filename = os.path.basename(filepath)
#     checksum = calculate_checksum(filepath)
#     size_bytes = os.path.getsize(filepath)
#     last_modified = datetime.fromtimestamp(os.path.getmtime(filepath))

#     # Check if file already exists based on filepath (and is NOT deleted)
#     existing_file = db.query(File).filter(
#         File.filepath == filepath,
#         File.is_deleted == False # IMPORTANT: Only consider non-deleted files
#     ).first()

#     inferred_tags = infer_tags_from_filepath(filepath)

#     if existing_file:
#         # If content changed, update existing record
#         if (existing_file.checksum != checksum or
#             existing_file.size_bytes != size_bytes or
#             existing_file.last_modified != last_modified or
#             existing_file.get_inferred_tags() != inferred_tags):
#             existing_file.filename = filename
#             existing_file.checksum = checksum
#             existing_file.size_bytes = size_bytes
#             existing_file.last_modified = last_modified
#             existing_file.set_inferred_tags(inferred_tags)
#             existing_file.set_custom_tags({**existing_file.get_custom_tags(), **custom_tags}) # Merge custom tags
#             existing_file.is_deleted = False # Ensure it's marked as not deleted if it was recovered
#             existing_file.deleted_at = None
#             db.commit()
#             db.refresh(existing_file)
#             return existing_file
#         else:
#             # If nothing changed, just update custom tags (if any new ones)
#             if custom_tags:
#                 existing_file.set_custom_tags({**existing_file.get_custom_tags(), **custom_tags})
#                 db.commit()
#                 db.refresh(existing_file)
#             return existing_file
#     else:
#         # Create new record if no existing non-deleted file found
#         new_file = File(
#             filename=filename,
#             filepath=filepath,
#             checksum=checksum,
#             size_bytes=size_bytes,
#             last_modified=last_modified,
#             owner_id=owner_id
#         )
#         new_file.set_inferred_tags(inferred_tags)
#         new_file.set_custom_tags(custom_tags)
#         db.add(new_file)
#         db.commit()
#         db.refresh(new_file)
#         return new_file

# def get_file_by_id(db: Session, file_id: int) -> Optional[File]:
#     """Retrieves a file metadata record by ID, only if NOT deleted."""
#     return db.query(File).filter(File.id == file_id, File.is_deleted == False).first()

# def get_all_files_for_listing(db: Session) -> List[File]:
#     """Lists all non-deleted file metadata records."""
#     return db.query(File).filter(File.is_deleted == False).all()

# def search_files_by_criteria(db: Session, keywords: Optional[List[str]] = None, owner_id: Optional[int] = None) -> List[File]:
#     """Searches non-deleted file metadata records by keywords and optional owner."""
#     query = db.query(File).filter(File.is_deleted == False)

#     if owner_id:
#         query = query.filter(File.owner_id == owner_id)

#     if keywords:
#         search_conditions = []
#         for keyword in keywords:
#             search_pattern = f"%{keyword.lower()}%"
#             search_conditions.append(File.filename.ilike(search_pattern))
#             # Search in inferred tags
#             search_conditions.append(File.inferred_tags_json.ilike(search_pattern))
#             # Search in custom tags
#             search_conditions.append(File.custom_tags_json.ilike(search_pattern))
#         query = query.filter(or_(*search_conditions))

#     return query.all()

# def update_file_tags(db: Session, file_id: int, new_tags: Dict[str, str], overwrite_existing: bool) -> File:
#     """Updates custom tags for a non-deleted file."""
#     file_record = db.query(File).filter(File.id == file_id, File.is_deleted == False).first()
#     if not file_record:
#         raise ValueError(f"No non-deleted metadata found for file ID: {file_id}")

#     if overwrite_existing:
#         file_record.set_custom_tags(new_tags)
#     else:
#         current_tags = file_record.get_custom_tags()
#         current_tags.update(new_tags)
#         file_record.set_custom_tags(current_tags)

#     db.commit()
#     db.refresh(file_record)
#     return file_record

# def delete_file_metadata(db: Session, file_id: int) -> bool:
#     """
#     Soft deletes a file metadata record by marking it as deleted and setting a timestamp.
#     Returns True if a record was marked, False otherwise.
#     """
#     file_record = db.query(File).filter(File.id == file_id, File.is_deleted == False).first()
#     if file_record:
#         file_record.is_deleted = True
#         file_record.deleted_at = datetime.utcnow()
#         db.commit()
#         return True
#     return False

# def recover_file_metadata(db: Session, file_id: int) -> Optional[File]:
#     """
#     Recovers a soft-deleted file metadata record by marking it as not deleted.
#     Returns the recovered File object or None if not found/not deleted.
#     """
#     file_record = db.query(File).filter(File.id == file_id, File.is_deleted == True).first()
#     if file_record:
#         file_record.is_deleted = False
#         file_record.deleted_at = None
#         db.commit()
#         db.refresh(file_record)
#         return file_record
#     return None

# def check_and_sync_files(db: Session, root_dir: str, dry_run: bool = True, fix: bool = False, default_owner_id: int = 1) -> Dict[str, Any]:
#     """
#     Compares file system state with database records, reports discrepancies, and can fix them.
#     This function will now ignore soft-deleted files in its check.
#     """
#     current_db_files: Dict[str, File] = {f.filepath: f for f in db.query(File).filter(File.is_deleted == False).all()}
#     files_on_system: Dict[str, Dict[str, Any]] = {}

#     missing_files_in_db = []
#     stale_records_in_db = []
#     updated_records = []
#     skipped_invalid_paths = []

#     # Map database filepaths to their IDs for quick lookup for stale records
#     db_filepath_to_id = {f.filepath: f.id for f in db.query(File).all()} # Get all, even deleted, to check for stale paths

#     # 1. Scan filesystem and identify missing/changed files in DB
#     for dirpath, _, filenames in os.walk(root_dir):
#         for filename in filenames:
#             filepath = os.path.abspath(os.path.join(dirpath, filename))
#             if not os.path.isfile(filepath): # Skip non-regular files
#                 skipped_invalid_paths.append(f"Not a regular file: {filepath}")
#                 continue

#             try:
#                 current_checksum = calculate_checksum(filepath)
#                 current_size = os.path.getsize(filepath)
#                 current_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
#             except Exception as e:
#                 skipped_invalid_paths.append(f"Error accessing file '{filepath}': {e}")
#                 continue

#             files_on_system[filepath] = {
#                 "filename": filename,
#                 "checksum": current_checksum,
#                 "size_bytes": current_size,
#                 "last_modified": current_mtime,
#                 "inferred_tags": infer_tags_from_filepath(filepath)
#             }

#             db_record = current_db_files.get(filepath)

#             if db_record is None:
#                 missing_files_in_db.append(filepath)
#                 if fix:
#                     # Check if it was previously soft-deleted
#                     soft_deleted_record = db.query(File).filter(File.filepath == filepath, File.is_deleted == True).first()
#                     if soft_deleted_record:
#                         # Recover the soft-deleted record if the file exists on disk
#                         soft_deleted_record.is_deleted = False
#                         soft_deleted_record.deleted_at = None
#                         soft_deleted_record.filename = filename
#                         soft_deleted_record.checksum = current_checksum
#                         soft_deleted_record.size_bytes = current_size
#                         soft_deleted_record.last_modified = current_mtime
#                         soft_deleted_record.set_inferred_tags(infer_tags_from_filepath(filepath))
#                         db.commit()
#                         updated_records.append((soft_deleted_record.id, filepath + " (recovered)"))
#                     else:
#                         # Add new metadata for genuinely new files
#                         try:
#                             # Verify default_owner_id exists
#                             owner = db.query(User).filter(User.id == default_owner_id).first()
#                             if not owner:
#                                 skipped_invalid_paths.append(f"Cannot add '{filepath}': Default owner ID {default_owner_id} does not exist.")
#                                 continue

#                             new_file_record = File(
#                                 filename=filename,
#                                 filepath=filepath,
#                                 checksum=current_checksum,
#                                 size_bytes=current_size,
#                                 last_modified=current_mtime,
#                                 owner_id=default_owner_id
#                             )
#                             new_file_record.set_inferred_tags(infer_tags_from_filepath(filepath))
#                             db.add(new_file_record)
#                             db.commit()
#                             db.refresh(new_file_record)
#                             updated_records.append((new_file_record.id, filepath + " (added)"))
#                         except Exception as e:
#                             skipped_invalid_paths.append(f"Error adding '{filepath}': {e}")
#             elif (db_record.checksum != current_checksum or
#                   db_record.size_bytes != current_size or
#                   db_record.last_modified != current_mtime or
#                   db_record.get_inferred_tags() != files_on_system[filepath]["inferred_tags"]):
#                 # File content or basic properties changed
#                 updated_records.append((db_record.id, filepath + " (modified)"))
#                 if fix:
#                     db_record.checksum = current_checksum
#                     db_record.size_bytes = current_size
#                     db_record.last_modified = current_mtime
#                     db_record.set_inferred_tags(files_on_system[filepath]["inferred_tags"])
#                     db.commit()

#     # 2. Identify stale records in DB (files in DB but not on system, and NOT already soft-deleted)
#     for db_filepath, db_file_id in db_filepath_to_id.items():
#         if db_filepath not in files_on_system:
#             # Check if it's already soft-deleted
#             db_record = db.query(File).filter(File.id == db_file_id).first()
#             if db_record and not db_record.is_deleted: # Only consider truly stale (non-deleted) records
#                 stale_records_in_db.append((db_file_id, db_filepath))
#                 if fix:
#                     db_record.is_deleted = True # Soft delete
#                     db_record.deleted_at = datetime.utcnow()
#                     db.commit()

#     return {
#         "missing_files_in_db": missing_files_in_db,
#         "stale_records_in_db": stale_records_in_db,
#         "updated_records": updated_records,
#         "skipped_invalid_paths": skipped_invalid_paths,
#     }
# filemeta/metadata_manager.py
# from typing import Dict, Any, List
# import os
# import json
# from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError, NoResultFound
# from datetime import datetime
# from sqlalchemy import func, or_, String,cast,Integer

# from .models import File, Tag
# from .utils import infer_metadata, parse_tag_value
# # >>> CRITICAL CHANGE HERE: Import get_engine, NOT engine directly
# from .database import Base, get_db, get_engine 

# # --- init_db function ---
# def init_db():
#     """Initializes the database schema by creating all necessary tables."""
#     # >>> CRITICAL CHANGE HERE: Call get_engine() to ensure it's initialized
#     current_engine = get_engine() 
#     # Use the returned engine object
#     Base.metadata.create_all(current_engine)
#     print("Database schema created or updated.")

# # --- add_file_metadata (no changes needed) ---
# def add_file_metadata(db: Session, filepath: str, custom_tags: Dict[str, Any]) -> File:
#     if not os.path.exists(filepath):
#         raise FileNotFoundError(f"File not found at: {filepath}")

#     existing_file = db.query(File).filter(File.filepath == filepath).first()
#     if existing_file:
#         raise ValueError(f"Metadata for file '{filepath}' already exists (ID: {existing_file.id}). Use 'update' to modify.")

#     inferred_data = infer_metadata(filepath)

#     file_record = File(
#         filename=os.path.basename(filepath),
#         filepath=filepath,
#         owner=inferred_data.get('os_owner'),
#         created_by="system",
#         inferred_tags=json.dumps(inferred_data)
#     )
#     db.add(file_record)
#     db.flush()

#     for key, value in custom_tags.items():
#         typed_value, value_type = parse_tag_value(str(value))
#         tag_record = Tag(
#             file_id=file_record.id,
#             key=key,
#             value=str(typed_value),
#             value_type=value_type
#         )
#         db.add(tag_record)

#     try:
#         db.commit()
#         db.refresh(file_record)
#         return file_record
#     except IntegrityError as e:
#         db.rollback()
#         if "UNIQUE constraint failed" in str(e) or "duplicate key value violates unique constraint" in str(e):
#             existing_file_on_error = db.query(File).filter(File.filepath == filepath).first()
#             existing_id_msg = f"(ID: {existing_file_on_error.id})" if existing_file_on_error else ""
#             raise ValueError(f"Metadata for file '{filepath}' already exists {existing_id_msg}. Use 'update' to modify.")
#         else:
#             raise Exception(f"Database integrity error: {e}. Check database constraints.")
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"An unexpected error occurred while adding file metadata: {e}")

# # --- get_file_metadata (no changes needed) ---
# def get_file_metadata(db: Session, file_id: int) -> File:
#     file_record = db.query(File).filter(File.id == file_id).first()
#     if not file_record:
#         raise NoResultFound(f"No metadata found for file ID: {file_id}")
#     return file_record

# # --- list_files (no changes needed) ---
# def list_files(db: Session) -> List[File]:
#     return db.query(File).all()

# # --- search_files (no changes needed) ---
# def search_files(db: Session, keywords: List[str]) -> List[File]:
#     if not keywords:
#         return []

#     search_conditions = []
#     for keyword in keywords:
#         search_pattern = f"%{keyword.lower()}%"

#         search_conditions.append(func.lower(File.filename).like(search_pattern))
#         search_conditions.append(func.lower(File.filepath).like(search_pattern))
#         search_conditions.append(func.lower(File.owner).like(search_pattern))
#         search_conditions.append(func.lower(File.created_by).like(search_pattern))

#         search_conditions.append(func.lower(File.inferred_tags.cast(String)).like(search_pattern))

#         search_conditions.append(
#             File.tags.any(
#                 or_(
#                     func.lower(Tag.key).like(search_pattern),
#                     func.lower(Tag.value).like(search_pattern)
#                 )
#             )
#         )

#     return db.query(File).filter(or_(*search_conditions)).distinct().all()

# # --- CORRECTED: update_file_tags function ---
# def update_file_tags(
#     db: Session,
#     file_id: int,
#     tags_to_add_modify: Dict[str, Any] = None,
#     tags_to_remove: List[str] = None,
#     new_filepath: str = None,
#     overwrite_existing: bool = False
# ) -> File:
#     """
#     Updates metadata (tags and/or filepath) for a specific file.

#     Args:
#         db (Session): SQLAlchemy database session.
#         file_id (int): The ID of the file metadata record to update.
#         tags_to_add_modify (Dict[str, Any], optional): Dictionary of tags to add or update (key: value).
#                                                        Defaults to None.
#         tags_to_remove (List[str], optional): List of tag keys to remove. Defaults to None.
#         new_filepath (str, optional): New file path to update. Defaults to None.
#         overwrite_existing (bool): If True, all existing custom tags for the file will be deleted
#                                    before adding the `tags_to_add_modify`.

#     Returns:
#         File: The updated File object.

#     Raises:
#         NoResultFound: If no file metadata record exists for the given ID.
#         ValueError: If the new_filepath does not exist on the filesystem.
#         Exception: For other database or internal errors.
#     """
#     file_record = db.query(File).filter(File.id == file_id).first()
#     if not file_record:
#         raise NoResultFound(f"No metadata found for file ID: {file_id}")

#     try:
#         # 1. Handle File Path Update
#         if new_filepath:
#             if not os.path.exists(new_filepath):
#                 raise ValueError(f"New file path '{new_filepath}' does not exist on the filesystem. Cannot update path.")
#             file_record.filepath = new_filepath
#             file_record.filename = os.path.basename(new_filepath) # Update filename if path changes

#         # 2. Handle Tag Removals/Overwrites
#         if overwrite_existing:
#             # If overwrite is true, delete ALL existing tags
#             db.query(Tag).filter(Tag.file_id == file_id).delete(synchronize_session=False)
#             db.flush() # Ensure deletions are processed before adding new ones
#         else:
#             # If not overwriting, handle specific tag removals
#             if tags_to_remove:
#                 db.query(Tag).filter(
#                     Tag.file_id == file_id,
#                     Tag.key.in_(tags_to_remove)
#                 ).delete(synchronize_session=False)
#                 db.flush() # Flush to ensure these are removed before potential re-add/update

#         # 3. Handle Tags to Add/Modify
#         # THIS BLOCK IS NOW OUTSIDE THE 'if overwrite_existing / else' structure.
#         # It runs AFTER any deletions (either full overwrite or specific removals).
#         if tags_to_add_modify:
#             for key, value in tags_to_add_modify.items():
#                 existing_tag = db.query(Tag).filter(Tag.file_id == file_id, Tag.key == key).first()
#                 typed_value, value_type = parse_tag_value(str(value)) # Always parse value for type

#                 if existing_tag:
#                     # Modify existing tag's value and type
#                     existing_tag.value = str(typed_value)
#                     existing_tag.value_type = value_type
#                 else:
#                     # Add new tag
#                     tag_record = Tag(
#                         file_id=file_record.id,
#                         key=key,
#                         value=str(typed_value),
#                         value_type=value_type
#                     )
#                     db.add(tag_record)

#         # 4. Update the file's last_modified_at timestamp
#         file_record.last_modified_at = datetime.now()

#         db.commit()
#         db.refresh(file_record) # Refresh to load updated tags and file data
#         return file_record
#     except NoResultFound:
#         db.rollback()
#         raise
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"An unexpected error occurred while updating file metadata for ID {file_id}: {e}")
# def search_files_numeric_range(db: Session, min_size_bytes: int = None, max_size_bytes: int = None) -> List[File]:
#     """
#     Search for files based on numeric range conditions, particularly file size.

#     Args:
#         db (Session): SQLAlchemy database session.
#         min_size_bytes (int, optional): Minimum file size in bytes. Defaults to None.
#         max_size_bytes (int, optional): Maximum file size in bytes. Defaults to None.

#     Returns:
#         List[File]: A list of File objects matching the numeric range criteria.
#     """
#     if min_size_bytes is None and max_size_bytes is None:
#         return []

#     query = db.query(File)
#     conditions = []

#     # The 'file_size' is stored within the 'inferred_tags' JSONB column.
#     # We need to cast it to an integer for numeric comparison.
#     # PostgreSQL JSONB operator '->>' extracts as text, so explicit casting is needed.
#     # For SQLite, JSON functions are more limited, but SQLAlchemy usually handles common patterns.
#     # If SQLite doesn't directly support JSONB casting, a simpler JSON TEXT operator might be needed
#     # or you'd need to store file_size as a separate column.
    
#     file_size_col = File.inferred_tags['file_size'].astext.cast(Integer)
#     # Note: On SQLite, inferred_tags is TEXT, so you might need to use json_extract and then cast.
#     # Example for SQLite:
#     # file_size_col = cast(func.json_extract(File.inferred_tags, '$.file_size'), Integer)


#     if min_size_bytes is not None:
#         conditions.append(file_size_col >= min_size_bytes)
    
#     if max_size_bytes is not None:
#         conditions.append(file_size_col <= max_size_bytes)

#     if conditions:
#         query = query.filter(*conditions) # Apply all conditions

#     return query.all()
# # --- delete_file_metadata (no changes needed) ---
# def delete_file_metadata(db: Session, file_id: int):
#     file_record = db.query(File).filter(File.id == file_id).first()
#     if not file_record:
#         raise NoResultFound(f"No metadata found for file ID: {file_id}")

#     try:
#         db.delete(file_record)
#         db.commit()
#     except NoResultFound:
#         db.rollback()
#         raise
#     except Exception as e:
#         db.rollback()
#         raise Exception(f"An unexpected error occurred while deleting metadata for file ID {file_id}: {e}")
# filemeta/metadata_manager.py
# filemeta/metadata_manager.py
from typing import Dict, Any, List,Optional
import os
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import func, or_, String, cast, Integer, text,TIMESTAMP,distinct  # Import 'text' for potential raw SQL if needed for specific DBs
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone, timedelta
from .models import File, Tag
from .utils import infer_metadata, parse_tag_value,parse_date_string
from .database import Base, get_db, get_engine 

# --- init_db function ---
def init_db():
    """Initializes the database schema by creating all necessary tables."""
    current_engine = get_engine() 
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
        # Store inferred_data as a JSON string, wrapped in quotes to match existing data format
        # If your DB column inferred_tags was JSONB, this would just be `inferred_data`
        inferred_tags=json.dumps(inferred_data) 
    )
    db.add(file_record)
    db.flush()

    for key, value in custom_tags.items():
        typed_value, value_type = parse_tag_value(str(value))
        tag_record = Tag(
            file_id=file_record.id,
            key=key,
            value=str(typed_value), # Store as string
            value_type=value_type
        )
        db.add(tag_record)

    try:
        db.commit()
        db.refresh(file_record)
        return file_record
    except IntegrityError as e:
        db.rollback()
        if "duplicate key value violates unique constraint" in str(e) or "UNIQUE constraint failed" in str(e):
            if "filepath" in str(e).lower() : 
                existing_file_on_error = db.query(File).filter(File.filepath == filepath).first()
                existing_id_msg = f"(ID: {existing_file_on_error.id})" if existing_file_on_error else ""
                raise ValueError(f"Metadata for file '{filepath}' already exists {existing_id_msg}. Use 'update' to modify or delete existing record.")
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

        # This will search within the string representation of the JSONB/TEXT
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

# --- CORRECTED: update_file_tags function (no changes needed) ---
def update_file_tags(
    db: Session,
    file_id: int,
    tags_to_add_modify: Dict[str, Any] = None,
    tags_to_remove: List[str] = None,
    new_filepath: str = None,
    overwrite_existing: bool = False
) -> File:
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise NoResultFound(f"No metadata found for file ID: {file_id}")

    try:
        if new_filepath:
            if not os.path.exists(new_filepath):
                raise ValueError(f"New file path '{new_filepath}' does not exist on the filesystem. Cannot update path.")
            file_record.filepath = new_filepath
            file_record.filename = os.path.basename(new_filepath)

        if overwrite_existing:
            db.query(Tag).filter(Tag.file_id == file_id).delete(synchronize_session=False)
            db.flush()
        else:
            if tags_to_remove:
                db.query(Tag).filter(
                    Tag.file_id == file_id,
                    Tag.key.in_(tags_to_remove)
                ).delete(synchronize_session=False)
                db.flush()

        if tags_to_add_modify:
            for key, value in tags_to_add_modify.items():
                existing_tag = db.query(Tag).filter(Tag.file_id == file_id, Tag.key == key).first()
                typed_value, value_type = parse_tag_value(str(value))

                if existing_tag:
                    existing_tag.value = str(typed_value)
                    existing_tag.value_type = value_type
                else:
                    tag_record = Tag(
                        file_id=file_record.id,
                        key=key,
                        value=str(typed_value),
                        value_type=value_type
                    )
                    db.add(tag_record)

        file_record.last_modified_at = datetime.now()

        db.commit()
        db.refresh(file_record)
        return file_record
    except NoResultFound:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while updating file metadata for ID {file_id}: {e}")

# def search_files_numeric_range(db: Session, min_size_bytes: int = None, max_size_bytes: int = None) -> List[File]:
#     """
#     Search for files based on numeric range conditions, particularly file size.
#     """
#     if min_size_bytes is None and max_size_bytes is None:
#         return []

#     query = db.query(File)
#     conditions = []

    # --- CRITICAL FIX START ---
    # Cast the entire inferred_tags column to JSONB first, then extract and cast to Integer.
    # This is necessary if inferred_tags is defined as Text/String in models.py
    # but contains JSON strings.
    # If inferred_tags is ALREADY a proper JSONB type in the DB, this might not be needed,
    # # but it's harmless and can act as a safeguard.
    
    # # Check if the dialect is PostgreSQL. If not, this might cause issues on other DBs.
    # # Given your DATABASE_URL is PostgreSQL, this should be safe.
    # file_size_col = cast(File.inferred_tags, JSONB)['file_size'].astext.cast(Integer)
    # # --- CRITICAL FIX END ---

    # if min_size_bytes is not None:
    #     conditions.append(file_size_col >= min_size_bytes)
    
    # if max_size_bytes is not None:
    #     conditions.append(file_size_col <= max_size_bytes)

    # if conditions:
    #     query = query.filter(*conditions)

    # return query.all()
def _get_json_date_column(field_name: str):
    """
    Helper to get a SQLAlchemy column expression for date fields
    within inferred_tags, handling the double-quoted string storage.
    Casts to TIMESTAMP for comparison.
    """
    # Cast to String to ensure string functions work correctly
    raw_string_col = cast(File.inferred_tags, String)
    
    # Replace escaped double quotes (\") with actual double quotes (")
    # This specifically targets the format that json.dumps() creates inside the string.
    # We also trim any possible outer quotes.
    cleaned_and_trimmed_string = func.trim(func.replace(raw_string_col, '\"', '"'), '"')
    
    # Use COALESCE and NULLIF to provide a default empty JSON object string if
    # the cleaned and trimmed string is empty or NULL.
    json_text_expr = func.coalesce(
        func.nullif(cleaned_and_trimmed_string, ''), # If cleaned/trimmed is '', set to NULL
        text("'{}'") # Then coalesce NULL to '{}'
    )
    
    # Now cast the (hopefully valid) JSON string to JSONB, extract, and cast to TIMESTAMP
    return cast(json_text_expr, JSONB).op('->>')(field_name).cast(TIMESTAMP)

# --- Comprehensive Search Function ---
def search_files_by_criteria(
    db: Session,
    keywords: Optional[List[str]] = None,
    min_size_bytes: Optional[int] = None,
    max_size_bytes: Optional[int] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    modified_after: Optional[datetime] = None,
    modified_before: Optional[datetime] = None,
    accessed_after: Optional[datetime] = None,
    accessed_before: Optional[datetime] = None
) -> List[File]:
    """
    Searches for files based on a combination of criteria:
    keywords, file size range, and creation/modification/access date ranges.
    """
    query = db.query(File)

    # 1. Apply Keyword Filters
    if keywords:
        keyword_conditions = []
        for keyword in keywords:
            search_pattern = f"%{keyword.lower()}%"
            keyword_conditions.append(func.lower(File.filename).like(search_pattern))
            keyword_conditions.append(func.lower(File.filepath).like(search_pattern))
            keyword_conditions.append(func.lower(File.owner).like(search_pattern))
            keyword_conditions.append(func.lower(File.created_by).like(search_pattern))
            # Search within the raw JSON string for inferred_tags
           # Explicitly cast to String before applying lower() for keyword search
            keyword_conditions.append(func.lower(cast(File.inferred_tags, String)).like(search_pattern))
            keyword_conditions.append(
                File.tags.any(
                    or_(
                        func.lower(Tag.key).like(search_pattern),
                        func.lower(Tag.value).like(search_pattern)
                    )
                )
            )
        query = query.filter(or_(*keyword_conditions))
    
    # 2. Apply Numeric (Size) Filters
    if min_size_bytes is not None or max_size_bytes is not None:
        size_conditions = []
        # Cast to String first for string functions
        raw_string_col = cast(File.inferred_tags, String)
        # Replace escaped double quotes (\") with actual double quotes (")
        cleaned_and_trimmed_string = func.trim(func.replace(raw_string_col, '\"', '"'), '"')

        # Coalesce to an empty JSON object string if trimmed content is empty or NULL
        json_text_expr = func.coalesce(
            func.nullif(cleaned_and_trimmed_string, ''), 
            text("'{}'")
        )
        file_size_col = cast(json_text_expr, JSONB).op('->>')('file_size').cast(Integer)
        
        if min_size_bytes is not None:
            size_conditions.append(file_size_col >= min_size_bytes)
        if max_size_bytes is not None:
            size_conditions.append(file_size_col <= max_size_bytes)
        
        if size_conditions:
            query = query.filter(*size_conditions)

    # 3. Apply Date Filters
    date_conditions = []

    # File.created_at and File.updated_at are already DateTime columns
    if created_after:
        date_conditions.append(File.created_at >= created_after)
    if created_before:
        # Add one day to search before to include the full day
        date_conditions.append(File.created_at <= created_before + timedelta(days=1, microseconds=-1)) 
    
    if modified_after:
        date_conditions.append(File.updated_at >= modified_after)
    if modified_before:
        # Add one day to search before to include the full day
        date_conditions.append(File.updated_at <= modified_before + timedelta(days=1, microseconds=-1))

    # Dates from inferred_tags (which are strings) need special handling
    # last_accessed_at, created_at_fs, last_modified_at (within inferred_tags JSON)
    
    # For `last_accessed_at` from inferred_tags
    inferred_accessed_at_col = _get_json_date_column('last_accessed_at')
    if accessed_after:
        date_conditions.append(inferred_accessed_at_col >= accessed_after)
    if accessed_before:
        date_conditions.append(inferred_accessed_at_col <= accessed_before + timedelta(days=1, microseconds=-1))

    if date_conditions:
        query = query.filter(*date_conditions)

    return query.distinct().all()

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
def rename_file_entry(db: Session, file_id: int, new_name: str) -> File:
    """
    Renames a file on the disk and updates its corresponding entry in the database.
    Args:
        db (Session): SQLAlchemy database session.
        file_id (int): The ID of the file metadata record to rename.
        new_name (str): The new filename (e.g., "report_final.docx").
    Returns:
        File: The updated File object.
    Raises:
        NoResultFound: If no file metadata record exists for the given ID.
        FileNotFoundError: If the original file does not exist on disk.
        PermissionError: If there are insufficient permissions to rename the file.
        OSError: For other operating system related errors during rename.
        Exception: For database or unexpected errors.
    """
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise NoResultFound(f"No metadata found for file ID: {file_id}")
    old_filepath = file_record.filepath
    # Construct new full path
    directory = os.path.dirname(old_filepath)
    new_filepath = os.path.join(directory, new_name)
    if not os.path.exists(old_filepath):
        raise FileNotFoundError(f"Original file not found on disk at: {old_filepath}")
    if os.path.exists(new_filepath):
        # Decide on behavior here: overwrite, raise error, or prompt user?
        # For simplicity, raising an error if new_filepath exists.
        raise FileExistsError(f"A file with the new name '{new_filepath}' already exists at the destination.")
    try:
        # Step 1: Rename the file on the disk
        os.rename(old_filepath, new_filepath)
        # Step 2: Update the database record
        file_record.filepath = new_filepath
        file_record.filename = new_name # Update filename to the new name
        file_record.last_modified_at = datetime.now() # Record this change
        db.commit()
        db.refresh(file_record)
        return file_record
    except NoResultFound: # Should be caught by the initial check, but defensive
        db.rollback()
        raise
    except FileExistsError:
        db.rollback()
        raise # Re-raise if we explicitly caught it above
    except (PermissionError, OSError) as e:
        db.rollback()
        # If disk rename failed, ensure DB isn't updated.
        # It's important that DB change only commits if disk change succeeds.
        raise e # Re-raise to be caught by CLI
    except Exception as e:
        db.rollback()
        raise Exception(f"An unexpected error occurred while renaming file ID {file_id}: {e}")
def list_and_search_tags(
    db: Session,
    unique: bool = False,
    sort_by: str = None,
    sort_order: str = 'asc',
    limit: int = None,
    offset: int = 0,
    keywords: List[str] = None
) -> List[Any]: # Can return List[Tag] or List[str] or List[Tuple[str, str]]
    """
    Lists and searches tags with options for uniqueness, sorting, pagination, and keyword filtering.

    Args:
        db (Session): SQLAlchemy database session.
        unique (bool): If True, returns unique tag keys or unique key-value pairs.
        sort_by (str, optional): 'key' or 'value' to sort results.
        sort_order (str): 'asc' or 'desc'.
        limit (int, optional): Maximum number of results to return.
        offset (int): Number of results to skip.
        keywords (List[str], optional): Keywords to search for in tag keys or values.

    Returns:
        List[Tag] or List[str] or List[Tuple[str, str]]: List of Tag objects, unique keys,
                                                       or unique key-value tuples.
    """
    query = db.query(Tag)

    # Apply keyword search filter first
    if keywords:
        search_conditions = []
        for keyword in keywords:
            search_pattern = f"%{keyword.lower()}%"
            search_conditions.append(func.lower(Tag.key).like(search_pattern))
            search_conditions.append(func.lower(Tag.value).like(search_pattern))
        query = query.filter(or_(*search_conditions))

    # Apply uniqueness logic
    if unique:
        # If unique, we only want the distinct key/value pairs or just keys
        # For simplicity, returning distinct key-value tuples here.
        # If you only want unique keys, you'd change the query select.
        query = query.with_entities(distinct(Tag.key), Tag.value)
        # If you only want unique keys: query = query.with_entities(distinct(Tag.key))

    # Apply sorting
    if sort_by:
        if sort_by == 'key':
            if sort_order == 'asc':
                query = query.order_by(Tag.key.asc())
            else:
                query = query.order_by(Tag.key.desc())
        elif sort_by == 'value':
            if sort_order == 'asc':
                query = query.order_by(Tag.value.asc())
            else:
                query = query.order_by(Tag.value.desc())

    # Apply pagination
    if limit is not None:
        query = query.limit(limit)
    if offset > 0:
        query = query.offset(offset)

    return query.all()
def validate_file_metadata(
    db: Session,
    check_all: bool = False,
    criteria: Optional[Dict[str, Any]] = None,
    tag_key: Optional[str] = None,
    tag_value: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Validates file metadata records against file system existence and tag presence.

    Args:
        db (Session): SQLAlchemy database session.
        check_all (bool): If True, validates all records.
        criteria (Dict[str, Any], optional): Dictionary of File column criteria
                                            (e.g., {'id': 1, 'filename': 'report.pdf'}).
        tag_key (str, optional): Key of a tag to check for existence.
        tag_value (str, optional): Specific value for the tag_key to check.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each describing a validation result
                              (e.g., {'id': ..., 'filepath': ..., 'disk_exists': ..., 'tag_status': ...}).
    """
    query = db.query(File)

    # Apply initial filtering based on criteria if not checking all records
    if not check_all and criteria:
        if 'id' in criteria:
            query = query.filter(File.id == criteria['id'])
        if 'filename' in criteria:
            query = query.filter(File.filename == criteria['filename'])
        if 'filepath' in criteria:
            query = query.filter(File.filepath == criteria['filepath'])

    files_to_validate = query.all()
    validation_results = []

    for file_record in files_to_validate:
        result = {
            'id': file_record.id,
            'filename': file_record.filename,
            'filepath': file_record.filepath,
            'disk_exists': os.path.exists(file_record.filepath),
            'tag_status': None # Initialize tag status
        }

        # Perform tag existence check if tag_key is provided
        if tag_key:
            tag_found = False
            for tag in file_record.tags:
                if tag.key == tag_key:
                    # Check for specific value if provided, otherwise just key existence
                    if tag_value is None or tag.value == tag_value:
                        tag_found = True
                        break
            
            # Formulate the tag status message
            if tag_found:
                result['tag_status'] = f"Required tag '{tag_key}'"
                if tag_value:
                    result['tag_status'] += f"='{tag_value}'"
                result['tag_status'] += " found."
            else:
                result['tag_status'] = f"Required tag '{tag_key}'"
                if tag_value:
                    result['tag_status'] += f"='{tag_value}'"
                result['tag_status'] += " NOT found."
        
        # Always add to results. The CLI will decide how to display.
        validation_results.append(result)

    return validation_results
