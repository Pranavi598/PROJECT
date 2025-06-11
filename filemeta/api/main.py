# filemeta/api/main.py

# Removed 'import os' as we're no longer using os.getenv in this file for JWT expiry
from fastapi import FastAPI, HTTPException, Query, Depends, APIRouter, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from sqlalchemy.orm import Session # Added this import for type hinting in dependencies
from sqlalchemy.exc import NoResultFound, OperationalError, IntegrityError
from datetime import timedelta

from ..database import get_db, create_user, get_user_by_username
from ..metadata_manager import (
    add_file_metadata,
    get_all_files_for_listing,
    get_file_by_id,
    search_files_by_criteria,
    update_file_tags,
    delete_file_metadata
)
from ..models import File, User # Ensure User is imported for type hinting in dependencies
from .auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES # Import the constant
from .dependencies import get_current_user, get_current_admin_user
from .schemas import (
    AddFileRequest,
    UpdateTagsRequest,
    FileMetadataResponse,
    UserCreateRequest,
    UserResponse,
    Token
)

app = FastAPI(
    title="FileMeta API",
    description="API for managing server file metadata.",
    version="1.0.0"
)

# --- Routers for better organization ---
admin_router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_admin_user)])
public_router = APIRouter(tags=["Auth & Public"])
file_router = APIRouter(prefix="/files", tags=["Files"], dependencies=[Depends(get_current_user)])


# --- Public Endpoints (Login) ---
@public_router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticates a user and returns an access token.
    """
    user = get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Use the ACCESS_TOKEN_EXPIRE_MINUTES constant directly from auth.py
    # No need for os.getenv or int() conversion here as it's already an int in auth.py
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "user_role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create user: {e}")

@admin_router.get("/users", response_model=List[UserResponse])
async def get_all_users(db: Session = Depends(get_db)):
    """
    Retrieves all user accounts (Admin only).
    """
    users = db.query(User).all()
    return users

@admin_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_api(user_id: int, db: Session = Depends(get_db)):
    """
    Deletes a user account (Admin only).
    """
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Optional: Logic to reassign files owned by this user or delete them
    # For now, just delete the user record.
    try:
        db.delete(user_to_delete)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete user: {e}")
    return


# --- File Management Endpoints (Requires Authentication, User or Admin) ---
@file_router.post("/", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_file_metadata(request: AddFileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Adds a new metadata record for a file, associating it with the logged-in user.
    """
    try:
        file_record = add_file_metadata(db, request.filepath, request.custom_tags, owner_id=current_user.id)
        return file_record.to_dict()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@file_router.get("/", response_model=List[FileMetadataResponse])
async def get_all_files_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves all file metadata records. Admins see all; regular users only see their own.
    """
    try:
        if current_user.role == 'admin':
            files = get_all_files_for_listing(db)
        else:
            files = db.query(File).filter(File.owner == str(current_user.id)).all()

        return [file.to_dict() for file in files]
    except OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@file_router.get("/{file_id}", response_model=FileMetadataResponse)
async def get_single_file_metadata(file_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves a single file metadata record by ID. Users can only access their own files or if admin.
    """
    try:
        file_record = get_file_by_id(db, file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")

        if current_user.role != 'admin' and file_record.owner != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this file.")

        return file_record.to_dict()
    except OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@file_router.get("/search/", response_model=List[FileMetadataResponse])
async def search_file_metadata(
    keywords: List[str] = Query(..., description="Keywords to search for (can be repeated)."),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Searches for files by keywords. Admins search all files; regular users search their own files.
    """
    if not keywords:
        raise HTTPException(status_code=400, detail="Please provide at least one keyword.")
    
    try:
        owner_id_for_search = None if current_user.role == 'admin' else current_user.id
        files = search_files_by_criteria(db, keywords, owner_id=owner_id_for_search)
        
        return [file.to_dict() for file in files]
    except OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@file_router.patch("/{file_id}/tags/", response_model=FileMetadataResponse)
async def update_file_custom_tags(file_id: int, request: UpdateTagsRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Updates or adds custom tags for a specific file. Only file owner or admin can update.
    """
    file_to_update = get_file_by_id(db, file_id)
    if not file_to_update:
        raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")

    if current_user.role != 'admin' and file_to_update.owner != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this file.")

    try:
        updated_file = update_file_tags(db, file_id, request.tags, request.overwrite)
        return updated_file.to_dict()
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")
    except OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@file_router.delete("/{file_id}", status_code=204)
async def delete_file_metadata_api(file_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Deletes a file metadata record. Only file owner or admin can delete.
    """
    file_to_delete = get_file_by_id(db, file_id)
    if not file_to_delete:
        raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")

    if current_user.role != 'admin' and file_to_delete.owner != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this file.")

    try:
        success = delete_file_metadata(db, file_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete file with ID {file_id}.")
        return
    except OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# Include the routers in the main app
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(file_router)