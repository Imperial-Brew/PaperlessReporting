import pytest
import json
import aiohttp
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
import hmac
import hashlib
from scripts.webhook_server import WebhookServer

@pytest.fixture
def webhook_server():
    """Create a test webhook server instance."""
    return WebhookServer(webhook_secret="test-secret")

@pytest.fixture
def client(webhook_server, aiohttp_client):
    """Create a test client for the webhook server."""
    return aiohttp_client(webhook_server.app)

def sign_payload(secret: str, payload: bytes) -> str:
    """Sign a payload with the given secret."""
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

@pytest.mark.asyncio
async def test_health_check(client):
    """Test the health check endpoint."""
    resp = await client.get("/health")
    assert resp.status == 200
    assert await resp.text() == "OK"

@pytest.mark.asyncio
async def test_webhook_missing_signature(client):
    """Test webhook with missing signature."""
    resp = await client.post("/webhook", json={"type": "test"})
    assert resp.status == 401
    assert await resp.text() == "Missing signature"

@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    """Test webhook with invalid signature."""
    payload = json.dumps({"type": "test"}).encode()
    headers = {"X-Webhook-Signature": "invalid-signature"}
    resp = await client.post("/webhook", data=payload, headers=headers)
    assert resp.status == 401
    assert await resp.text() == "Invalid signature"

@pytest.mark.asyncio
async def test_webhook_missing_event_type(client):
    """Test webhook with missing event type."""
    payload = json.dumps({}).encode()
    signature = sign_payload("test-secret", payload)
    headers = {"X-Webhook-Signature": signature}
    resp = await client.post("/webhook", data=payload, headers=headers)
    assert resp.status == 400
    assert await resp.text() == "Missing event type"

@pytest.mark.asyncio
async def test_webhook_unsupported_event(client):
    """Test webhook with unsupported event type."""
    payload = json.dumps({"type": "unsupported.event"}).encode()
    signature = sign_payload("test-secret", payload)
    headers = {"X-Webhook-Signature": signature}
    resp = await client.post("/webhook", data=payload, headers=headers)
    assert resp.status == 400
    assert await resp.text() == "Unsupported event type"

@pytest.mark.asyncio
async def test_webhook_success(client):
    """Test successful webhook handling."""
    # Create a test handler
    handled_events = []
    async def test_handler(data):
        handled_events.append(data)
    
    # Add the handler to the server
    client.app["event_handlers"]["test.event"] = test_handler
    
    # Send a webhook
    payload = json.dumps({"type": "test.event", "data": "test"}).encode()
    signature = sign_payload("test-secret", payload)
    headers = {"X-Webhook-Signature": signature}
    resp = await client.post("/webhook", data=payload, headers=headers)
    
    # Check response
    assert resp.status == 200
    assert await resp.text() == "OK"
    
    # Check that handler was called
    assert len(handled_events) == 1
    assert handled_events[0] == {"type": "test.event", "data": "test"}

@pytest.mark.asyncio
async def test_webhook_handler_error(client):
    """Test webhook with handler error."""
    # Create a handler that raises an error
    async def error_handler(data):
        raise Exception("Test error")
    
    # Add the handler to the server
    client.app["event_handlers"]["error.event"] = error_handler
    
    # Send a webhook
    payload = json.dumps({"type": "error.event"}).encode()
    signature = sign_payload("test-secret", payload)
    headers = {"X-Webhook-Signature": signature}
    resp = await client.post("/webhook", data=payload, headers=headers)
    
    # Check response
    assert resp.status == 500
    assert await resp.text() == "Internal server error" 