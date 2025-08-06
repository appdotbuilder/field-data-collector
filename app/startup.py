from app.database import create_tables
from app.seed_data import seed_database
from nicegui import ui
import app.auth
import app.dashboard


def startup() -> None:
    # Initialize database and seed data
    create_tables()
    seed_database()

    # Set up application theme
    ui.colors(
        primary="#2563eb",
        secondary="#64748b",
        accent="#10b981",
        positive="#10b981",
        negative="#ef4444",
        warning="#f59e0b",
        info="#3b82f6",
    )

    # Register application modules
    app.auth.create()
    app.dashboard.create()
