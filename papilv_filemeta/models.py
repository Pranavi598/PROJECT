# from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
# # from sqlalchemy.dialects.postgresql import JSONB # <-- REMOVE THIS LINE IF USING SQLITE
# from sqlalchemy.orm import relationship
# from datetime import datetime
# import json
# from .database import Base

# # If using SQLite, you should import `JSON` from `sqlalchemy.types`
# # or `sqlite.JSON` from `sqlalchemy.dialects.sqlite` if you want specific SQLite JSON features.
# # For simplicity, if your SQLAlchemy version is recent enough (1.3+ with SQLite JSON1 extension),
# # Column(JSON) might just work. If not, use `String` and manually dump/load.
# from sqlalchemy.types import JSON # <-- ADD THIS FOR GENERIC JSON TYPE (works for SQLite)
# # from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON # Alternative for explicit SQLite JSON


# # --- User Model ---
# class User(Base):
#     __tablename__ = 'user'
#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String(255), unique=True, index=True, nullable=False)
#     hashed_password = Column(String(255), nullable=False)
#     role = Column(String(50), default="user", nullable=False)
#     created_at = Column(DateTime(timezone=True), default=datetime.now)
#     updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
#     files = relationship("File", back_populates="owner_rel", cascade="all, delete-orphan")

#     def __repr__(self):
#         return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

# # --- File Model ---
# class File(Base):
#     __tablename__ = 'file'

#     id = Column(Integer, primary_key=True, index=True)
#     filename = Column(String(255), nullable=False)
#     filepath = Column(Text, nullable=False, unique=True)

#     owner = Column(Integer, ForeignKey('user.id'), nullable=True)
#     owner_rel = relationship("User", back_populates="files")

#     created_by = Column(String(255), nullable=False)
#     created_at = Column(DateTime(timezone=True), default=datetime.now, nullable=False)
#     updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now, nullable=False)
    
#     # --- CHANGE THIS LINE FOR SQLITE ---
#     inferred_tags = Column(JSON, default=lambda: {}, nullable=False) # Use generic JSON for SQLite
#     # If JSON type gives issues with older SQLite:
#     # inferred_tags = Column(Text, default=lambda: json.dumps({}), nullable=False) # Store as Text, handle JSON conversion manually

#     tags = relationship("Tag", back_populates="file", cascade="all, delete-orphan")

#     __table_args__ = (UniqueConstraint('filename', 'filepath', name='_filename_filepath_uc'),) # Added a unique constraint for filename/filepath pair

#     def __repr__(self):
#         return f"<File(id={self.id}, filename='{self.filename}', filepath='{self.filepath}', owner_id={self.owner})>"

#     def to_dict(self):
#         return {
#             "id": self.id,
#             "filename": self.filename,
#             "filepath": self.filepath,
#             "owner": self.owner, # This will be the owner ID (int)
#             "created_by": self.created_by,
#             "created_at": self.created_at.isoformat() if self.created_at else None,
#             "updated_at": self.updated_at.isoformat() if self.updated_at else None,
#             "inferred_tags": self.inferred_tags if self.inferred_tags is not None else {},
#             "tags": [tag.to_dict() for tag in self.tags] if self.tags else []
#         }

# # --- Tag Model ---
# class Tag(Base):
#     __tablename__ = 'tag'

#     id = Column(Integer, primary_key=True, index=True)
#     file_id = Column(Integer, ForeignKey('file.id', ondelete='CASCADE'), nullable=False)
#     key = Column(String(255), nullable=False)
#     value = Column(Text, nullable=False)
#     value_type = Column(String(50), nullable=False)

#     file = relationship("File", back_populates="tags")

#     __table_args__ = (UniqueConstraint('file_id', 'key', name='_file_key_uc'),)

#     def __repr__(self):
#         return f"<Tag(id={self.id}, file_id={self.file_id}, key='{self.key}', value='{self.value}', type='{self.value_type}')>"

#     def get_typed_value(self):
#         if self.value_type == 'int':
#             try:
#                 return int(self.value)
#             except ValueError:
#                 return None
#         elif self.value_type == 'float':
#             try:
#                 return float(self.value)
#             except ValueError:
#                 return None
#         elif self.value_type == 'bool':
#             return self.value.lower() == 'true'
#         elif self.value_type == 'NoneType':
#             return None
#         return self.value

#     def to_dict(self):
#         return {
#             "key": self.key,
#             "value": self.value,
#             "value_type": self.value_type
#         }


# 
# filemeta/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json # For handling JSONB default values

Base = declarative_base()

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(Text, nullable=False)
    owner = Column(String(255))
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    inferred_tags = Column(JSONB, default=lambda: json.dumps({}), nullable=False) # Store as JSONB

    tags = relationship("Tag", back_populates="file", cascade="all, delete-orphan") # ADD THIS CASCADE

    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', filepath='{self.filepath}')>"

    def to_dict(self):
        """Converts File object to a dictionary for display."""
        inferred = self.inferred_tags if self.inferred_tags else {}
        # Ensure inferred_tags is a dict, not a string if it was loaded directly from JSONB
        if isinstance(inferred, str):
            try:
                inferred = json.loads(inferred)
            except json.JSONDecodeError:
                inferred = {} # Fallback

        custom_tags = {tag.key: tag.get_typed_value() for tag in self.tags}
        return {
            "ID": self.id,
            "Filename": self.filename,
            "Filepath": self.filepath,
            "Owner": self.owner,
            "Created By": self.created_by,
            "Created At": self.created_at.isoformat() if self.created_at else None,
            "Updated At": self.updated_at.isoformat() if self.updated_at else None,
            "Inferred Tags": inferred,
            "Custom Tags": custom_tags
        }

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id', ondelete='CASCADE'), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), nullable=False) # Store original Python type

    file = relationship("File", back_populates="tags")

    def __repr__(self):
        return f"<Tag(id={self.id}, file_id={self.file_id}, key='{self.key}', value='{self.value}', type='{self.value_type}')>"

    def get_typed_value(self):
        """Converts the stored string value back to its original Python type."""
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() == 'true' # Handle 'True' or 'true'
        elif self.value_type == 'NoneType':
            return None
        # Add more types as needed (e.g., list, dict if you allow complex tag values)
        return self.value # Default to string