# filemeta/api/schemas.py
import json
from pydantic import BaseModel, Field, field_validator # Use field_validator for Pydantic v2
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Auxiliary Schemas ---

class TagResponse(BaseModel):
    """Schema for returning individual tags."""
    key: str
    value: str # Tag value is stored as string in DB
    value_type: str # e.g., "string", "integer", "boolean", "float"

    class Config:
        from_attributes = True # Enable ORM mode for Tag model


# --- File Metadata Schemas ---

class FileCreate(BaseModel):
    """Schema for creating a new file metadata record."""
    filepath: str = Field(..., example="/server/data/document.pdf")
    # custom_tags should be a dict where value can be anything, handled by parse_tag_value in metadata_manager
    custom_tags: Optional[Dict[str, Any]] = {} 

class FileUpdate(BaseModel):
    """Schema for updating file metadata (tags and/or filepath)."""
    tags_to_add_modify: Optional[Dict[str, Any]] = None # Values can be anything, will be parsed
    tags_to_remove: Optional[List[str]] = None
    new_filepath: Optional[str] = None
    overwrite_existing: bool = False # If true, replaces ALL existing custom tags


class FileResponse(BaseModel):
    """Schema for returning file metadata records."""
    id: int = Field(..., alias="ID") # Map DB 'id' to API 'ID'
    filename: str = Field(..., alias="Filename")
    filepath: str = Field(..., alias="Filepath")
    owner: str = Field(..., alias="Owner") # Assuming File.owner is an INTEGER foreign key to User.id
    created_by: str = Field(..., alias="Created By")
    created_at: datetime = Field(..., alias="Created At")
    updated_at: datetime = Field(..., alias="Updated At")
    
    # Inferred tags are stored as JSONB (Python dict)
    inferred_tags: Dict[str, Any] = Field(..., alias="Inferred Tags")
    
    # Tags are a list of TagResponse objects from the relationship
    tags: List[TagResponse] = Field(default_factory=list, alias="Custom Tags") 

    # If you still want a validator for inferred_tags in case of old data or bad input
    @field_validator('inferred_tags', mode='before')
    @classmethod
    def parse_inferred_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {} # Or raise an error
        return v


    class Config:
        from_attributes = True # Pydantic v2: Allows mapping from SQLAlchemy models
        populate_by_name = True # Allows aliases like "Created By" to be used in response
        json_dumps = json.dumps # Ensures Dict[str, Any] is properly serialized to JSON


# --- User & Auth Schemas ---
class UserCreateRequest(BaseModel):
    """Schema for creating a new user."""
    username: str
    password: str
    role: Optional[str] = 'user' # Default role is 'user'

class UserResponse(BaseModel):
    """Schema for returning user details."""
    id: int
    username: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Enable ORM mode for User model


class Token(BaseModel):
    """Schema for the access token response."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for the data contained within the JWT token."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    user_role: Optional[str] = None
