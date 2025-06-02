# Paperless Parts Webhook Server

## Overview

This document provides comprehensive information about the webhook server for receiving and processing events from Paperless Parts, including setup instructions, configuration, and supported event types.

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

- **quote.created** - Triggered when a new quote is created
- **quote.status_changed** - Triggered when a quote's status changes
- **order.created** - Triggered when a new order is created
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

The webhook server can upload data to AWS S3. See [s3_configuration.md](s3_configuration.md) for details on configuring S3 integration.

## Recent Changes

### Added Support for `order.created` Event Type

- Modified `scripts/webhook_server.py` to handle `order.created` events
- Reused the existing `handle_order_status_changed` function to process the order data
- Added logging to track order creation events

### Added Support for `quote.created` Event Type

- Modified `scripts/webhook_server.py` to handle `quote.created` events
- Reused the existing `handle_quote_status_changed` function to process the quote data
- Added logging to track quote creation events

### Fixed Quote Created Event Processing

The webhook server was encountering an error when processing `quote.created` events due to field name differences. The fix includes:

- Updated the `handle_quote_status_changed` function to check for both `quote_number` and `number` fields
- Added fallback logic to use `number` if `quote_number` is not present
- Updated the function's docstring to reflect that it handles both event types

## Testing

You can test the webhook server using the provided test scripts:

```
python scripts/test_webhook.py
python scripts/test_order_created.py
python scripts/test_quote_created.py
python scripts/test_quote_created_fix.py
```

These will send sample webhook events to the server and verify that they're processed correctly.

## Troubleshooting

### 404 Errors
1. Make sure the server is running
2. Check that you're using the correct URL
3. Verify that the routes are properly registered

### Authentication Errors
1. Check that you're using the correct webhook secret
2. Verify that you're using one of the supported authentication methods

### App Structure Issues

If you encounter errors related to the app structure (e.g., `name 'app' is not defined`), ensure that:

1. The webhook_server.py file doesn't directly use the 'app' variable with decorators
2. Routes are registered using app.add_url_rule() in app.py
3. The application is started using the correct command: `gunicorn app:app`

## Recommendations for Future Development

1. **Add Support for More Event Types**
   - Consider adding support for other Paperless Parts event types like:
     - `quote.updated`
     - `quote.sent`
     - `order.updated`

2. **Improve Error Handling**
   - Add more detailed error messages for different failure scenarios
   - Implement retry logic for failed webhook processing

3. **Enhance Logging**
   - Add more structured logging to make troubleshooting easier
   - Consider adding request IDs to track webhook requests through the system

4. **Implement Webhook Verification**
   - Add support for verifying webhook signatures to ensure requests are coming from Paperless Parts
   - Store webhook events for audit purposes