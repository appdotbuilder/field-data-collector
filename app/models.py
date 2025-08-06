from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any


# Persistent models (stored in database)
class User(SQLModel, table=True):
    """User authentication model for field data collectors."""

    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    full_name: str = Field(max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)

    # Relationships
    data_collections: List["DataCollection"] = Relationship(back_populates="user")


class Photo(SQLModel, table=True):
    """Photo/file storage model for uploaded images."""

    __tablename__ = "photos"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    original_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int = Field(gt=0)  # Size in bytes
    mime_type: str = Field(max_length=100, default="image/jpeg")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional metadata
    photo_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    data_collections: List["DataCollection"] = Relationship(back_populates="photo")


class DataCollection(SQLModel, table=True):
    """Main data collection record for field submissions."""

    __tablename__ = "data_collections"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    submission_date: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Foreign keys
    user_id: int = Field(foreign_key="users.id")
    photo_id: Optional[int] = Field(default=None, foreign_key="photos.id")

    # Additional metadata
    location_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    device_info: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Status tracking
    is_synchronized: bool = Field(default=False)
    sync_error: Optional[str] = Field(default=None, max_length=500)

    # Relationships
    user: User = Relationship(back_populates="data_collections")
    photo: Optional[Photo] = Relationship(back_populates="data_collections")


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    """Schema for creating a new user."""

    username: str = Field(max_length=50)
    password: str = Field(min_length=6, max_length=100)
    full_name: str = Field(max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)


class UserLogin(SQLModel, table=False):
    """Schema for user login credentials."""

    username: str = Field(max_length=50)
    password: str = Field(max_length=100)


class UserResponse(SQLModel, table=False):
    """Schema for user data in API responses."""

    id: int
    username: str
    full_name: str
    email: Optional[str]
    is_active: bool
    created_at: str  # ISO format string
    last_login: Optional[str]  # ISO format string


class PhotoUpload(SQLModel, table=False):
    """Schema for photo upload metadata."""

    filename: str = Field(max_length=255)
    file_size: int = Field(gt=0)
    mime_type: str = Field(max_length=100, default="image/jpeg")
    photo_metadata: Optional[Dict[str, Any]] = Field(default=None)


class PhotoResponse(SQLModel, table=False):
    """Schema for photo data in API responses."""

    id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_at: str  # ISO format string


class DataCollectionCreate(SQLModel, table=False):
    """Schema for creating a new data collection record."""

    customer_name: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    photo_id: Optional[int] = Field(default=None)
    location_data: Optional[Dict[str, Any]] = Field(default=None)
    device_info: Optional[Dict[str, Any]] = Field(default=None)


class DataCollectionUpdate(SQLModel, table=False):
    """Schema for updating a data collection record."""

    customer_name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    photo_id: Optional[int] = Field(default=None)
    location_data: Optional[Dict[str, Any]] = Field(default=None)
    device_info: Optional[Dict[str, Any]] = Field(default=None)
    is_synchronized: Optional[bool] = Field(default=None)
    sync_error: Optional[str] = Field(default=None, max_length=500)


class DataCollectionResponse(SQLModel, table=False):
    """Schema for data collection records in API responses."""

    id: int
    customer_name: str
    description: str
    submission_date: str  # ISO format string
    user_id: int
    photo_id: Optional[int]
    location_data: Optional[Dict[str, Any]]
    device_info: Optional[Dict[str, Any]]
    is_synchronized: bool
    sync_error: Optional[str]


class DataCollectionWithDetails(SQLModel, table=False):
    """Schema for data collection records with user and photo details."""

    id: int
    customer_name: str
    description: str
    submission_date: str  # ISO format string
    is_synchronized: bool
    sync_error: Optional[str]
    user: UserResponse
    photo: Optional[PhotoResponse]


class DashboardStats(SQLModel, table=False):
    """Schema for dashboard statistics."""

    total_collections: int
    collections_today: int
    collections_this_week: int
    collections_this_month: int
    pending_sync: int
    last_submission: Optional[str]  # ISO format string
