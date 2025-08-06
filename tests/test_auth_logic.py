"""
Logic tests for authentication without UI dependencies.
"""

import pytest
from app.services import AuthService
from app.models import UserCreate, UserLogin
from app.database import reset_db


@pytest.fixture()
def new_db():
    """Reset database for each test."""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def sample_user(new_db):
    """Create a sample user for testing."""
    user_data = UserCreate(username="testuser", password="test123", full_name="Test User", email="test@example.com")
    user = AuthService.create_user(user_data)
    assert user is not None
    return user


class TestAuthLogic:
    """Test authentication logic without session dependencies."""

    def test_user_creation_and_retrieval(self, sample_user):
        """Test basic user creation and retrieval."""
        assert sample_user.username == "testuser"
        assert sample_user.full_name == "Test User"
        assert sample_user.email == "test@example.com"
        assert sample_user.is_active

        # Test retrieval by ID
        if sample_user.id is not None:
            retrieved_user = AuthService.get_user_by_id(sample_user.id)
            assert retrieved_user is not None
            assert retrieved_user.username == sample_user.username

    def test_authentication_success(self, sample_user):
        """Test successful authentication."""
        login_data = UserLogin(username="testuser", password="test123")
        authenticated_user = AuthService.authenticate_user(login_data)

        assert authenticated_user is not None
        assert authenticated_user.id == sample_user.id
        assert authenticated_user.username == "testuser"
        assert authenticated_user.last_login is not None

    def test_authentication_failure(self, sample_user):
        """Test authentication failures."""
        # Wrong password
        login_data = UserLogin(username="testuser", password="wrong")
        user = AuthService.authenticate_user(login_data)
        assert user is None

        # Nonexistent user
        login_data = UserLogin(username="nonexistent", password="test123")
        user = AuthService.authenticate_user(login_data)
        assert user is None

    def test_password_hashing_security(self):
        """Test password hashing security."""
        password = "mysecurepassword"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

        # Both should verify correctly
        assert AuthService.verify_password(password, hash1)
        assert AuthService.verify_password(password, hash2)

        # Wrong password should not verify
        assert not AuthService.verify_password("wrongpassword", hash1)
        assert not AuthService.verify_password("wrongpassword", hash2)

    def test_user_response_conversion(self, sample_user):
        """Test conversion to user response."""
        response = AuthService.to_user_response(sample_user)

        assert response.id == sample_user.id
        assert response.username == "testuser"
        assert response.full_name == "Test User"
        assert response.email == "test@example.com"
        assert response.is_active
        assert isinstance(response.created_at, str)  # Should be ISO string

    def test_duplicate_username_prevention(self, new_db):
        """Test that duplicate usernames are prevented."""
        user_data1 = UserCreate(username="duplicate", password="password1", full_name="User One")
        user_data2 = UserCreate(username="duplicate", password="password2", full_name="User Two")

        # First user should be created successfully
        user1 = AuthService.create_user(user_data1)
        assert user1 is not None

        # Second user with same username should fail
        user2 = AuthService.create_user(user_data2)
        assert user2 is None

    def test_inactive_user_authentication(self, new_db):
        """Test that inactive users cannot authenticate."""
        # Create user
        user_data = UserCreate(username="testuser", password="test123", full_name="Test User")
        user = AuthService.create_user(user_data)
        assert user is not None

        # Deactivate user
        user.is_active = False
        from app.database import get_session

        with get_session() as session:
            session.add(user)
            session.commit()

        # Authentication should fail for inactive user
        login_data = UserLogin(username="testuser", password="test123")
        auth_user = AuthService.authenticate_user(login_data)
        assert auth_user is None
