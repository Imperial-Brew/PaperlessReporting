import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from typing import Dict, Any

from scripts.utils.async_puller import AsyncPuller
from scripts.utils.async_token_bucket import AsyncTokenBucket

def make_aiohttp_context_manager(status=200, json_data=None):
    response = AsyncMock()
    response.status = status
    if json_data is not None:
        response.json = AsyncMock(return_value=json_data)
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = response
    context_manager.__aexit__.return_value = None
    return context_manager, response

class TestPuller(AsyncPuller[Dict[str, Any]]):
    """Test implementation of AsyncPuller."""
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": data.get("id"), "name": data.get("name")}

@pytest.fixture
def puller():
    """Create a test puller instance."""
    return TestPuller(endpoint="test")

@pytest.fixture
def mock_session():
    session = AsyncMock()
    context_manager, _ = make_aiohttp_context_manager(200, {"id": 1, "name": "test"})
    session.get.return_value = context_manager
    return session

@pytest.mark.asyncio
async def test_fetch_item_success(puller, mock_session):
    result = await puller.fetch_item(mock_session, 1)
    assert result == {"id": 1, "name": "test"}

@pytest.mark.asyncio
async def test_fetch_item_rate_limit(puller, mock_session):
    context_manager, _ = make_aiohttp_context_manager(429)
    mock_session.get.return_value = context_manager
    result = await puller.fetch_item(mock_session, 1)
    assert result is None

@pytest.mark.asyncio
async def test_fetch_item_error(puller, mock_session):
    context_manager, _ = make_aiohttp_context_manager(500)
    mock_session.get.return_value = context_manager
    result = await puller.fetch_item(mock_session, 1)
    assert result is None

@pytest.mark.asyncio
async def test_process_items(puller, mock_session):
    def get_side_effect(*args, **kwargs):
        context_manager, _ = make_aiohttp_context_manager(200, {"id": 1, "name": "test"})
        return context_manager
    mock_session.get.side_effect = get_side_effect
    
    # Patch aiohttp.ClientSession to return a context manager whose __aenter__ returns mock_session
    mock_client_session_cm = AsyncMock()
    mock_client_session_cm.__aenter__.return_value = mock_session
    mock_client_session_cm.__aexit__.return_value = None
    
    with patch("aiohttp.ClientSession", return_value=mock_client_session_cm):
        await puller.process_items([1, 2, 3], "test.csv")
        assert mock_session.get.call_count == 3

@pytest.mark.asyncio
async def test_fetch_all_paginated(puller, mock_session):
    responses = [
        {"results": [{"id": 1, "name": "test1"}], "next": "next_url"},
        {"results": [{"id": 2, "name": "test2"}], "next": None}
    ]
    def get_side_effect(*args, **kwargs):
        async def mock_json():
            return responses.pop(0)
        context_manager, response = make_aiohttp_context_manager(200)
        response.json = AsyncMock(side_effect=mock_json)
        return context_manager
    mock_session.get.side_effect = get_side_effect
    
    # Patch aiohttp.ClientSession to return a context manager whose __aenter__ returns mock_session
    mock_client_session_cm = AsyncMock()
    mock_client_session_cm.__aenter__.return_value = mock_session
    mock_client_session_cm.__aexit__.return_value = None
    
    with patch("aiohttp.ClientSession", return_value=mock_client_session_cm):
        items = []
        async for item in puller.fetch_all_paginated(mock_session):
            items.append(item)
        assert len(items) == 2
        assert items[0] == {"id": 1, "name": "test1"}
        assert items[1] == {"id": 2, "name": "test2"}

@pytest.mark.asyncio
async def test_token_bucket():
    bucket = AsyncTokenBucket(rate=1.0, capacity=2)
    assert await bucket.acquire()
    assert await bucket.acquire()
    assert not await bucket.acquire(timeout=0.1)
    await asyncio.sleep(1.1)
    assert await bucket.acquire() 