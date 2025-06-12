
# # main.py
# import uvicorn
# import os
# from typing import List, Dict, Union, Optional
# from fastapi import FastAPI, Depends, HTTPException, status, Query
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlalchemy.orm import Session
# from sqlalchemy.exc import NoResultFound, OperationalError, IntegrityError
# from datetime import datetime

# # Import your core metadata management functions
# from filemeta.database import get_db, init_db as filemeta_init_db, close_db_engine
# from filemeta.metadata_manager import (
#     add_file_metadata,
#     list_files,
#     get_file_metadata,
#     update_file_tags,
#     delete_file_metadata,
#     search_files_by_criteria # Use the new comprehensive search function
# )
# from filemeta.models import File # Keep this import, even if not directly used for ORM conversion

# # Import Pydantic schemas and authentication/authorization logic
# from schemas import (
#     Token, User, UserCreate, UserResponse,
#     FileAddRequest, FileUpdateRequest, FileResponse,
#     UserBase, SearchQueryParams # Now including new date parameters
# )
# from auth import (
#     authenticate_user, create_access_token, get_password_hash,
#     get_current_user, get_admin_user, FAKE_USERS_DB
# )
# from dependencies import get_db_session
# from filemeta.utils import convert_human_readable_to_bytes, parse_date_string # New import for date parsing

# # Create the FastAPI app
# app = FastAPI(
#     title="File Metadata API",
#     description="A REST API for managing server file metadata with user authentication and roles."
# )

# # --- API Lifecycle Events ---
# @app.on_event("startup")
# async def startup_event():
#     """
#     On startup, initialize the file metadata database and create a default admin user
#     if they don't already exist in our in-memory user store.
#     """
#     print("API starting up...")
#     try:
#         # Initialize the file metadata database (tables)
#         filemeta_init_db()
#         print("File metadata database tables initialized.")
#     except OperationalError as e:
#         print(f"ERROR: Database connection failed at startup: {e}", flush=True)
#     except Exception as e:
#         print(f"ERROR: Unexpected error during file metadata DB init: {e}", flush=True)

#     # Initialize a default admin user if not exists
#     if "admin" not in FAKE_USERS_DB:
#         hashed_password = get_password_hash("adminpass") # Default admin password
#         FAKE_USERS_DB["admin"] = User(
#             id=1, username="admin", hashed_password=hashed_password, role="admin"
#         )
#         print("Default admin user 'admin' created with password 'adminpass'.")

#     # Initialize a default regular user if not exists
#     if "user1" not in FAKE_USERS_DB:
#         hashed_password = get_password_hash("userpass") # Default user password
#         FAKE_USERS_DB["user1"] = User(
#             id=2, username="user1", hashed_password=hashed_password, role="user"
#         )
#         print("Default user 'user1' created with password 'userpass'.")

#     print("API startup complete.")

# @app.on_event("shutdown")
# async def shutdown_event():
#     """
#     On shutdown, close the database engine connection.
#     """
#     print("API shutting down...")
#     close_db_engine()
#     print("Database engine closed.")
#     print("API shutdown complete.")

# # --- Authentication Endpoints ---
# @app.post("/token", response_model=Token)
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     """
#     Endpoint for users to authenticate and get an access token.
#     Requires `username` and `password` in the form data.
#     """
#     user = authenticate_user(FAKE_USERS_DB, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token = create_access_token(data={"sub": user.username, "role": user.role})
#     return {"access_token": access_token, "token_type": "bearer"}

# # --- User Management Endpoints (Admin Only) ---
# @app.get("/users/me", response_model=UserResponse)
# async def read_users_me(current_user: User = Depends(get_current_user)):
#     """
#     Get information about the currently authenticated user.
#     """
#     return UserResponse(id=current_user.id, username=current_user.username, role=current_user.role)

# @app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
# async def create_new_user(user: UserCreate, current_admin_user: User = Depends(get_admin_user)):
#     """
#     Create a new user. Only accessible by admin users.
#     Default role for new users is 'user'.
#     """
#     if user.username in FAKE_USERS_DB:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Username already registered"
#         )
#     user_id = len(FAKE_USERS_DB) + 1 # Simple incrementing ID
#     hashed_password = get_password_hash(user.password)
#     new_user = User(
#         id=user_id, username=user.username, hashed_password=hashed_password, role="user"
#     )
#     FAKE_USERS_DB[user.username] = new_user
#     return UserResponse(id=new_user.id, username=new_user.username, role=new_user.role)

# @app.get("/users/", response_model=List[UserResponse])
# async def list_all_users(current_admin_user: User = Depends(get_admin_user)):
#     """
#     List all registered users. Only accessible by admin users.
#     """
#     return [UserResponse(id=u.id, username=u.username, role=u.role) for u in FAKE_USERS_DB.values()]

# # --- File Metadata Endpoints (Admin & User) ---

# # IMPORTANT: Define the more specific /files/search route BEFORE /files/{file_id}
# @app.get("/files/search", response_model=List[FileResponse])
# async def search_files_api(
#     keywords: Optional[List[str]] = Query(None, description="Keywords to search for in file metadata (filename, path, owner, tags). Can be repeated."),
#     size_gt: Optional[str] = Query(None, description='Search for files larger than the specified size (e.g., "10MB", "1GB").'),
#     size_lt: Optional[str] = Query(None, description='Search for files smaller than the specified size (e.g., "100KB", "1GB").'),
#     size_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description='Search for files within a size range (e.g., "100KB 1MB"). Requires two values.'),
#     # New date/time search parameters
#     created_after: Optional[str] = Query(None, description="Search for files created after this date/time (e.g., '2024-01-01' or '2024-06-11 10:00:00')."),
#     created_before: Optional[str] = Query(None, description="Search for files created before this date/time."),
#     modified_after: Optional[str] = Query(None, description="Search for files modified after this date/time."),
#     modified_before: Optional[str] = Query(None, description="Search for files modified before this date/time."),
#     accessed_after: Optional[str] = Query(None, description="Search for files last accessed after this date/time."),
#     accessed_before: Optional[str] = Query(None, description="Search for files last accessed before this date/time."),
#     created_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description="Search for files created within this date/time range (e.g., ['2024-01-01', '2024-03-31'])."),
#     modified_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description="Search for files modified within this date/time range."),
#     accessed_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description="Search for files last accessed within this date/time range."),

#     db: Session = Depends(get_db_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Search for file metadata based on keywords, file size ranges, and date/time ranges.
#     """
#     # Check if any search criterion is provided
#     if not any([
#         keywords, size_gt, size_lt, size_between,
#         created_after, created_before, modified_after, modified_before,
#         accessed_after, accessed_before, created_between, modified_between, accessed_between
#     ]):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Please provide at least one search criterion."
#         )

#     # Parse size parameters
#     parsed_min_size_bytes = None
#     parsed_max_size_bytes = None
#     try:
#         if size_gt:
#             parsed_min_size_bytes = convert_human_readable_to_bytes(size_gt)
#         if size_lt:
#             parsed_max_size_bytes = convert_human_readable_to_bytes(size_lt)
#         if size_between:
#             parsed_min_size_bytes = convert_human_readable_to_bytes(size_between[0])
#             parsed_max_size_bytes = convert_human_readable_to_bytes(size_between[1])
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid size format: {e}")

#     # Parse date parameters
#     parsed_created_after: Optional[datetime] = None
#     parsed_created_before: Optional[datetime] = None
#     parsed_modified_after: Optional[datetime] = None
#     parsed_modified_before: Optional[datetime] = None
#     parsed_accessed_after: Optional[datetime] = None
#     parsed_accessed_before: Optional[datetime] = None

#     try:
#         if created_after:
#             parsed_created_after = parse_date_string(created_after)
#         if created_before:
#             parsed_created_before = parse_date_string(created_before)
#         if created_between:
#             parsed_created_after = parse_date_string(created_between[0])
#             parsed_created_before = parse_date_string(created_between[1])

#         if modified_after:
#             parsed_modified_after = parse_date_string(modified_after)
#         if modified_before:
#             parsed_modified_before = parse_date_string(modified_before)
#         if modified_between:
#             parsed_modified_after = parse_date_string(modified_between[0])
#             parsed_modified_before = parse_date_string(modified_between[1])

#         if accessed_after:
#             parsed_accessed_after = parse_date_string(accessed_after)
#         if accessed_before:
#             parsed_accessed_before = parse_date_string(accessed_before)
#         if accessed_between:
#             parsed_accessed_after = parse_date_string(accessed_between[0])
#             parsed_accessed_before = parse_date_string(accessed_between[1])

#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid date format: {e}")

#     try:
#         # Call the comprehensive search function
#         files = search_files_by_criteria(
#             db=db,
#             keywords=keywords,
#             min_size_bytes=parsed_min_size_bytes,
#             max_size_bytes=parsed_max_size_bytes,
#             created_after=parsed_created_after,
#             created_before=parsed_created_before,
#             modified_after=parsed_modified_after,
#             modified_before=parsed_modified_before,
#             accessed_after=parsed_accessed_after,
#             accessed_before=parsed_accessed_before
#         )
        
#         return [FileResponse.from_orm(file) for file in files]

#     except OperationalError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


# @app.post("/files/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
# async def add_file_metadata_api(
#     request: FileAddRequest,
#     db: Session = Depends(get_db_session),
#     current_user: User = Depends(get_current_user) # Authenticated access
# ):
#     """
#     Adds a new metadata record for an existing file on the server.
#     """
#     try:
#         file_record = add_file_metadata(db, request.filepath, request.tags)
#         return FileResponse.from_orm(file_record)
#     except FileNotFoundError as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     except OperationalError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# @app.get("/files/{file_id}", response_model=FileResponse)
# async def get_file_metadata_api(
#     file_id: int,
#     db: Session = Depends(get_db_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Retrieves full metadata for a single file by its ID.
#     """
#     try:
#         file_record = get_file_metadata(db, file_id)
#         return FileResponse.from_orm(file_record)
#     except NoResultFound as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except OperationalError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# @app.put("/files/{file_id}", response_model=FileResponse)
# async def update_file_metadata_api(
#     file_id: int,
#     request: FileUpdateRequest,
#     db: Session = Depends(get_db_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Updates metadata for a file identified by its ID.
#     """
#     if not request.tags_to_add_modify and not request.tags_to_remove and not request.new_filepath and not request.overwrite:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Please provide at least one option to update (tags_to_add_modify, tags_to_remove, new_filepath, or overwrite)."
#         )

#     if request.overwrite and request.tags_to_remove:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cannot use 'overwrite' and 'tags_to_remove' together. 'overwrite' clears all tags before applying new ones."
#         )

#     try:
#         updated_file = update_file_tags(
#             db,
#             file_id,
#             tags_to_add_modify=request.tags_to_add_modify,
#             tags_to_remove=request.tags_to_remove,
#             new_filepath=request.new_filepath,
#             overwrite_existing=request.overwrite
#         )
#         return FileResponse.from_orm(updated_file)
#     except NoResultFound as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     except OperationalError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# @app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_file_metadata_api(
#     file_id: int,
#     db: Session = Depends(get_db_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Permanently removes a file's metadata record from the database.
#     This does NOT affect the actual file on the filesystem.
#     """
#     try:
#         delete_file_metadata(db, file_id)
#         return {"message": f"Metadata for file ID {file_id} deleted successfully."}
#     except NoResultFound as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except OperationalError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# @app.get("/files/", response_model=List[FileResponse])
# async def list_files_api(
#     db: Session = Depends(get_db_session),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Displays all file metadata records currently stored in the database.
#     """
#     try:
#         files = list_files(db)
#         return [FileResponse.from_orm(file) for file in files]
#     except OperationalError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


# if __name__ == "__main__":
#     if not os.getenv("DATABASE_URL"):
#         print("\nWARNING: DATABASE_URL environment variable is not set.")
#         print("Please set it, e.g.: export DATABASE_URL='postgresql://filemeta_user:your_strong_password@localhost/filemeta_db'")
#         print("Using default (possibly incorrect) DATABASE_URL. API might not connect to DB.\n")

#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# main.py
import uvicorn
import os
from typing import List, Dict, Union, Optional, Tuple
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, OperationalError, IntegrityError
from datetime import datetime

# Import your core metadata management functions
from filemeta.database import get_db, init_db as filemeta_init_db, close_db_engine
from filemeta.metadata_manager import (
    add_file_metadata,
    list_files,
    get_file_metadata,
    update_file_tags,
    delete_file_metadata,
    search_files_by_criteria, # Existing comprehensive search function
    rename_file_entry,         # NEW: Renaming function
    list_and_search_tags,      # NEW: Tag listing/searching function
    validate_file_metadata     # NEW: Validation function
)
from filemeta.models import File # Keep this import, even if not directly used for ORM conversion

# Import Pydantic schemas and authentication/authorization logic
from schemas import (
    Token, User, UserCreate, UserResponse,
    FileAddRequest, FileUpdateRequest, FileResponse,
    UserBase, SearchQueryParams,
    FileRenameRequest,           # NEW: For renaming files
    TagResponse, UniqueTagKeyValuePair, TagListSearchQueryParams, # NEW: For tags endpoint
    FileValidationRequest, FileValidationResult # NEW: For validation endpoint
)
from auth import (
    authenticate_user, create_access_token, get_password_hash,
    get_current_user, get_admin_user, FAKE_USERS_DB
)
from dependencies import get_db_session
from filemeta.utils import convert_human_readable_to_bytes, parse_date_string # New import for date parsing

# Create the FastAPI app
app = FastAPI(
    title="File Metadata API",
    description="A REST API for managing server file metadata with user authentication and roles."
)

# --- API Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """
    On startup, initialize the file metadata database and create a default admin user
    if they don't already exist in our in-memory user store.
    """
    print("API starting up...")
    try:
        # Initialize the file metadata database (tables)
        filemeta_init_db()
        print("File metadata database tables initialized.")
    except OperationalError as e:
        print(f"ERROR: Database connection failed at startup: {e}", flush=True)
    except Exception as e:
        print(f"ERROR: Unexpected error during file metadata DB init: {e}", flush=True)

    # Initialize a default admin user if not exists
    if "admin" not in FAKE_USERS_DB:
        hashed_password = get_password_hash("adminpass") # Default admin password
        FAKE_USERS_DB["admin"] = User(
            id=1, username="admin", hashed_password=hashed_password, role="admin"
        )
        print("Default admin user 'admin' created with password 'adminpass'.")

    # Initialize a default regular user if not exists
    if "user1" not in FAKE_USERS_DB:
        hashed_password = get_password_hash("userpass") # Default user password
        FAKE_USERS_DB["user1"] = User(
            id=2, username="user1", hashed_password=hashed_password, role="user"
        )
        print("Default user 'user1' created with password 'userpass'.")

    print("API startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    On shutdown, close the database engine connection.
    """
    print("API shutting down...")
    close_db_engine()
    print("Database engine closed.")
    print("API shutdown complete.")

# --- Authentication Endpoints ---
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint for users to authenticate and get an access token.
    Requires `username` and `password` in the form data.
    """
    user = authenticate_user(FAKE_USERS_DB, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Management Endpoints (Admin Only) ---
@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    """
    return UserResponse(id=current_user.id, username=current_user.username, role=current_user.role)

@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(user: UserCreate, current_admin_user: User = Depends(get_admin_user)):
    """
    Create a new user. Only accessible by admin users.
    Default role for new users is 'user'.
    """
    if user.username in FAKE_USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    user_id = len(FAKE_USERS_DB) + 1 # Simple incrementing ID
    hashed_password = get_password_hash(user.password)
    new_user = User(
        id=user_id, username=user.username, hashed_password=hashed_password, role="user"
    )
    FAKE_USERS_DB[user.username] = new_user
    return UserResponse(id=new_user.id, username=new_user.username, role=new_user.role)

@app.get("/users/", response_model=List[UserResponse])
async def list_all_users(current_admin_user: User = Depends(get_admin_user)):
    """
    List all registered users. Only accessible by admin users.
    """
    return [UserResponse(id=u.id, username=u.username, role=u.role) for u in FAKE_USERS_DB.values()]

# --- File Metadata Endpoints (Admin & User) ---

# IMPORTANT: Define the more specific /files/search route BEFORE /files/{file_id}
@app.get("/files/search", response_model=List[FileResponse])
async def search_files_api(
    keywords: Optional[List[str]] = Query(None, description="Keywords to search for in file metadata (filename, path, owner, tags). Can be repeated."),
    size_gt: Optional[str] = Query(None, description='Search for files larger than the specified size (e.g., "10MB", "1GB").'),
    size_lt: Optional[str] = Query(None, description='Search for files smaller than the specified size (e.g., "100KB", "1GB").'),
    size_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description='Search for files within a size range (e.g., "100KB 1MB"). Requires two values.'),
    # New date/time search parameters
    created_after: Optional[str] = Query(None, description="Search for files created after this date/time (e.g., '2024-01-01' or '2024-06-11 10:00:00')."),
    created_before: Optional[str] = Query(None, description="Search for files created before this date/time."),
    modified_after: Optional[str] = Query(None, description="Search for files modified after this date/time."),
    modified_before: Optional[str] = Query(None, description="Search for files modified before this date/time."),
    accessed_after: Optional[str] = Query(None, description="Search for files last accessed after this date/time."),
    accessed_before: Optional[str] = Query(None, description="Search for files last accessed before this date/time."),
    created_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description="Search for files created within this date/time range (e.g., ['2024-01-01', '2024-03-31'])."),
    modified_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description="Search for files modified within this date/time range."),
    accessed_between: Optional[List[str]] = Query(None, min_items=2, max_items=2, description="Search for files last accessed within this date/time range."),

    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Search for file metadata based on keywords, file size ranges, and date/time ranges.
    """
    # Check if any search criterion is provided
    if not any([
        keywords, size_gt, size_lt, size_between,
        created_after, created_before, modified_after, modified_before,
        accessed_after, accessed_before, created_between, modified_between, accessed_between
    ]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one search criterion."
        )

    # Parse size parameters
    parsed_min_size_bytes = None
    parsed_max_size_bytes = None
    try:
        if size_gt:
            parsed_min_size_bytes = convert_human_readable_to_bytes(size_gt)
        if size_lt:
            parsed_max_size_bytes = convert_human_readable_to_bytes(size_lt)
        if size_between:
            parsed_min_size_bytes = convert_human_readable_to_bytes(size_between[0])
            parsed_max_size_bytes = convert_human_readable_to_bytes(size_between[1])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid size format: {e}")

    # Parse date parameters
    parsed_created_after: Optional[datetime] = None
    parsed_created_before: Optional[datetime] = None
    parsed_modified_after: Optional[datetime] = None
    parsed_modified_before: Optional[datetime] = None
    parsed_accessed_after: Optional[datetime] = None
    parsed_accessed_before: Optional[datetime] = None

    try:
        if created_after:
            parsed_created_after = parse_date_string(created_after)
        if created_before:
            parsed_created_before = parse_date_string(created_before)
        if created_between:
            parsed_created_after = parse_date_string(created_between[0])
            parsed_created_before = parse_date_string(created_between[1])

        if modified_after:
            parsed_modified_after = parse_date_string(modified_after)
        if modified_before:
            parsed_modified_before = parse_date_string(modified_before)
        if modified_between:
            parsed_modified_after = parse_date_string(modified_between[0])
            parsed_modified_before = parse_date_string(modified_between[1])

        if accessed_after:
            parsed_accessed_after = parse_date_string(accessed_after)
        if accessed_before:
            parsed_accessed_before = parse_date_string(accessed_before)
        if accessed_between:
            parsed_accessed_after = parse_date_string(accessed_between[0])
            parsed_accessed_before = parse_date_string(accessed_between[1])

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid date format: {e}")

    try:
        # Call the comprehensive search function
        files = search_files_by_criteria(
            db=db,
            keywords=keywords,
            min_size_bytes=parsed_min_size_bytes,
            max_size_bytes=parsed_max_size_bytes,
            created_after=parsed_created_after,
            created_before=parsed_created_before,
            modified_after=parsed_modified_after,
            modified_before=parsed_modified_before,
            accessed_after=parsed_accessed_after,
            accessed_before=parsed_accessed_before
        )
        
        return [FileResponse.from_orm(file) for file in files]

    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@app.post("/files/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def add_file_metadata_api(
    request: FileAddRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user) # Authenticated access
):
    """
    Adds a new metadata record for an existing file on the server.
    """
    try:
        file_record = add_file_metadata(db, request.filepath, request.tags)
        return FileResponse.from_orm(file_record)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.get("/files/{file_id}", response_model=FileResponse)
async def get_file_metadata_api(
    file_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves full metadata for a single file by its ID.
    """
    try:
        file_record = get_file_metadata(db, file_id)
        return FileResponse.from_orm(file_record)
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.put("/files/{file_id}", response_model=FileResponse)
async def update_file_metadata_api(
    file_id: int,
    request: FileUpdateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates metadata for a file identified by its ID.
    """
    if not request.tags_to_add_modify and not request.tags_to_remove and not request.new_filepath and not request.overwrite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one option to update (tags_to_add_modify, tags_to_remove, new_filepath, or overwrite)."
        )

    if request.overwrite and request.tags_to_remove:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot use 'overwrite' and 'tags_to_remove' together. 'overwrite' clears all tags before applying new ones."
        )

    try:
        updated_file = update_file_tags(
            db,
            file_id,
            tags_to_add_modify=request.tags_to_add_modify,
            tags_to_remove=request.tags_to_remove,
            new_filepath=request.new_filepath,
            overwrite_existing=request.overwrite
        )
        return FileResponse.from_orm(updated_file)
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_metadata_api(
    file_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Permanently removes a file's metadata record from the database.
    This does NOT affect the actual file on the filesystem.
    """
    try:
        delete_file_metadata(db, file_id)
        return {"message": f"Metadata for file ID {file_id} deleted successfully."}
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@app.get("/files/", response_model=List[FileResponse])
async def list_files_api(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Displays all file metadata records currently stored in the database.
    """
    try:
        files = list_files(db)
        return [FileResponse.from_orm(file) for file in files]
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# NEW: Endpoint for renaming a file on disk and updating its metadata
@app.put("/files/{file_id}/rename", response_model=FileResponse)
async def rename_file_api(
    file_id: int,
    request: FileRenameRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user) # Can be admin or regular user
):
    """
    Renames a file on the disk and updates its corresponding metadata entry in the database.
    """
    try:
        updated_file = rename_file_entry(db, file_id, request.new_name)
        return FileResponse.from_orm(updated_file)
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found on disk: {e}")
    except FileExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A file with the new name already exists: {e}")
    except (PermissionError, OSError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission or OS error during rename: {e}")
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# NEW: Endpoint for listing and searching tags
@app.get("/tags/", response_model=Union[List[TagResponse], List[UniqueTagKeyValuePair]])
async def list_and_search_tags_api(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    unique: bool = Query(False, description="If True, returns unique tag keys or unique key-value pairs."),
    sort_by: Optional[str] = Query(None, description="Sort results by 'key' or 'value'."),
    sort_order: str = Query('asc', description="Sort order: 'asc' or 'desc'."),
    limit: Optional[int] = Query(None, gt=0, description="Maximum number of results to return."),
    offset: int = Query(0, ge=0, description="Number of results to skip."),
    keywords: Optional[List[str]] = Query(None, description="Keywords to search for in tag keys or values.")
):
    """
    Lists and searches tags with options for uniqueness, sorting, pagination, and keyword filtering.
    Returns TagResponse objects by default. If unique=True, returns unique key-value pairs.
    """
    if sort_by not in [None, 'key', 'value']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_by value. Must be 'key' or 'value'.")
    if sort_order not in ['asc', 'desc']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_order value. Must be 'asc' or 'desc'.")

    try:
        results = list_and_search_tags(
            db=db,
            unique=unique,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
            keywords=keywords
        )
        
        # Determine the correct Pydantic model for the response based on 'unique' flag
        if unique:
            # list_and_search_tags returns List[Tuple[str, str]] when unique=True
            # Convert tuples to UniqueTagKeyValuePair models
            return [UniqueTagKeyValuePair(key=item[0], value=item[1]) for item in results]
        else:
            # list_and_search_tags returns List[Tag] when unique=False
            return [TagResponse.from_orm(tag) for tag in results]

    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# NEW: Endpoint for validating file metadata
@app.post("/files/validate", response_model=List[FileValidationResult])
async def validate_files_api(
    request: FileValidationRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user) # Can be admin or regular user
):
    """
    Validates file metadata records against file system existence and tag presence.
    """
    try:
        validation_results = validate_file_metadata(
            db=db,
            check_all=request.check_all,
            criteria=request.criteria,
            tag_key=request.tag_key,
            tag_value=request.tag_value
        )
        return validation_results
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print("\nWARNING: DATABASE_URL environment variable is not set.")
        print("Please set it, e.g.: export DATABASE_URL='postgresql://filemeta_user:your_strong_password@localhost/filemeta_db'")
        print("Using default (possibly incorrect) DATABASE_URL. API might not connect to DB.\n")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
