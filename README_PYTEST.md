# Pytest Configuration

## Changes Made

The pytest configuration has been updated to make the coverage reporting optional. This change was made to address an error that occurred when running pytest without the pytest-cov plugin installed.

### Previous Error

```
ERROR: usage: _jb_pytest_runner.py [options] [file_or_dir] [file_or_dir] [...]
_jb_pytest_runner.py: error: unrecognized arguments: --cov=scripts --cov-report=term --cov-report=html
```

### Solution

The `addopts` line in pytest.ini has been commented out, making the coverage arguments optional. This allows pytest to run without the pytest-cov plugin installed.

## Using Pytest

### Running Tests Without Coverage

To run tests without coverage reporting:

```
pytest
```

Or to run a specific test file:

```
pytest scripts/test_s3_config.py
```

### Running Tests With Coverage

To run tests with coverage reporting, you need to install the pytest-cov plugin:

```
pip install pytest-cov
```

Alternatively, you can uncomment the pytest-cov line in requirements.txt and run:

```
pip install -r requirements.txt
```

Then you can run pytest with the coverage arguments:

```
pytest --cov=scripts --cov-report=term --cov-report=html
```

Or to run a specific test file with coverage:

```
pytest scripts/test_s3_config.py --cov=scripts --cov-report=term --cov-report=html
```

## Restoring Automatic Coverage

If you want to restore the automatic coverage reporting for all pytest runs, you can uncomment the `addopts` line in pytest.ini:

```
# Configure pytest-cov (only used if pytest-cov is installed)
addopts = --cov=scripts --cov-report=term --cov-report=html
```

Note that this will require the pytest-cov plugin to be installed for all pytest runs.
