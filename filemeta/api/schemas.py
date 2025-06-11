# filemeta/api/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- File Metadata Schemas ---
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
    Owner: str # This will be the user ID (as a string)
    Created_By: str = Field(..., alias="Created By")
    Created_At: datetime = Field(..., alias="Created At")
    Updated_At: datetime = Field(..., alias="Updated At")
    Inferred_Tags: Dict[str, Any] = Field(..., alias="Inferred Tags")
    Custom_Tags: Dict[str, Any] = Field(..., alias="Custom Tags")

    class Config:
        # Pydantic v2: from_attributes = True is the modern way to enable ORM mode
        # Pydantic v1: orm_mode = True
        from_attributes = True # This allows Pydantic to read data from SQLAlchemy models
        populate_by_name = True # Allows field aliases (e.g., "Created By") to be populated


# --- User & Auth Schemas ---
class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = 'user' # Default role is 'user'

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Enable ORM mode for User model


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    user_role: Optional[str] = None
