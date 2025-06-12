# # schemas.py
# from typing import Optional, Dict, List, Any, Union
# from datetime import datetime
# from pydantic import BaseModel, Field

# # --- Auth Schemas ---
# class UserBase(BaseModel):
#     username: str

# class UserCreate(UserBase):
#     password: str

# class User(UserBase):
#     id: int
#     hashed_password: str
#     role: str # "admin" or "user"

#     class Config:
#         orm_mode = True # Enable ORM mode for Pydantic to read directly from SQLAlchemy models

# class UserResponse(BaseModel):
#     id: int
#     username: str
#     role: str

#     class Config:
#         orm_mode = True

# class Token(BaseModel):
#     access_token: str
#     token_type: str

# class TokenData(BaseModel):
#     username: Union[str, None] = None
#     role: Union[str, None] = None

# # --- File Metadata Schemas ---
# class FileAddRequest(BaseModel):
#     filepath: str
#     tags: Dict[str, Any] = Field(default_factory=dict, description="Custom tags in KEY=VALUE format.")

# class FileUpdateRequest(BaseModel):
#     tags_to_add_modify: Optional[Dict[str, Any]] = Field(None, description="Dictionary of tags to add or modify (key: value).")
#     tags_to_remove: Optional[List[str]] = Field(None, description="List of tag keys to remove.")
#     new_filepath: Optional[str] = Field(None, description="New file path to update.")
#     overwrite: bool = Field(False, description="If true, all existing custom tags will be deleted BEFORE new tags are added.")

# class FileResponse(BaseModel):
#     # This maps directly to the File.to_dict() output
#     ID: int = Field(..., alias="ID")
#     Filename: str = Field(..., alias="Filename")
#     Filepath: str = Field(..., alias="Filepath")
#     Owner: Optional[str] = Field(None, alias="Owner")
#     CreatedBy: Optional[str] = Field(None, alias="Created By") # Note alias for spaces
#     CreatedAt: Optional[datetime] = Field(None, alias="Created At")
#     UpdatedAt: Optional[datetime] = Field(None, alias="Updated At") # Corrected back to datetime
#     InferredTags: Dict[str, Any] = Field(..., alias="Inferred Tags")
#     CustomTags: Dict[str, Any] = Field(..., alias="Custom Tags")

#     class Config:
#         orm_mode = True # Enable ORM mode for Pydantic to read directly from SQLAlchemy models
#         allow_population_by_field_name = True # Allow using field names as well as aliases

#     @classmethod
#     def from_orm(cls, obj: Any):
#         """
#         Custom from_orm to handle the to_dict() conversion.
#         """
#         if not hasattr(obj, 'to_dict'):
#             raise TypeError(f"Object of type {type(obj)} does not have a 'to_dict' method.")
        
#         data = obj.to_dict()
        
#         # Parse date strings from to_dict() into datetime objects for Pydantic model
#         if 'Created At' in data and isinstance(data['Created At'], str):
#             try:
#                 data['Created At'] = datetime.fromisoformat(data['Created At'])
#             except ValueError:
#                 data['Created At'] = None
#         if 'Updated At' in data and isinstance(data['Updated At'], str):
#             try:
#                 data['Updated At'] = datetime.fromisoformat(data['Updated At'])
#             except ValueError:
#                 data['Updated At'] = None

#         return cls(**data)


# class SearchQueryParams(BaseModel):
#     keywords: Optional[List[str]] = None
#     size_gt: Optional[str] = None
#     size_lt: Optional[str] = None
#     size_between: Optional[List[str]] = None
#     # NEW: Date/time search parameters
#     created_after: Optional[str] = Field(None, description="Search for files created after this date/time (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS').")
#     created_before: Optional[str] = Field(None, description="Search for files created before this date/time.")
#     modified_after: Optional[str] = Field(None, description="Search for files modified after this date/time.")
#     modified_before: Optional[str] = Field(None, description="Search for files modified before this date/time.")
#     accessed_after: Optional[str] = Field(None, description="Search for files last accessed after this date/time.")
#     accessed_before: Optional[str] = Field(None, description="Search for files last accessed before this date/time.")
#     created_between: Optional[List[str]] = Field(None, min_items=2, max_items=2, description="Search for files created within this date/time range (e.g., ['YYYY-MM-DD', 'YYYY-MM-DD']).")
#     modified_between: Optional[List[str]] = Field(None, min_items=2, max_items=2, description="Search for files modified within this date/time range.")
#     accessed_between: Optional[List[str]] = Field(None, min_items=2, max_items=2, description="Search for files last accessed within this date/time range.")

# schemas.py
from typing import Optional, Dict, List, Any, Union, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

# --- Auth Schemas ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    hashed_password: str
    role: str # "admin" or "user"

    class Config:
        orm_mode = True # Enable ORM mode for Pydantic to read directly from SQLAlchemy models

class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None
    role: Union[str, None] = None

# --- File Metadata Schemas ---
class FileAddRequest(BaseModel):
    filepath: str
    tags: Dict[str, Any] = Field(default_factory=dict, description="Custom tags in KEY=VALUE format.")

class FileUpdateRequest(BaseModel):
    tags_to_add_modify: Optional[Dict[str, Any]] = Field(None, description="Dictionary of tags to add or modify (key: value).")
    tags_to_remove: Optional[List[str]] = Field(None, description="List of tag keys to remove.")
    new_filepath: Optional[str] = Field(None, description="New file path to update.")
    overwrite: bool = Field(False, description="If true, all existing custom tags will be deleted BEFORE new tags are added.")

# NEW: Schema for File Rename Request
class FileRenameRequest(BaseModel):
    new_name: str = Field(..., description="The new filename (e.g., 'report_final.docx').")

# NEW: Schema for Tag response (for list_and_search_tags)
class TagResponse(BaseModel):
    key: str
    value: str
    value_type: str

    class Config:
        orm_mode = True

# NEW: Schema for unique tag key-value pair when 'unique' is True
class UniqueTagKeyValuePair(BaseModel):
    key: str
    value: str # Value can be string for unique(key, value) pairs

# NEW: Schema for query parameters for list_and_search_tags
class TagListSearchQueryParams(BaseModel):
    unique: bool = Field(False, description="If True, returns unique tag keys or unique key-value pairs.")
    sort_by: Optional[str] = Field(None, description="Sort results by 'key' or 'value'.")
    sort_order: str = Field('asc', description="Sort order: 'asc' or 'desc'.")
    limit: Optional[int] = Field(None, gt=0, description="Maximum number of results to return.")
    offset: int = Field(0, ge=0, description="Number of results to skip.")
    keywords: Optional[List[str]] = Field(None, description="Keywords to search for in tag keys or values.")

# NEW: Schema for File Validation Request
class FileValidationRequest(BaseModel):
    check_all: bool = Field(False, description="If True, validates all records. 'criteria' will be ignored.")
    criteria: Optional[Dict[str, Any]] = Field(None, description="Dictionary of File column criteria (e.g., {'id': 1, 'filename': 'report.pdf'}).")
    tag_key: Optional[str] = Field(None, description="Key of a tag to check for existence.")
    tag_value: Optional[str] = Field(None, description="Specific value for the tag_key to check.")

# NEW: Schema for File Validation Result
class FileValidationResult(BaseModel):
    id: int
    filename: str
    filepath: str
    disk_exists: bool
    tag_status: Optional[str] = None


class FileResponse(BaseModel):
    # This maps directly to the File.to_dict() output
    ID: int = Field(..., alias="ID")
    Filename: str = Field(..., alias="Filename")
    Filepath: str = Field(..., alias="Filepath")
    Owner: Optional[str] = Field(None, alias="Owner")
    CreatedBy: Optional[str] = Field(None, alias="Created By") # Note alias for spaces
    CreatedAt: Optional[datetime] = Field(None, alias="Created At")
    UpdatedAt: Optional[datetime] = Field(None, alias="Updated At") # Corrected back to datetime
    InferredTags: Dict[str, Any] = Field(..., alias="Inferred Tags")
    CustomTags: Dict[str, Any] = Field(..., alias="Custom Tags")

    class Config:
        orm_mode = True # Enable ORM mode for Pydantic to read directly from SQLAlchemy models
        allow_population_by_field_name = True # Allow using field names as well as aliases

    @classmethod
    def from_orm(cls, obj: Any):
        """
        Custom from_orm to handle the to_dict() conversion.
        """
        if not hasattr(obj, 'to_dict'):
            raise TypeError(f"Object of type {type(obj)} does not have a 'to_dict' method.")
        
        data = obj.to_dict()
        
        # Parse date strings from to_dict() into datetime objects for Pydantic model
        if 'Created At' in data and isinstance(data['Created At'], str):
            try:
                data['Created At'] = datetime.fromisoformat(data['Created At'])
            except ValueError:
                data['Created At'] = None
        if 'Updated At' in data and isinstance(data['Updated At'], str):
            try:
                data['Updated At'] = datetime.fromisoformat(data['Updated At'])
            except ValueError:
                data['Updated At'] = None

        return cls(**data)


class SearchQueryParams(BaseModel):
    keywords: Optional[List[str]] = None
    size_gt: Optional[str] = None
    size_lt: Optional[str] = None
    size_between: Optional[List[str]] = None
    created_after: Optional[str] = Field(None, description="Search for files created after this date/time (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS').")
    created_before: Optional[str] = Field(None, description="Search for files created before this date/time.")
    modified_after: Optional[str] = Field(None, description="Search for files modified after this date/time.")
    modified_before: Optional[str] = Field(None, description="Search for files modified before this date/time.")
    accessed_after: Optional[str] = Field(None, description="Search for files last accessed after this date/time.")
    accessed_before: Optional[str] = Field(None, description="Search for files last accessed before this date/time.")
    created_between: Optional[List[str]] = Field(None, min_items=2, max_items=2, description="Search for files created within this date/time range (e.g., ['YYYY-MM-DD', 'YYYY-MM-DD']).")
    modified_between: Optional[List[str]] = Field(None, min_items=2, max_items=2, description="Search for files modified within this date/time range.")
    accessed_between: Optional[List[str]] = Field(None, min_items=2, max_items=2, description="Search for files last accessed within this date/time range.")

