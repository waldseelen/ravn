"""
ravn_app/api/routers/ — HTTP endpoint routers.

Each module in this package owns one product area.  Routers validate incoming
requests, call the appropriate ravn_app.core service, and return serialized
responses.  No business logic lives here.
"""
