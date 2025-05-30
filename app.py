from flask import Flask
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)

# Import routes from webhook_server
from scripts.webhook_server import webhook_server

# Register routes from webhook_server
app.add_url_rule('/', 'index', webhook_server.index)
app.add_url_rule('/health', 'health', webhook_server.health)
app.add_url_rule('/webhook', 'webhook', webhook_server.webhook, methods=['POST'])

logger.info("Registered routes from webhook_server")

# Expose 'app' for WSGI servers like gunicorn
__all__ = ["app"]

# Optional: allow running locally with `python app.py`
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
