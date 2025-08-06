"""
Seed data for field data collection application.
Creates demo users and sample data for testing.
"""

import logging
from app.services import AuthService
from app.models import UserCreate, UserLogin

logger = logging.getLogger(__name__)


def create_demo_users() -> None:
    """Create demo users for testing the application."""
    demo_users = [
        UserCreate(username="demo", password="demo123", full_name="Demo User", email="demo@example.com"),
        UserCreate(
            username="fieldworker", password="field123", full_name="Field Worker", email="fieldworker@example.com"
        ),
        UserCreate(
            username="supervisor", password="super123", full_name="Field Supervisor", email="supervisor@example.com"
        ),
    ]

    for user_data in demo_users:
        login_data = UserLogin(username=user_data.username, password=user_data.password)
        existing_user = AuthService.authenticate_user(login_data)

        if existing_user is None:
            user = AuthService.create_user(user_data)
            if user:
                logger.info(f"Created demo user: {user.username} ({user.full_name})")
            else:
                logger.warning(f"Failed to create user: {user_data.username}")
        else:
            logger.info(f"Demo user already exists: {user_data.username}")


def seed_database() -> None:
    """Seed the database with initial data."""
    logger.info("Seeding database with demo data...")
    create_demo_users()
    logger.info("Database seeding completed!")
