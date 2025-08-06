"""
Service layer for field data collection application.
Handles authentication, photo storage, and data collection operations.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
from sqlmodel import select
from nicegui import ui

from app.database import get_session
from app.models import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    Photo,
    PhotoResponse,
    DataCollection,
    DataCollectionCreate,
    DataCollectionResponse,
    DashboardStats,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for user authentication and session management."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${password_hash}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, hash_value = password_hash.split("$")
            return hashlib.sha256((password + salt).encode()).hexdigest() == hash_value
        except ValueError as e:
            logger.warning(f"Invalid password hash format: {e}")
            return False

    @staticmethod
    def create_user(user_create: UserCreate) -> Optional[User]:
        """Create a new user account."""
        with get_session() as session:
            # Check if username already exists
            existing_user = session.exec(select(User).where(User.username == user_create.username)).first()

            if existing_user:
                return None

            user = User(
                username=user_create.username,
                password_hash=AuthService.hash_password(user_create.password),
                full_name=user_create.full_name,
                email=user_create.email,
            )

            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    @staticmethod
    def authenticate_user(login_data: UserLogin) -> Optional[User]:
        """Authenticate a user with username and password."""
        with get_session() as session:
            user = session.exec(select(User).where(User.username == login_data.username)).first()

            if user is None:
                return None

            if not user.is_active:
                return None

            if not AuthService.verify_password(login_data.password, user.password_hash):
                return None

            # Update last login
            user.last_login = datetime.utcnow()
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID."""
        with get_session() as session:
            return session.get(User, user_id)

    @staticmethod
    def to_user_response(user: User) -> UserResponse:
        """Convert User model to UserResponse schema."""
        return UserResponse(
            id=user.id or 0,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
        )


class PhotoService:
    """Service for photo upload and storage management."""

    UPLOAD_DIR: str = "uploads/photos"
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @classmethod
    def setup_upload_directory(cls) -> None:
        """Ensure upload directory exists."""
        Path(cls.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """Generate a unique filename while preserving extension."""
        file_path = Path(original_filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = secrets.token_hex(8)
        return f"{timestamp}_{unique_id}{file_path.suffix.lower()}"

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        """Check if file has an allowed extension."""
        file_path = Path(filename)
        return file_path.suffix.lower() in PhotoService.ALLOWED_EXTENSIONS

    @staticmethod
    def save_photo(file_content: bytes, original_filename: str, mime_type: str) -> Optional[Photo]:
        """Save uploaded photo to filesystem and database."""
        if not PhotoService.is_allowed_file(original_filename):
            return None

        if len(file_content) > PhotoService.MAX_FILE_SIZE:
            return None

        PhotoService.setup_upload_directory()

        # Generate unique filename
        filename = PhotoService.generate_unique_filename(original_filename)
        file_path = Path(PhotoService.UPLOAD_DIR) / filename

        try:
            # Write file to disk
            file_path.write_bytes(file_content)

            # Save to database
            with get_session() as session:
                photo = Photo(
                    filename=filename,
                    original_filename=original_filename,
                    file_path=str(file_path),
                    file_size=len(file_content),
                    mime_type=mime_type,
                )

                session.add(photo)
                session.commit()
                session.refresh(photo)
                return photo

        except Exception as e:
            # Clean up file if database save fails
            if file_path.exists():
                file_path.unlink()
            logger.error(f"Error saving photo: {str(e)}")
            ui.notify(f"Error saving photo: {str(e)}", type="negative")
            return None

    @staticmethod
    def get_photo_by_id(photo_id: int) -> Optional[Photo]:
        """Get photo by ID."""
        with get_session() as session:
            return session.get(Photo, photo_id)

    @staticmethod
    def to_photo_response(photo: Photo) -> PhotoResponse:
        """Convert Photo model to PhotoResponse schema."""
        return PhotoResponse(
            id=photo.id or 0,
            filename=photo.filename,
            original_filename=photo.original_filename,
            file_path=photo.file_path,
            file_size=photo.file_size,
            mime_type=photo.mime_type,
            uploaded_at=photo.uploaded_at.isoformat(),
        )


class DataCollectionService:
    """Service for managing field data collection records."""

    @staticmethod
    def create_collection(user_id: int, collection_data: DataCollectionCreate) -> Optional[DataCollection]:
        """Create a new data collection record."""
        with get_session() as session:
            # Verify user exists
            user = session.get(User, user_id)
            if user is None:
                return None

            # Verify photo exists if provided
            if collection_data.photo_id is not None:
                photo = session.get(Photo, collection_data.photo_id)
                if photo is None:
                    return None

            collection = DataCollection(
                customer_name=collection_data.customer_name,
                description=collection_data.description,
                user_id=user_id,
                photo_id=collection_data.photo_id,
                location_data=collection_data.location_data,
                device_info=collection_data.device_info,
            )

            session.add(collection)
            session.commit()
            session.refresh(collection)
            return collection

    @staticmethod
    def get_collections_by_user(user_id: int, limit: int = 100) -> List[DataCollection]:
        """Get data collections for a specific user."""
        with get_session() as session:
            from sqlmodel import desc

            statement = (
                select(DataCollection)
                .where(DataCollection.user_id == user_id)
                .order_by(desc(DataCollection.submission_date))
                .limit(limit)
            )
            return list(session.exec(statement).all())

    @staticmethod
    def get_collection_by_id(collection_id: int) -> Optional[DataCollection]:
        """Get data collection by ID."""
        with get_session() as session:
            return session.get(DataCollection, collection_id)

    @staticmethod
    def get_dashboard_stats(user_id: int) -> DashboardStats:
        """Get dashboard statistics for a user."""
        with get_session() as session:
            now = datetime.utcnow()
            today_start = datetime(now.year, now.month, now.day)
            week_start = now - timedelta(days=now.weekday())
            month_start = datetime(now.year, now.month, 1)

            # Total collections
            total_collections = session.exec(select(DataCollection).where(DataCollection.user_id == user_id)).all()

            # Collections today
            collections_today = [c for c in total_collections if c.submission_date >= today_start]

            # Collections this week
            collections_this_week = [c for c in total_collections if c.submission_date >= week_start]

            # Collections this month
            collections_this_month = [c for c in total_collections if c.submission_date >= month_start]

            # Pending sync
            pending_sync = [c for c in total_collections if not c.is_synchronized]

            # Last submission
            last_submission = None
            if total_collections:
                last_collection = max(total_collections, key=lambda c: c.submission_date)
                last_submission = last_collection.submission_date.isoformat()

            return DashboardStats(
                total_collections=len(total_collections),
                collections_today=len(collections_today),
                collections_this_week=len(collections_this_week),
                collections_this_month=len(collections_this_month),
                pending_sync=len(pending_sync),
                last_submission=last_submission,
            )

    @staticmethod
    def to_collection_response(collection: DataCollection) -> DataCollectionResponse:
        """Convert DataCollection model to DataCollectionResponse schema."""
        return DataCollectionResponse(
            id=collection.id or 0,
            customer_name=collection.customer_name,
            description=collection.description,
            submission_date=collection.submission_date.isoformat(),
            user_id=collection.user_id,
            photo_id=collection.photo_id,
            location_data=collection.location_data,
            device_info=collection.device_info,
            is_synchronized=collection.is_synchronized,
            sync_error=collection.sync_error,
        )
