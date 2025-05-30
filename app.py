from flask import Flask
import os

# Create the Flask application
app = Flask(__name__)

# Import webhook routes so they register on this app
import scripts.webhook_server  # noqa: F401

# Expose 'app' for WSGI servers like gunicorn
__all__ = ["app"]

# Optional: allow running locally with `python app.py`
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
