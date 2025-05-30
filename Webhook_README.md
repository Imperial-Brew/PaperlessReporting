# Paperless Parts Webhook Server

This document explains how to use the webhook server for receiving and processing events from Paperless Parts.

## Endpoints

The webhook server provides the following endpoints:

- **GET /** - Returns basic information about the API
- **GET /health** - Health check endpoint for monitoring
- **POST /webhook** - Webhook endpoint for receiving events from Paperless Parts

## Authentication

The webhook endpoint supports two authentication methods:

1. **Token Parameter**: Add a `token` query parameter to the URL with your webhook secret
   ```
   POST /webhook?token=your-webhook-secret
   ```

2. **X-Webhook-Signature Header**: Sign the request body with your webhook secret using HMAC-SHA256
   ```
   POST /webhook
   X-Webhook-Signature: computed-signature
   ```

## Supported Events

The webhook server currently supports the following event types:

- **quote.status_changed** - Triggered when a quote's status changes
- **order.status_changed** - Triggered when an order's status changes

## Configuration

The webhook server can be configured using environment variables or the `config.json` file:

### Environment Variables

```
WEBHOOK_SECRET=your-webhook-secret
PAPERLESS_API_TOKEN=your-api-token
```

### Config File

```json
{
  "webhook_secret": "your-webhook-secret",
  "api_key": "your-api-token"
}
```

## S3 Integration

The webhook server can upload data to AWS S3. See [Webhook_S3_Setup.md](Webhook_S3_Setup.md) for details on configuring S3 integration.

## Testing

You can test the webhook server using the provided test script:

```
python scripts/test_webhook.py
```

This will send a sample webhook event to the server.

## Troubleshooting

If you encounter 404 errors:
1. Make sure the server is running
2. Check that you're using the correct URL
3. Verify that the routes are properly registered

If you encounter authentication errors:
1. Check that you're using the correct webhook secret
2. Verify that you're using one of the supported authentication methods