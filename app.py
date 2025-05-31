from flask import Flask, request
import os
import uuid
from scripts.utils.logging_config import configure_logging, get_logger, set_correlation_id

# Configure centralized logging
configure_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    use_json=os.getenv('LOG_FORMAT', '').lower() == 'json',
    log_file=os.getenv('LOG_FILE')
)
logger = get_logger(__name__)

# Create the Flask application
app = Flask(__name__)

# Add middleware to set correlation ID for each request
@app.before_request
def before_request():
    # Get correlation ID from header or generate a new one
    correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
    set_correlation_id(correlation_id)
    logger.info(f"Request started: {request.method} {request.path}")

@app.after_request
def after_request(response):
    # Add correlation ID to response headers
    correlation_id = set_correlation_id()  # Get current correlation ID
    response.headers['X-Correlation-ID'] = correlation_id
    logger.info(f"Request completed: {request.method} {request.path} - {response.status_code}")
    return response

# Import WebhookServer class and initialize it with our Flask app
from scripts.webhook_server import webhook_server

# Set the Flask app for the webhook server
webhook_server.app = app

# Register routes from webhook_server
app.add_url_rule('/', 'index', webhook_server.index)
app.add_url_rule('/health', 'health', webhook_server.health)
app.add_url_rule('/webhook', 'webhook', webhook_server.webhook, methods=['POST'])

# Initialize event handlers
app.config['event_handlers'] = {}

logger.info("Registered routes from webhook_server")

# Expose 'app' for WSGI servers like gunicorn
__all__ = ["app"]

# Optional: allow running locally with `python app.py`
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
