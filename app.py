from scripts.webhook_server import app
# when using gunicorn or similar WSGI servers.
# It imports the app instance from the webhook_server module.

__all__ = ["app"]

# This file exists to maintain compatibility with gunicorn's app:app convention 