# Quote Created Event Fix

## Issue Identified

The webhook server was encountering an error when processing `quote.created` events. The error message was:

```
⚠️ Missing required fields in quote data: {'uuid': '608d41a4-8f92-49a9-8d53-5bef17be3131', 'number': 7838, 'status': 'draft', ...}
```

This was happening because the `handle_quote_status_changed` function, which is used to process both `quote.status_changed` and `quote.created` events, was expecting a field named `quote_number`, but the data from `quote.created` events contains a field named `number` instead.

## Changes Made

1. Modified the `handle_quote_status_changed` function in `scripts/webhook_server.py` to handle both data formats:
   - Updated the function to check for both `quote_number` and `number` fields
   - Added fallback logic to use `number` if `quote_number` is not present
   - Updated the function's docstring to reflect that it handles both event types

2. Created a test script `scripts/test_quote_created_fix.py` to verify the fix:
   - The script simulates a `quote.created` event with the actual data structure
   - It sends the event to the webhook server and checks the response

## How to Test

You can test the fix by running the new test script:

```
python scripts/test_quote_created_fix.py
```

This will send a sample `quote.created` event to the webhook server and verify that it's processed correctly.

## Technical Details

The key change was in the `handle_quote_status_changed` function:

```python
# Before:
quote_number = data.get('quote_number')

# After:
quote_number = data.get('quote_number') or str(data.get('number', ''))
```

This change allows the function to handle both data formats:
- For `quote.status_changed` events, it will use the `quote_number` field
- For `quote.created` events, it will use the `number` field if `quote_number` is not present

The `str()` conversion is used to ensure that the value is a string, as the `number` field in the `quote.created` event is an integer.

## Future Considerations

1. Consider standardizing the field names in the webhook server to match the Paperless Parts API
2. Add more comprehensive validation for webhook events to catch similar issues earlier
3. Implement more detailed logging to make troubleshooting easier