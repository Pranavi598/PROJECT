from fastapi import FastAPI, HTTPException, Body, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.exc import NoResultFound, OperationalError
from datetime import datetime

from .database import get_db
from .metadata_manager import (
    add_file_metadata,
    list_files,
    get_file_metadata,
    search_files,
    update_file_tags,
    delete_file_metadata # You'd need to implement this in metadata_manager.py
)
from .models import File # To help with conversion to dict

app = FastAPI(
    title="FileMeta API",
    description="API for managing server file metadata.",
    version="1.0.0"
)

# Pydantic models for request/response bodies
class AddFileRequest(BaseModel):
    filepath: str = Field(..., example="/server/data/document.pdf")
    custom_tags: Optional[Dict[str, str]] = {}

class UpdateTagsRequest(BaseModel):
    tags: Dict[str, str] = {}
    overwrite: bool = False

class FileMetadataResponse(BaseModel):
    ID: int
    Filename: str
    Filepath: str
    Owner: str
    Created_By: str = Field(..., alias="Created By")
    Created_At: datetime = Field(..., alias="Created At")
    Updated_At: datetime = Field(..., alias="Updated At")
    Inferred_Tags: Dict[str, Any] = Field(..., alias="Inferred Tags")
    Custom_Tags: Dict[str, Any] = Field(..., alias="Custom Tags") # <--- CHANGE THIS LINE

    class Config:
        populate_by_name = True
        from_attributes = True

# --- API Endpoints ---

@app.post("/files/", response_model=FileMetadataResponse)
async def create_file_metadata(request: AddFileRequest):
    with get_db() as db:
        try:
            file_record = add_file_metadata(db, request.filepath, request.custom_tags)
            return file_record.to_dict() # Assuming to_dict() provides the fields for FileMetadataResponse
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except OperationalError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/files/", response_model=List[FileMetadataResponse])
async def get_all_files():
    with get_db() as db:
        try:
            files = list_files(db)
            return [file.to_dict() for file in files]
        except OperationalError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/files/{file_id}", response_model=FileMetadataResponse)
async def get_single_file_metadata(file_id: int):
    with get_db() as db:
        try:
            file_record = get_file_metadata(db, file_id)
            return file_record.to_dict()
        except NoResultFound:
            raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")
        except OperationalError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/files/search/", response_model=List[FileMetadataResponse])
async def search_file_metadata(
    keywords: List[str] = Query(..., description="Keywords to search for (can be repeated).")
):
    if not keywords:
        raise HTTPException(status_code=400, detail="Please provide at least one keyword.")
    with get_db() as db:
        try:
            files = search_files(db, keywords)
            return [file.to_dict() for file in files]
        except OperationalError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.put("/files/{file_id}/tags/", response_model=FileMetadataResponse)
async def update_file_custom_tags(file_id: int, request: UpdateTagsRequest):
    with get_db() as db:
        try:
            updated_file = update_file_tags(db, file_id, request.tags, request.overwrite)
            return updated_file.to_dict()
        except NoResultFound:
            raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")
        except OperationalError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.delete("/files/{file_id}", status_code=204) # 204 No Content for successful deletion
async def delete_file_metadata_api(file_id: int):
    with get_db() as db:
        try:
            # You need to implement delete_file_metadata in metadata_manager.py
            # This function should return True on success, False/raise error on failure
            success = delete_file_metadata(db, file_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found or could not be deleted.")
            return # FastAPI automatically sends 204
        except NoResultFound: # Handle if delete_file_metadata raises this
            raise HTTPException(status_code=404, detail=f"File with ID {file_id} not found.")
        except OperationalError as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")