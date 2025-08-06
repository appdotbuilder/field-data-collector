"""
Dashboard module for field data collection.
Main interface for data submission with mobile-friendly photo upload.
"""

import logging
from datetime import datetime
from typing import Optional
from nicegui import ui, events
from app.auth import SessionManager
from app.services import PhotoService, DataCollectionService
from app.models import DataCollectionCreate

logger = logging.getLogger(__name__)


def create_mobile_styles() -> None:
    """Add mobile-optimized CSS styles."""
    ui.add_head_html("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <style>
        body { 
            margin: 0; 
            padding: 0; 
            background: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        }
        .dashboard-container {
            min-height: 100vh;
            padding: 0;
        }
        .header-bar {
            background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
            color: white;
            padding: 16px 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .content-area {
            padding: 20px;
            max-width: 600px;
            margin: 0 auto;
        }
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }
        .form-card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
        }
        .photo-upload-area {
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            background: #f8fafc;
            transition: all 0.3s ease;
        }
        .photo-upload-area:hover {
            border-color: #2563eb;
            background: #eff6ff;
        }
        .photo-preview {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        @media (max-width: 480px) {
            .content-area { padding: 15px; }
            .header-bar { padding: 12px 15px; }
            .form-card { padding: 20px; }
        }
    </style>
    """)


def create_header(user_name: str) -> ui.row:
    """Create the dashboard header with user info and logout."""
    with ui.row().classes("header-bar w-full justify-between items-center") as header:
        with ui.column():
            ui.label("Field Data Collection").classes("text-xl font-bold")
            ui.label(f"Welcome, {user_name}").classes("text-blue-100 text-sm")

        ui.button("Logout", on_click=lambda: ui.navigate.to("/logout")).props("flat color=white outline")

    return header


def create_stats_row(user_id: int) -> ui.row:
    """Create dashboard statistics row."""
    stats = DataCollectionService.get_dashboard_stats(user_id)

    with ui.row().classes("w-full gap-4 mb-6") as stats_row:
        # Today's collections
        with ui.card().classes("stat-card flex-1 text-center"):
            ui.label(str(stats.collections_today)).classes("text-2xl font-bold text-primary")
            ui.label("Today").classes("text-sm text-gray-600")

        # Total collections
        with ui.card().classes("stat-card flex-1 text-center"):
            ui.label(str(stats.total_collections)).classes("text-2xl font-bold text-green-600")
            ui.label("Total").classes("text-sm text-gray-600")

        # Pending sync
        with ui.card().classes("stat-card flex-1 text-center"):
            ui.label(str(stats.pending_sync)).classes("text-2xl font-bold text-amber-600")
            ui.label("Pending").classes("text-sm text-gray-600")

    return stats_row


def create_data_collection_form(user_id: int) -> None:
    """Create the main data collection form."""
    uploaded_photo_id: Optional[int] = None

    with ui.card().classes("form-card w-full mb-6"):
        ui.label("New Data Collection").classes("text-xl font-bold text-gray-800 mb-6")

        # Customer name input
        customer_name = (
            ui.input(label="Customer Name", placeholder="Enter customer name")
            .classes("w-full mb-4")
            .props("outlined dense")
        )

        # Description textarea
        description = (
            ui.textarea(label="Description", placeholder="Enter detailed description of the collection")
            .classes("w-full mb-6")
            .props("outlined rows=4")
        )

        # Photo upload section
        with ui.column().classes("w-full mb-6"):
            ui.label("Photo Upload (Optional)").classes("text-base font-semibold text-gray-700 mb-3")

            with ui.column().classes("photo-upload-area w-full") as upload_area:
                ui.icon("camera_alt", size="2rem").classes("text-gray-400 mb-2")
                ui.label("Take a photo or select from gallery").classes("text-gray-600 mb-4 text-center")

                ui.upload(
                    on_upload=lambda e: handle_photo_upload(e, upload_area, user_id),
                    auto_upload=True,
                    max_file_size=10_000_000,  # 10MB
                ).props('accept="image/*" capture="environment"').classes("w-full")

        # Submit button
        ui.button(
            "Submit Data Collection",
            on_click=lambda: handle_form_submit(
                customer_name.value,
                description.value,
                uploaded_photo_id,
                user_id,
                customer_name,
                description,
                upload_area,
            ),
        ).classes(
            "w-full bg-primary text-white py-3 rounded-lg text-lg font-semibold hover:bg-primary-600 transition-colors"
        )

        def handle_photo_upload(e: events.UploadEventArguments, container: ui.column, user_id: int) -> None:
            """Handle photo upload from camera or gallery."""
            nonlocal uploaded_photo_id

            try:
                # Validate file
                if not PhotoService.is_allowed_file(e.name):
                    ui.notify("Please upload a valid image file (JPG, PNG, GIF, WebP)", type="negative")
                    return

                if len(e.content.read()) > PhotoService.MAX_FILE_SIZE:
                    ui.notify("File size too large. Maximum size is 10MB.", type="negative")
                    return

                # Reset content position after size check
                e.content.seek(0)

                # Save photo
                photo = PhotoService.save_photo(e.content.read(), e.name, e.type)

                if photo is None:
                    ui.notify("Failed to upload photo. Please try again.", type="negative")
                    return

                uploaded_photo_id = photo.id

                # Update UI to show photo preview
                container.clear()
                with container:
                    ui.label("Photo uploaded successfully!").classes("text-green-600 font-semibold mb-2")

                    # Show photo preview if possible (in real app, you'd serve the image)
                    with ui.row().classes("items-center gap-4"):
                        ui.icon("check_circle", size="1.5rem").classes("text-green-500")
                        ui.label(f"📸 {e.name}").classes("text-gray-700")

                    # Option to upload different photo
                    ui.button("Change Photo", on_click=lambda: reset_photo_upload(container)).props(
                        "flat color=primary"
                    ).classes("mt-3")

                ui.notify("Photo uploaded successfully!", type="positive")

            except Exception as ex:
                logger.error(f"Error uploading photo: {str(ex)}")
                ui.notify(f"Error uploading photo: {str(ex)}", type="negative")

        def reset_photo_upload(container: ui.column) -> None:
            """Reset photo upload area to initial state."""
            nonlocal uploaded_photo_id
            uploaded_photo_id = None

            container.clear()
            with container:
                ui.icon("camera_alt", size="2rem").classes("text-gray-400 mb-2")
                ui.label("Take a photo or select from gallery").classes("text-gray-600 mb-4 text-center")

                ui.upload(
                    on_upload=lambda e: handle_photo_upload(e, container, user_id),
                    auto_upload=True,
                    max_file_size=10_000_000,
                ).props('accept="image/*" capture="environment"').classes("w-full")

        def handle_form_submit(
            customer_name_val: str,
            description_val: str,
            photo_id: Optional[int],
            user_id: int,
            customer_input: ui.input,
            desc_input: ui.textarea,
            upload_container: ui.column,
        ) -> None:
            """Handle form submission."""
            nonlocal uploaded_photo_id

            # Validate inputs
            if not customer_name_val or not customer_name_val.strip():
                ui.notify("Customer name is required", type="negative")
                customer_input.run_method("focus")
                return

            if not description_val or not description_val.strip():
                ui.notify("Description is required", type="negative")
                desc_input.run_method("focus")
                return

            # Create data collection
            collection_data = DataCollectionCreate(
                customer_name=customer_name_val.strip(),
                description=description_val.strip(),
                photo_id=photo_id,
                device_info={"user_agent": "NiceGUI Mobile App", "timestamp": datetime.utcnow().isoformat()},
            )

            try:
                collection = DataCollectionService.create_collection(user_id, collection_data)

                if collection is None:
                    ui.notify("Failed to save data collection. Please try again.", type="negative")
                    return

                # Success - clear form
                customer_input.set_value("")
                desc_input.set_value("")
                uploaded_photo_id = None
                reset_photo_upload(upload_container)

                # Refresh stats
                ui.navigate.reload()

                ui.notify(
                    f"Data collection saved successfully! Customer: {customer_name_val}", type="positive", timeout=3000
                )

            except Exception as ex:
                logger.error(f"Error saving data: {str(ex)}")
                ui.notify(f"Error saving data: {str(ex)}", type="negative")


def create_recent_collections(user_id: int) -> None:
    """Display recent data collections."""
    recent_collections = DataCollectionService.get_collections_by_user(user_id, limit=5)

    if not recent_collections:
        with ui.card().classes("stat-card w-full text-center py-8"):
            ui.icon("inbox", size="3rem").classes("text-gray-300 mb-3")
            ui.label("No data collections yet").classes("text-gray-500 text-lg")
            ui.label("Use the form above to create your first collection").classes("text-gray-400 text-sm")
        return

    with ui.card().classes("stat-card w-full"):
        ui.label("Recent Collections").classes("text-lg font-semibold text-gray-800 mb-4")

        for collection in recent_collections:
            with ui.row().classes("w-full items-center justify-between py-3 border-b border-gray-100 last:border-0"):
                with ui.column().classes("flex-1"):
                    ui.label(collection.customer_name).classes("font-medium text-gray-800")
                    ui.label(collection.description[:50] + ("..." if len(collection.description) > 50 else "")).classes(
                        "text-sm text-gray-600"
                    )
                    ui.label(collection.submission_date.strftime("%m/%d/%Y %H:%M")).classes("text-xs text-gray-500")

                with ui.row().classes("items-center gap-2"):
                    if collection.photo_id:
                        ui.icon("photo_camera", size="1.2rem").classes("text-green-500")

                    status_color = "text-green-500" if collection.is_synchronized else "text-amber-500"
                    status_icon = "sync" if collection.is_synchronized else "sync_problem"
                    ui.icon(status_icon, size="1.2rem").classes(status_color)


def create() -> None:
    """Create dashboard routes and components."""

    @ui.page("/dashboard")
    def dashboard_page():
        # Require authentication
        user = SessionManager.require_authentication()
        if user is None:
            return

        if user.id is None:
            ui.notify("User session error", type="negative")
            ui.navigate.to("/login")
            return

        # Apply mobile styles
        create_mobile_styles()

        with ui.column().classes("dashboard-container w-full"):
            # Header
            create_header(user.full_name)

            # Main content
            with ui.column().classes("content-area w-full"):
                # Statistics
                create_stats_row(user.id)

                # Data collection form
                create_data_collection_form(user.id)

                # Recent collections
                create_recent_collections(user.id)

    @ui.page("/")
    def index():
        """Redirect root to appropriate page."""
        if SessionManager.is_authenticated():
            ui.navigate.to("/dashboard")
        else:
            ui.navigate.to("/login")
