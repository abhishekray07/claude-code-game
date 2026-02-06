"""Shared test fixtures."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx._transports.asgi import ASGITransport


@pytest.fixture
def mock_sandbox_manager():
    """Mock sandbox_manager for API tests."""
    with patch("app.api.docker_terminal.sandbox_manager") as mock:
        mock.create_session = AsyncMock(return_value={
            "session_id": "test1234",
            "port": 10001,
            "ttyd_token": "fake-token",
        })
        mock.get_session = MagicMock(return_value=None)
        mock.destroy_session = AsyncMock()
        mock.update_activity = MagicMock()
        mock.can_create_session_for_ip = MagicMock(return_value=True)
        mock.sessions = {}
        yield mock


@pytest.fixture
def mock_level():
    """Mock level loading."""
    mock_lev = MagicMock()
    mock_lev.number = 1
    mock_lev.title = "Test Level"
    mock_lev.module = "basics"
    mock_lev.intro = "Test intro"
    mock_lev.video = None
    mock_lev.exercise = None
    with patch("app.api.docker_terminal.load_level_by_number", return_value=mock_lev):
        yield mock_lev


@pytest.fixture
def client(mock_sandbox_manager, mock_level):
    """Async test client with mocked dependencies."""
    from app.main import app
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")
