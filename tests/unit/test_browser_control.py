import pytest
from unittest.mock import AsyncMock, MagicMock
from kree.actions.browser_control import _BrowserThread

@pytest.mark.asyncio
async def test_smart_click_exception_handling():
    bt = _BrowserThread()
    
    # Mock page and get_by_role
    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.first.click = AsyncMock(side_effect=Exception("Simulated Playwright Timeout"))
    
    mock_page.get_by_role.return_value = mock_locator
    mock_page.get_by_text.return_value = mock_locator
    mock_page.get_by_placeholder.return_value = mock_locator
    
    # Replace _get_page with our mock
    bt._get_page = AsyncMock(return_value=mock_page)
    
    # Execute smart click. It should NOT crash, but return a "Could not find..." message due to the timeout.
    result = await bt._smart_click("nonexistent button")
    assert "Could not find: 'nonexistent button'" in result

@pytest.mark.asyncio
async def test_smart_type_exception_handling():
    bt = _BrowserThread()
    
    mock_page = MagicMock()
    mock_locator = MagicMock()
    # It uses clear and type
    mock_locator.first.clear = AsyncMock()
    mock_locator.first.type = AsyncMock(side_effect=Exception("Simulated Playwright Timeout"))
    
    mock_page.get_by_role.return_value = mock_locator
    mock_page.get_by_placeholder.return_value = mock_locator
    mock_page.get_by_label.return_value = mock_locator
    
    bt._get_page = AsyncMock(return_value=mock_page)
    
    result = await bt._smart_type("search box", "hello world")
    assert "Could not find input: 'search box'" in result
