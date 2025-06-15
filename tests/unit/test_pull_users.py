import pytest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path
from scripts.pull_users import fetch_users, main

@pytest.fixture
def mock_response():
    mock = MagicMock()
    mock.json.return_value = [
        {"id": 1, "first_name": "John", "last_name": "Doe", "email": "john@example.com", "role": "Admin"},
        {"id": 2, "first_name": "Jane", "last_name": "Smith", "email": "jane@example.com", "role": "Sales"}
    ]
    mock.raise_for_status = MagicMock()
    return mock

def test_fetch_users(mock_response):
    with patch('requests.get', return_value=mock_response):
        users = fetch_users()
        assert len(users) == 2
        assert users[0]['first_name'] == 'John'
        assert users[1]['email'] == 'jane@example.com'

def test_fetch_users_pagination(mock_response):
    # Test pagination handling
    first_response = MagicMock()
    first_response.json.return_value = {
        "results": [{"id": 1, "first_name": "John"}],
        "next": "next_url"
    }
    
    second_response = MagicMock()
    second_response.json.return_value = {
        "results": [{"id": 2, "first_name": "Jane"}],
        "next": None
    }
    
    with patch('requests.get', side_effect=[first_response, second_response]):
        users = fetch_users()
        assert len(users) == 2

def test_main_function(mock_response):
    with patch('scripts.pull_users.fetch_users', return_value=mock_response.json()):
        with patch('builtins.open', MagicMock()):
            with patch('csv.DictWriter') as mock_writer:
                instance = mock_writer.return_value
                instance.writeheader = MagicMock()
                instance.writerows = MagicMock()
                with patch('pathlib.Path.mkdir'):
                    main()
                    # Verify CSV writing was attempted
                    assert instance.writeheader.called
                    assert instance.writerows.called