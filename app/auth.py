"""
Authentication module for field data collection application.
Handles user login, session management, and route protection.
"""

from typing import Optional
from nicegui import ui, app
from app.services import AuthService
from app.models import UserLogin, User


class SessionManager:
    """Manages user authentication sessions."""

    @staticmethod
    def login_user(user: User) -> None:
        """Store user information in session storage."""
        if user.id is None:
            raise ValueError("User ID cannot be None")

        app.storage.user["user_id"] = user.id
        app.storage.user["username"] = user.username
        app.storage.user["full_name"] = user.full_name
        app.storage.user["is_authenticated"] = True

    @staticmethod
    def logout_user() -> None:
        """Clear user session data."""
        app.storage.user.clear()

    @staticmethod
    def get_current_user() -> Optional[User]:
        """Get the currently authenticated user."""
        if not app.storage.user.get("is_authenticated"):
            return None

        user_id = app.storage.user.get("user_id")
        if user_id is None:
            return None

        return AuthService.get_user_by_id(user_id)

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is currently authenticated."""
        return bool(app.storage.user.get("is_authenticated", False))

    @staticmethod
    def require_authentication() -> Optional[User]:
        """Require authentication and return user or redirect to login."""
        user = SessionManager.get_current_user()
        if user is None:
            ui.navigate.to("/login")
            return None
        return user


def create_login_form() -> None:
    """Create the login form UI."""
    ui.colors(
        primary="#2563eb",
        secondary="#64748b",
        accent="#10b981",
        positive="#10b981",
        negative="#ef4444",
        warning="#f59e0b",
        info="#3b82f6",
    )

    # Add mobile viewport meta tag for responsive design
    ui.add_head_html("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <style>
        body { 
            margin: 0; 
            padding: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        }
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            box-sizing: border-box;
        }
        .login-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
        @media (max-width: 480px) {
            .login-container { padding: 10px; }
            .login-card { border-radius: 12px; }
        }
    </style>
    """)

    with ui.column().classes("login-container w-full"):
        with ui.card().classes("login-card p-8 w-full"):
            # App logo/title
            with ui.column().classes("items-center mb-8"):
                ui.icon("camera_alt", size="3rem").classes("text-primary mb-4")
                ui.label("Field Data Collection").classes("text-2xl font-bold text-gray-800 text-center")
                ui.label("Sign in to your account").classes("text-gray-600 text-center")

            # Login form
            username_input = (
                ui.input(label="Username", placeholder="Enter your username")
                .classes("w-full mb-4")
                .props("outlined dense")
            )

            password_input = (
                ui.input(
                    label="Password", placeholder="Enter your password", password=True, password_toggle_button=True
                )
                .classes("w-full mb-6")
                .props("outlined dense")
            )

            # Login button
            ui.button("Sign In", on_click=lambda: handle_login(username_input.value, password_input.value)).classes(
                "w-full bg-primary text-white py-3 rounded-lg font-semibold hover:bg-primary-600 transition-colors"
            )

            # Error message container
            error_container = ui.column().classes("w-full mt-4 hidden")

            # Demo credentials info
            with ui.expansion("Demo Credentials", icon="info").classes("w-full mt-6 text-sm"):
                ui.label("For testing purposes:").classes("text-gray-600 mb-2")
                ui.label("Username: demo").classes("font-mono text-gray-700")
                ui.label("Password: demo123").classes("font-mono text-gray-700")
                ui.label("Or create a new account by contacting your administrator.").classes(
                    "text-gray-500 mt-2 text-xs"
                )

            def handle_login(username: str, password: str) -> None:
                """Handle login form submission."""
                error_container.classes(remove="hidden")
                error_container.clear()

                if not username or not password:
                    with error_container:
                        ui.label("Please enter both username and password").classes("text-negative text-sm")
                    return

                # Create login data
                login_data = UserLogin(username=username.strip(), password=password)

                # Authenticate user
                user = AuthService.authenticate_user(login_data)

                if user is None:
                    with error_container:
                        ui.label("Invalid username or password").classes("text-negative text-sm")
                    return

                # Login successful
                SessionManager.login_user(user)
                ui.notify(f"Welcome back, {user.full_name}!", type="positive")
                ui.navigate.to("/dashboard")

            # Handle Enter key submission
            username_input.on("keydown.enter", lambda: password_input.run_method("focus"))
            password_input.on("keydown.enter", lambda: handle_login(username_input.value, password_input.value))


def create() -> None:
    """Create authentication routes and components."""

    @ui.page("/login")
    def login_page():
        # Redirect if already authenticated
        if SessionManager.is_authenticated():
            ui.navigate.to("/dashboard")
            return

        create_login_form()

    @ui.page("/logout")
    def logout_page():
        SessionManager.logout_user()
        ui.notify("You have been logged out successfully", type="info")
        ui.navigate.to("/login")
