# filemeta_project/api.py (This is your main application file now)

import os
from fastapi import FastAPI, HTTPException, Query, Depends, APIRouter, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, OperationalError, IntegrityError
from datetime import timedelta

# Corrected absolute imports for modules within papilv_filemeta
from papilv_filemeta.database import init_db, get_db, create_user, get_user_by_username
from papilv_filemeta.metadata_manager import ( # Standardized function names
    add_file_metadata,
    list_files,          # Renamed from get_all_files_for_listing
    get_file_metadata,   # Renamed from get_file_by_id
    search_files,        # Renamed from search_files_by_criteria
    update_file_tags,
    delete_file_metadata
)
from papilv_filemeta.models import File as DBFile, User as DBUser # Alias DB models to avoid Pydantic name clash
from papilv_filemeta.api.auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from papilv_filemeta.api.dependencies import get_current_user, get_current_admin_user
from papilv_filemeta.api.schemas import ( # Assuming schemas are in papilv_filemeta/api/schemas.py
    FileCreate,          # Renamed from AddFileRequest
    FileResponse,        # Renamed from FileMetadataResponse
    UserCreateRequest,
    UserResponse,
    Token,
    FileUpdate           # Renamed from UpdateTagsRequest, matches previous api.py structure
)


app = FastAPI(
    title="FileMeta API",
    description="API for managing server file metadata with authentication.",
    version="1.0.0"
)

# --- Startup Event: Initialize Database ---
@app.on_event("startup")
def on_startup():
    """Initializes the database when the FastAPI application starts."""
    print("FastAPI app starting up: Initializing database...")
    try:
        init_db()
        print("Database initialization complete.")
    except Exception as e:
        print(f"Error during database initialization: {e}")
        # Optionally, re-raise the exception to prevent the app from starting if DB is critical
        # raise

# --- Routers for better organization ---
admin_router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_admin_user)])
public_router = APIRouter(tags=["Auth & Public"])
file_router = APIRouter(prefix="/files", tags=["Files"], dependencies=[Depends(get_current_user)])


# --- Public Endpoints (Login & Root) ---

@app.get("/")
async def root():
    return {"message": "Welcome to the File Metadata API! Visit /docs for API documentation."}

# papilv_filemeta/api/main.py
# ...
@public_router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticates a user and returns an access token.
    """
    print(f"DEBUG: Inside login_for_access_token. Type of 'db' is: {type(db)}") # ADD THIS LINE
    user = get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        # ... rest of the code
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "user_role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- Admin Endpoints ---
@admin_router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_api(user_create: UserCreateRequest, db: Session = Depends(get_db)):
    """
    Creates a new user account (Admin only).
    """
    try:
        hashed_password = get_password_hash(user_create.password)
        new_user = create_user(db, username=user_create.username, hashed_password=hashed_password, role=user_create.role)
        return new_user
    except ValueError as e: # Catch duplicate username specifically from create_user
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create user: {e}")

@admin_router.get("/users", response_model=List[UserResponse])
async def get_all_users(db: Session = Depends(get_db)): # No current_user needed here due to router dependency
    """
    Retrieves all user accounts (Admin only).
    """
    users = db.query(DBUser).all() # Use DBUser alias
    return users

@admin_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_api(user_id: int, db: Session = Depends(get_db)): # No current_user needed here due to router dependency
    """
    Deletes a user account (Admin only).
    """
    user_to_delete = db.query(DBUser).filter(DBUser.id == user_id).first() # Use DBUser alias
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        db.delete(user_to_delete)
        db.commit()
    except IntegrityError as e: # Catch potential foreign key constraints
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot delete user: {e}. Check if files are owned by this user.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete user: {e}")
    return


# --- File Management Endpoints (Requires Authentication, User or Admin) ---

# Renamed AddFileRequest to FileCreate for consistency with previous discussion
@file_router.post("/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def create_file_metadata_api(file_data: FileCreate, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Adds a new metadata record for a file, associating it with the logged-in user.
    """
    try:
        # Pass current_user.id as owner_id to metadata_manager
        file_record = add_file_metadata(db, file_data.filepath, file_data.custom_tags, owner_id=current_user.id)
        return file_record # Pydantic model will handle conversion from DBFile
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e: # For cases like file already exists in DB
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except OperationalError as e: # Catch DB connection/operation errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database operational error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@file_router.get("/", response_model=List[FileResponse])
async def list_all_files_api(current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves all file metadata records. Admins see all; regular users only see their own.
    """
    try:
        if current_user.role == 'admin':
            files = list_files(db) # Uses the new function name from metadata_manager
        else:
            # Assumes File.owner is an Integer (foreign key to User.id)
            files = db.query(DBFile).filter(DBFile.owner == current_user.id).all() 
        
        return files # Pydantic model will handle conversion from List[DBFile]
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database operational error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@file_router.get("/{file_id}", response_model=FileResponse)
async def get_single_file_metadata_api(file_id: int, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves a single file metadata record by ID. Users can only access their own files or if admin.
    """
    try:
        file_record = get_file_metadata(db, file_id) # Uses the new function name from metadata_manager
        if not file_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with ID {file_id} not found.")

        # Ensure correct type comparison: file_record.owner (int) vs current_user.id (int)
        if current_user.role != 'admin' and file_record.owner != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this file.")

        return file_record # Pydantic model will handle conversion from DBFile
    except NoResultFound as e: # Catch if get_file_metadata raises NoResultFound
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database operational error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@file_router.get("/search/", response_model=List[FileResponse])
async def search_file_metadata_api(
    keywords: str = Query(..., description="Comma-separated keywords to search for."), # Changed to str for consistency
    current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Searches for files by keywords. Admins search all files; regular users search their own files.
    """
    keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
    if not keywords_list:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please provide at least one keyword.")
    
    try:
        # Pass owner_id for search if not admin
        owner_id_for_search = None if current_user.role == 'admin' else current_user.id
        files = search_files(db, keywords_list, owner_id=owner_id_for_search) # Uses the new function name from metadata_manager
        
        return files # Pydantic model will handle conversion from List[DBFile]
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database operational error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

# Renamed UpdateTagsRequest to FileUpdate for consistency with previous discussion
@file_router.patch("/{file_id}", response_model=FileResponse) # Changed to PATCH for partial updates
async def update_file_custom_tags_api(file_id: int, update_data: FileUpdate, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Updates or adds custom tags and/or filepath for a specific file. Only file owner or admin can update.
    """
    file_to_update = get_file_metadata(db, file_id) # Get file first to check ownership
    if not file_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with ID {file_id} not found.")

    # Ensure correct type comparison: file_to_update.owner (int) vs current_user.id (int)
    if current_user.role != 'admin' and file_to_update.owner != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this file.")

    try:
        # Use the correct update_file_tags function signature
        updated_file = update_file_tags(
            db,
            file_id,
            tags_to_add_modify=update_data.tags_to_add_modify,
            tags_to_remove=update_data.tags_to_remove,
            new_filepath=update_data.new_filepath,
            overwrite_existing=update_data.overwrite_existing
        )
        return updated_file # Pydantic model will handle conversion from DBFile
    except NoResultFound as e: # Catch if update_file_tags raises NoResultFound
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e: # From update_file_tags for invalid filepath, conflicts etc.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database operational error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


@file_router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_metadata_api(file_id: int, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Deletes a file metadata record. Only file owner or admin can delete.
    """
    file_to_delete = get_file_metadata(db, file_id) # Get file first to check ownership
    if not file_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with ID {file_id} not found.")

    # Ensure correct type comparison: file_to_delete.owner (int) vs current_user.id (int)
    if current_user.role != 'admin' and file_to_delete.owner != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this file.")

    try:
        # delete_file_metadata returns None upon successful deletion
        delete_file_metadata(db, file_id)
        return {} # Return empty dict for 204 No Content
    except NoResultFound as e: # Catch if delete_file_metadata raises NoResultFound
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database operational error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


# Include the routers in the main app
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(file_router)
