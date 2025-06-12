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
# filemeta/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(Text, nullable=False, unique=True) # Ensure filepath is unique
    owner = Column(String(255))
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    inferred_tags = Column(JSONB, default=lambda: json.dumps({}), nullable=False) # Store as JSONB

    tags = relationship("Tag", back_populates="file", cascade="all, delete-orphan") 

    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', filepath='{self.filepath}')>"

    def to_dict(self):
        """Converts File object to a dictionary for display."""
        inferred = self.inferred_tags if self.inferred_tags else {}
        # Ensure inferred_tags is a dict, not a string if it was loaded directly from JSONB
        # This check is mostly for older SQLAlchemy versions or if data was inserted manually as string
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
            try:
                return int(self.value)
            except ValueError:
                return self.value # Fallback if conversion fails
        elif self.value_type == 'float':
            try:
                return float(self.value)
            except ValueError:
                return self.value # Fallback
        elif self.value_type == 'bool':
            # Handle 'True' or 'true' and 'False' or 'false'
            return self.value.lower() == 'true' 
        elif self.value_type == 'NoneType':
            return None
        # Add more types as needed (e.g., list, dict if you allow complex tag values)
        return self.value # Default to string if type not recognized or conversion fails

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False) # True for admin, False for regular user

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"

    def to_dict(self, include_password=False):
        """Converts User object to a dictionary for display."""
        user_data = {
            "id": self.id,
            "username": self.username,
            "is_admin": self.is_admin
        }
        if include_password:
            user_data["hashed_password"] = self.hashed_password
        return user_data

