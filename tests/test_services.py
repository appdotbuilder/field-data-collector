"""
Tests for service layer functions.
"""

import pytest
from app.services import AuthService, PhotoService, DataCollectionService
from app.models import UserCreate, UserLogin, DataCollectionCreate
from app.database import reset_db


@pytest.fixture()
def new_db():
    """Reset database for each test."""
    reset_db()
    yield
    reset_db()


class TestAuthService:
    """Test authentication service functionality."""

    def test_hash_password(self):
        """Test password hashing functionality."""
        password = "test123"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        assert "$" in hash1  # Should contain salt separator
        assert len(hash1.split("$")) == 2  # Should have salt and hash

    def test_verify_password(self):
        """Test password verification."""
        password = "test123"
        password_hash = AuthService.hash_password(password)

        # Correct password should verify
        assert AuthService.verify_password(password, password_hash)

        # Wrong password should not verify
        assert not AuthService.verify_password("wrong", password_hash)

        # Invalid hash format should not verify
        assert not AuthService.verify_password(password, "invalid_hash")

    def test_create_user_success(self, new_db):
        """Test successful user creation."""
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User", email="test@example.com")

        user = AuthService.create_user(user_data)

        assert user is not None
        assert user.id is not None
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.email == "test@example.com"
        assert user.is_active
        assert user.password_hash != "test123"  # Should be hashed

    def test_create_user_duplicate_username(self, new_db):
        """Test user creation with duplicate username."""
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User", email="test@example.com")

        # Create first user
        user1 = AuthService.create_user(user_data)
        assert user1 is not None

        # Try to create second user with same username
        user2 = AuthService.create_user(user_data)
        assert user2 is None

    def test_authenticate_user_success(self, new_db):
        """Test successful user authentication."""
        # Create user
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        created_user = AuthService.create_user(user_data)
        assert created_user is not None

        # Authenticate user
        login_data = UserLogin(username="testuser", password="test123")
        authenticated_user = AuthService.authenticate_user(login_data)

        assert authenticated_user is not None
        assert authenticated_user.id == created_user.id
        assert authenticated_user.username == "testuser"
        assert authenticated_user.last_login is not None

    def test_authenticate_user_wrong_password(self, new_db):
        """Test authentication with wrong password."""
        # Create user
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        AuthService.create_user(user_data)

        # Try wrong password
        login_data = UserLogin(username="testuser", password="wrong")
        user = AuthService.authenticate_user(login_data)

        assert user is None

    def test_authenticate_user_nonexistent(self, new_db):
        """Test authentication with nonexistent username."""
        login_data = UserLogin(username="nonexistent", password="test123")
        user = AuthService.authenticate_user(login_data)

        assert user is None

    def test_authenticate_user_inactive(self, new_db):
        """Test authentication with inactive user."""
        # Create user and deactivate
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        user = AuthService.create_user(user_data)
        assert user is not None

        # Manually deactivate user
        user.is_active = False
        from app.database import get_session

        with get_session() as session:
            session.add(user)
            session.commit()

        # Try to authenticate
        login_data = UserLogin(username="testuser", password="test123")
        auth_user = AuthService.authenticate_user(login_data)

        assert auth_user is None

    def test_get_user_by_id(self, new_db):
        """Test getting user by ID."""
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        created_user = AuthService.create_user(user_data)
        assert created_user is not None
        assert created_user.id is not None

        retrieved_user = AuthService.get_user_by_id(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == "testuser"

        # Test nonexistent ID
        nonexistent_user = AuthService.get_user_by_id(99999)
        assert nonexistent_user is None

    def test_to_user_response(self, new_db):
        """Test user response conversion."""
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        user = AuthService.create_user(user_data)
        assert user is not None

        response = AuthService.to_user_response(user)

        assert response.id == user.id
        assert response.username == "testuser"
        assert response.full_name == "Test User"
        assert response.is_active
        assert isinstance(response.created_at, str)  # Should be ISO format


class TestPhotoService:
    """Test photo service functionality."""

    def test_is_allowed_file(self):
        """Test file extension validation."""
        # Allowed extensions
        assert PhotoService.is_allowed_file("test.jpg")
        assert PhotoService.is_allowed_file("test.jpeg")
        assert PhotoService.is_allowed_file("test.png")
        assert PhotoService.is_allowed_file("test.gif")
        assert PhotoService.is_allowed_file("test.webp")
        assert PhotoService.is_allowed_file("TEST.JPG")  # Case insensitive

        # Not allowed extensions
        assert not PhotoService.is_allowed_file("test.txt")
        assert not PhotoService.is_allowed_file("test.pdf")
        assert not PhotoService.is_allowed_file("test.doc")
        assert not PhotoService.is_allowed_file("test")  # No extension

    def test_generate_unique_filename(self):
        """Test unique filename generation."""
        filename1 = PhotoService.generate_unique_filename("test.jpg")
        filename2 = PhotoService.generate_unique_filename("test.jpg")

        # Should be different
        assert filename1 != filename2

        # Should preserve extension
        assert filename1.endswith(".jpg")
        assert filename2.endswith(".jpg")

        # Should handle different extensions
        png_filename = PhotoService.generate_unique_filename("image.PNG")
        assert png_filename.endswith(".png")  # Should be lowercase

    def test_save_photo_success(self, new_db, tmp_path):
        """Test successful photo saving."""
        from pathlib import Path

        # Mock upload directory to temp path
        original_upload_dir = PhotoService.UPLOAD_DIR
        PhotoService.UPLOAD_DIR = str(tmp_path / "uploads")

        try:
            file_content = b"fake image data"
            original_filename = "test.jpg"
            mime_type = "image/jpeg"

            photo = PhotoService.save_photo(file_content, original_filename, mime_type)

            assert photo is not None
            assert photo.id is not None
            assert photo.original_filename == original_filename
            assert photo.mime_type == mime_type
            assert photo.file_size == len(file_content)

            # Check file was actually saved
            file_path = Path(photo.file_path)
            assert file_path.exists()

            saved_content = file_path.read_bytes()
            assert saved_content == file_content

        finally:
            PhotoService.UPLOAD_DIR = original_upload_dir

    def test_save_photo_invalid_extension(self, new_db):
        """Test photo saving with invalid extension."""
        file_content = b"fake data"
        photo = PhotoService.save_photo(file_content, "test.txt", "text/plain")
        assert photo is None

    def test_save_photo_too_large(self, new_db):
        """Test photo saving with file too large."""
        large_content = b"x" * (PhotoService.MAX_FILE_SIZE + 1)
        photo = PhotoService.save_photo(large_content, "test.jpg", "image/jpeg")
        assert photo is None

    def test_get_photo_by_id(self, new_db, tmp_path):
        """Test getting photo by ID."""

        # Mock upload directory
        original_upload_dir = PhotoService.UPLOAD_DIR
        PhotoService.UPLOAD_DIR = str(tmp_path / "uploads")

        try:
            # Save a photo first
            file_content = b"fake image data"
            photo = PhotoService.save_photo(file_content, "test.jpg", "image/jpeg")
            assert photo is not None
            assert photo.id is not None

            # Retrieve photo by ID
            retrieved_photo = PhotoService.get_photo_by_id(photo.id)
            assert retrieved_photo is not None
            assert retrieved_photo.id == photo.id
            assert retrieved_photo.filename == photo.filename

            # Test nonexistent ID
            nonexistent_photo = PhotoService.get_photo_by_id(99999)
            assert nonexistent_photo is None

        finally:
            PhotoService.UPLOAD_DIR = original_upload_dir


class TestDataCollectionService:
    """Test data collection service functionality."""

    def test_create_collection_success(self, new_db):
        """Test successful data collection creation."""
        # Create user first
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        user = AuthService.create_user(user_data)
        assert user is not None
        assert user.id is not None

        # Create data collection
        collection_data = DataCollectionCreate(
            customer_name="John Doe",
            description="Test customer visit",
            location_data={"lat": 40.7128, "lng": -74.0060},
            device_info={"device": "mobile"},
        )

        collection = DataCollectionService.create_collection(user.id, collection_data)

        assert collection is not None
        assert collection.id is not None
        assert collection.customer_name == "John Doe"
        assert collection.description == "Test customer visit"
        assert collection.user_id == user.id
        assert collection.photo_id is None
        assert collection.location_data == {"lat": 40.7128, "lng": -74.0060}
        assert not collection.is_synchronized

    def test_create_collection_with_photo(self, new_db, tmp_path):
        """Test data collection creation with photo."""

        # Mock upload directory
        original_upload_dir = PhotoService.UPLOAD_DIR
        PhotoService.UPLOAD_DIR = str(tmp_path / "uploads")

        try:
            # Create user
            user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
            user = AuthService.create_user(user_data)
            assert user is not None
            assert user.id is not None

            # Create photo
            photo = PhotoService.save_photo(b"fake image", "test.jpg", "image/jpeg")
            assert photo is not None
            assert photo.id is not None

            # Create data collection with photo
            collection_data = DataCollectionCreate(
                customer_name="Jane Doe", description="Customer with photo", photo_id=photo.id
            )

            collection = DataCollectionService.create_collection(user.id, collection_data)

            assert collection is not None
            assert collection.photo_id == photo.id

        finally:
            PhotoService.UPLOAD_DIR = original_upload_dir

    def test_create_collection_invalid_user(self, new_db):
        """Test data collection creation with invalid user."""
        collection_data = DataCollectionCreate(customer_name="John Doe", description="Test")

        collection = DataCollectionService.create_collection(99999, collection_data)
        assert collection is None

    def test_create_collection_invalid_photo(self, new_db):
        """Test data collection creation with invalid photo ID."""
        # Create user
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        user = AuthService.create_user(user_data)
        assert user is not None
        assert user.id is not None

        # Try to create collection with nonexistent photo
        collection_data = DataCollectionCreate(customer_name="John Doe", description="Test", photo_id=99999)

        collection = DataCollectionService.create_collection(user.id, collection_data)
        assert collection is None

    def test_get_collections_by_user(self, new_db):
        """Test getting collections for a user."""
        # Create user
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        user = AuthService.create_user(user_data)
        assert user is not None
        assert user.id is not None

        # Create multiple collections
        for i in range(3):
            collection_data = DataCollectionCreate(customer_name=f"Customer {i}", description=f"Description {i}")
            collection = DataCollectionService.create_collection(user.id, collection_data)
            assert collection is not None

        # Get collections
        collections = DataCollectionService.get_collections_by_user(user.id)
        assert len(collections) == 3

        # Should be ordered by submission_date desc
        assert collections[0].submission_date >= collections[1].submission_date
        assert collections[1].submission_date >= collections[2].submission_date

    def test_get_dashboard_stats(self, new_db):
        """Test dashboard statistics calculation."""
        # Create user
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        user = AuthService.create_user(user_data)
        assert user is not None
        assert user.id is not None

        # Initially should have zero stats
        stats = DataCollectionService.get_dashboard_stats(user.id)
        assert stats.total_collections == 0
        assert stats.collections_today == 0
        assert stats.collections_this_week == 0
        assert stats.collections_this_month == 0
        assert stats.pending_sync == 0
        assert stats.last_submission is None

        # Create some collections
        for i in range(5):
            collection_data = DataCollectionCreate(customer_name=f"Customer {i}", description=f"Description {i}")
            collection = DataCollectionService.create_collection(user.id, collection_data)
            assert collection is not None

        # Check updated stats
        stats = DataCollectionService.get_dashboard_stats(user.id)
        assert stats.total_collections == 5
        assert stats.collections_today == 5  # All created today
        assert stats.collections_this_week == 5
        assert stats.collections_this_month == 5
        assert stats.pending_sync == 5  # All unsynchronized
        assert stats.last_submission is not None
