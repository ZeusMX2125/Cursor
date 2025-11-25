"""Tests for the refactored TopstepX client with Result-based error handling."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from api.topstepx_client_v2 import TopstepXClientV2
from api.result import Success, Error
from config.settings import Settings
from api.auth_manager import AuthManager


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock(spec=Settings)
    settings.topstepx_base_url = "https://api.topstepx.com/api"
    settings.topstepx_username = "test_user"
    settings.topstepx_api_key = "test_key"
    settings.topstepx_auth_mode = "login_key"
    settings.topstepx_validate_tokens = False
    return settings


@pytest.fixture
def mock_auth_manager():
    """Create mock auth manager."""
    auth = Mock(spec=AuthManager)
    auth.get_headers = AsyncMock(return_value={
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    })
    return auth


@pytest.mark.asyncio
async def test_client_returns_success_on_200(mock_settings, mock_auth_manager):
    """Test that client returns Success when API responds with 200."""
    client = TopstepXClientV2(mock_settings, mock_auth_manager)
    await client.initialize()
    
    # Mock the session to return a successful response
    with patch.object(client.session, 'request') as mock_request:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "contracts": [{"id": "1", "symbol": "ESZ25"}]
        })
        mock_request.return_value.__aenter__.return_value = mock_response
        
        result = await client.list_available_contracts(live=True)
        
        assert isinstance(result, Success)
        assert result.is_success()
        assert not result.is_error()
        contracts = result.unwrap()
        assert len(contracts) == 1
        assert contracts[0]["symbol"] == "ESZ25"
    
    await client.close()


@pytest.mark.asyncio
async def test_client_returns_error_on_500(mock_settings, mock_auth_manager):
    """Test that client returns Error when API responds with 500."""
    client = TopstepXClientV2(mock_settings, mock_auth_manager)
    await client.initialize()
    
    with patch.object(client.session, 'request') as mock_request:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_request.return_value.__aenter__.return_value = mock_response
        
        result = await client.list_available_contracts(live=True)
        
        assert isinstance(result, Error)
        assert not result.is_success()
        assert result.is_error()
        assert result.status_code == 502  # Upstream error
        assert "ProjectX API error" in result.message
    
    await client.close()


@pytest.mark.asyncio
async def test_client_returns_error_on_401(mock_settings, mock_auth_manager):
    """Test that client returns Error when auth fails."""
    client = TopstepXClientV2(mock_settings, mock_auth_manager)
    await client.initialize()
    
    with patch.object(client.session, 'request') as mock_request:
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errorCode": 1,
            "errorMessage": "Invalid credentials"
        })
        mock_request.return_value.__aenter__.return_value = mock_response
        
        result = await client.list_available_contracts(live=True)
        
        assert isinstance(result, Error)
        assert result.status_code == 401
        assert "Invalid credentials" in result.message or "Unauthorized" in result.message
    
    await client.close()

