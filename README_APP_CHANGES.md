# App Structure Changes

## Issue Fixed

Fixed the error: `name 'app' is not defined` in the webhook server.

## Changes Made

1. **Removed direct use of 'app' in webhook_server.py**
   - Removed `@app.route` decorators
   - Removed code that used `app.url_map.iter_rules()`
   - Modified the `if __name__ == "__main__":` block to create a Flask app if the script is run directly

2. **Fixed merge conflicts in render.yaml**
   - Resolved conflicts to use `gunicorn app:app` as the start command

## Explanation

The issue was that webhook_server.py was trying to use the 'app' variable directly with decorators and other Flask-specific code, but 'app' was defined in app.py and not in webhook_server.py.

The application is structured so that:
1. app.py creates the Flask application
2. app.py imports the webhook_server module
3. app.py registers the routes from webhook_server using app.add_url_rule()

By removing the direct use of 'app' in webhook_server.py, we've made the code more modular and avoided circular imports. The webhook_server.py file can now be imported by app.py without errors.

## Testing

The changes have been tested to ensure that:
1. The application starts without errors
2. The routes are correctly registered
3. The webhook functionality works as expected

## Deployment

The application is deployed using Render with the command `gunicorn app:app`, which starts the Flask application defined in app.py.