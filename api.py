# filemeta_project/api.py

import os
import json
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # Import for auth
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, IntegrityError
from datetime import datetime, timedelta # Ensure timedelta is imported if used for token expiry

# Corrected absolute imports for models and manager functions
from papilv_filemeta.database import init_db, get_db
from papilv_filemeta.metadata_manager import (
    add_file_metadata,
    list_files,
    get_file_metadata,
    search_files,
    update_file_tags,
    delete_file_metadata
)
# Alias to avoid conflict with Pydantic 'File' and 'Tag' used in responses
from papilv_filemeta.models import File as DBFile, Tag as DBTag, User as DBUser # Import DBUser
from papilv_filemeta.api.auth import ( # Assuming your auth logic is in papilv_filemeta/api/auth.py
    authenticate_user,
    create_access_token,
    get_current_active_user, # This function will provide the authenticated user
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# --- Pydantic Models for API Request/Response ---

# Tag model for response
class TagResponse(BaseModel):
    key: str
    value: str
    value_type: str

    class Config:
        from_attributes = True


# File model for response
class FileResponse(BaseModel):
    id: int
    filename: str
    filepath: str
    # owner: Optional[str] = None # Will be populated based on owner_id join
    # created_by: Optional[str] = None # Will be populated based on created_by value
    owner_username: Optional[str] = Field(None, alias="owner") # Use alias for owner field in response to match CLI
    created_by_username: Optional[str] = Field(None, alias="created_by") # Use alias for created_by field in response
    created_at: datetime
    updated_at: datetime
    inferred_tags: Optional[Dict[str, Any]] = None # Should be a dictionary
    tags: List['TagResponse'] = [] # List of TagResponse objects

    # Validator to handle potential stringified JSON from older DB entries or inconsistent data
    @validator('inferred_tags', pre=True, always=True)
    def parse_inferred_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

    class Config:
        from_attributes = True
        json_dumps = json.dumps


# Model for adding file metadata (request body)
class FileCreate(BaseModel):
    filepath: str
    custom_tags: Dict[str, Any] = {} # Default to empty dict is good


# Model for updating file metadata (request body)
class FileUpdate(BaseModel):
    tags_to_add_modify: Optional[Dict[str, Any]] = None
    tags_to_remove: Optional[List[str]] = None
    new_filepath: Optional[str] = None
    overwrite_existing: bool = False


# Model for search query (query parameters)
class FileSearchQuery(BaseModel):
    keywords: str = Field(..., description="Comma-separated keywords to search for")


# --- FastAPI Application Instance ---
app = FastAPI(
    title="File Metadata API",
    description="API for managing file metadata.",
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


# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "Welcome to the File Metadata API! Visit /docs for API documentation."}

# Login endpoint to get a token
@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/files/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def create_file_metadata(
    file_data: FileCreate,
    db: Session = Depends(get_db), # Dependency for database session
    current_user: DBUser = Depends(get_current_active_user) # Authentication dependency
):
    """
    Adds new metadata for a file.
    """
    try:
        # Pass owner_id and created_by from the authenticated user
        file_record = add_file_metadata(
            db,
            filepath=file_data.filepath,
            custom_tags=file_data.custom_tags,
            owner_id=current_user.id,        # Use the ID of the authenticated user
            created_by=current_user.username  # Use the username of the authenticated user
        )
        return file_record
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e: # For cases like file already exists, or other business logic errors
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except IntegrityError as e: # Catch database integrity errors specifically
        db.rollback() # Crucial to rollback the session on integrity errors
        # Extract PostgreSQL specific error if available for better detail
        detail_msg = f"Database integrity error: {e.orig.pgerror}" if hasattr(e.orig, 'pgerror') else str(e)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail_msg)
    except Exception as e:
        # THIS IS THE CRITICAL CHANGE FOR DEBUGGING: Include the exception type and message
        print(f"DEBUG: Unhandled exception in create_file_metadata: {type(e).__name__}: {e}") # Log on server
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add file metadata: {type(e).__name__}: {e}")


@app.get("/files/", response_model=List[FileResponse])
async def read_files(db: Session = Depends(get_db)): # Add DB dependency
    """
    Lists all stored file metadata.
    """
    try:
        files = list_files(db)
        return files
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve files: {type(e).__name__}: {e}")

@app.get("/files/{file_id}", response_model=FileResponse)
async def read_file_metadata(file_id: int, db: Session = Depends(get_db)): # Add DB dependency
    """
    Retrieves metadata for a specific file by ID.
    """
    try:
        file_record = get_file_metadata(db, file_id)
        if file_record is None:
            raise NoResultFound(f"File with ID {file_id} not found")
        return file_record
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve file metadata: {type(e).__name__}: {e}")

@app.get("/files/search/", response_model=List[FileResponse])
async def search_file_metadata(query: FileSearchQuery = Depends(), db: Session = Depends(get_db)): # Add DB dependency
    """
    Searches for files based on keywords across various metadata fields.
    Keywords should be provided as a comma-separated string in the query parameter.
    Example: /files/search/?keywords=report,finance
    """
    keywords_list = [k.strip() for k in query.keywords.split(',') if k.strip()]

    try:
        files = search_files(db, keywords_list)
        return files
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to perform search: {type(e).__name__}: {e}")


@app.put("/files/{file_id}", response_model=FileResponse)
async def update_file_metadata(
    file_id: int,
    update_data: FileUpdate,
    db: Session = Depends(get_db), # Add DB dependency
    current_user: DBUser = Depends(get_current_active_user) # Add authentication for update
):
    """
    Updates metadata (tags, filepath) for a specific file.
    """
    try:
        updated_file = update_file_tags(
            db,
            file_id,
            tags_to_add_modify=update_data.tags_to_add_modify,
            tags_to_remove=update_data.tags_to_remove,
            new_filepath=update_data.new_filepath,
            overwrite_existing=update_data.overwrite_existing
        )
        return updated_file
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e: # For invalid input or conflicts
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update file metadata: {type(e).__name__}: {e}")

@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_metadata_api(file_id: int, db: Session = Depends(get_db)): # Add DB dependency
    """
    Deletes metadata for a specific file by ID.
    """
    try:
        delete_file_metadata(db, file_id)
        return {}
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete file metadata: {type(e).__name__}: {e}")