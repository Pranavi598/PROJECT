# filemeta/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import json 

Base = declarative_base()

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, unique=True, index=True, nullable=False)
    owner = Column(String, nullable=False) # Storing user ID as string for simplicity with current User model
    created_by = Column(String, nullable=False) # Could reference user ID if a users table is made
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    inferred_tags = Column(JSON, default={}) # Stores automatically inferred metadata

    tags = relationship("Tag", back_populates="file", cascade="all, delete-orphan")

    def to_dict(self):
        """Converts the File object and its associated tags to a dictionary."""
        inferred = self.inferred_tags if isinstance(self.inferred_tags, dict) else {}
        # Ensure inferred_tags is a dictionary
        try:
            inferred = json.loads(self.inferred_tags) if isinstance(self.inferred_tags, str) else self.inferred_tags
        except json.JSONDecodeError:
            inferred = {} # Fallback if JSON is malformed

        custom_tags_dict = {tag.key: self._convert_tag_value(tag.value, tag.value_type) for tag in self.tags}

        return {
            "ID": self.id,
            "Filename": self.filename,
            "Filepath": self.filepath,
            "Owner": self.owner,
            "Created By": self.created_by,
            "Created At": self.created_at.isoformat() if self.created_at else None,
            "Updated At": self.updated_at.isoformat() if self.updated_at else None,
            "Inferred Tags": inferred,
            "Custom Tags": custom_tags_dict,
        }

    def _convert_tag_value(self, value, value_type):
        """Converts stored string value back to its original type."""
        if value_type == 'integer':
            return int(value)
        elif value_type == 'float':
            return float(value)
        elif value_type == 'boolean':
            return value.lower() == 'true'
        elif value_type == 'list':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [v.strip() for v in value.strip('[]').split(',') if v.strip()] # Fallback
        elif value_type == 'dict':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {} # Fallback
        return value # Default to string

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False) # Store all values as text/string
    value_type = Column(String, nullable=False) # e.g., 'string', 'integer', 'float', 'boolean', 'list', 'dict'

    # Ensure uniqueness of key within the scope of a file_id
    __table_args__ = (UniqueConstraint('file_id', 'key', name='_file_key_uc'),)

    file = relationship("File", back_populates="tags")


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False) # e.g., "admin", "user"
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def to_dict(self):
        """Converts the User object to a dictionary (useful for responses)."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }