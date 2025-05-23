# Paperless Webhook Server

A webhook server for handling Paperless API events, deployed on Render.

## Features

- Secure webhook endpoint with signature verification
- Event-based handler system
- Health check endpoint
- Comprehensive logging
- Automatic deployment on Render

## Environment Variables

The following environment variables need to be set in your Render dashboard:

- `WEBHOOK_SECRET`: Secret key for validating webhook signatures
- `API_KEY`: Your Paperless API key
- `API_BASE_URL`: Base URL for the Paperless API

## Webhook Endpoint

The webhook endpoint is available at:
```
https://paperless-webhook.onrender.com/webhook
```

### Request Format

```json
{
  "type": "event.type",
  "data": {
    // Event-specific data
  }
}
```

### Headers

- `X-Webhook-Signature`: HMAC-SHA256 signature of the request body

### Response Codes

- `200`: Event handled successfully
- `400`: Invalid request (missing event type, unsupported event)
- `401`: Invalid or missing signature
- `500`: Internal server error

## Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
python -m pytest tests/
```

3. Start the server locally:
```bash
python scripts/webhook_server.py
```

## Deployment

The server is automatically deployed to Render when changes are pushed to the main branch.

## Health Check

The health check endpoint is available at:
```
https://paperless-webhook.onrender.com/health
```

## License

MIT 