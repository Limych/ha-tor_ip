# pylint: disable=protected-access,redefined-outer-name
"""Test tor_check API Client."""

from __future__ import annotations

import socket
from unittest.mock import patch

import aiohttp
import pytest
import pytest_asyncio
import python_socks
from aioresponses import aioresponses

from custom_components.tor_check import api
from custom_components.tor_check.api import (
    IPIFY_API_URL,
    TorCheckApiClient,
    TorCheckApiClientAuthenticationError,
    TorCheckApiClientCommunicationError,
)


# mock object here
@pytest_asyncio.fixture
async def mock_response():
    """Make mock response object."""
    with aioresponses() as mocker:
        yield mocker


# your client async here
@pytest_asyncio.fixture
async def async_client():
    """Make client session object."""
    async with aiohttp.ClientSession() as session:
        yield session


async def test__async_get_data(async_client, mock_response) -> None:
    """Test _async_get_data for correct usage."""
    url = "test.url"
    data = "123.45.67.89"
    mock_response.get(url, status=200, body=data)
    #
    resp = await api._async_get_data(async_client, url)
    #
    assert resp == data


async def test__async_get_data_fails(async_client, mock_response) -> None:
    """Test _async_get_data for fails."""
    for status in [401, 403]:
        url = f"test.url/fail-{status}"
        mock_response.get(url, status=status)
        #
        with pytest.raises(TorCheckApiClientAuthenticationError):
            _ = await api._async_get_data(async_client, url)

    url = "test.url/fail-timeout"
    mock_response.get(url, exception=TimeoutError)
    #
    with pytest.raises(TorCheckApiClientCommunicationError):
        _ = await api._async_get_data(async_client, url)

    for exception in [
        aiohttp.ClientError,
        socket.gaierror,
        python_socks.ProxyConnectionError,
    ]:
        url = f"test.url/fail-{exception}"
        mock_response.get(url, exception=exception)
        #
        with pytest.raises(TorCheckApiClientCommunicationError):
            _ = await api._async_get_data(async_client, url)


async def test_async_get_my_tor_ip(async_client, mock_response) -> None:
    """Test TorCheckApiClient.async_get_my_tor_ip."""
    api = TorCheckApiClient(async_client, async_client)

    data = "123.45.67.89"
    mock_response.get(url=IPIFY_API_URL, status=200, body=data)
    #
    resp = await api.async_get_my_tor_ip()
    #
    assert resp == data


async def test_async_get_my_ip(async_client, mock_response) -> None:
    """Test TorCheckApiClient.async_get_my_ip."""
    api = TorCheckApiClient(async_client, async_client)

    data = "123.45.67.89"
    mock_response.get(url=IPIFY_API_URL, status=200, body=data)
    #
    resp = await api.async_get_my_ip()
    #
    assert resp == data


@patch("socket.getaddrinfo")
async def test_async_is_tor_ip(mock_getaddrinfo: socket.getaddrinfo) -> None:
    """Test TorCheckApiClient.async_is_tor_ip."""
    mock_getaddrinfo = mock_getaddrinfo.return_value  # We want the instance

    resp = await TorCheckApiClient.async_is_tor_ip(None)
    #
    assert resp is False

    ip = "123.45.67.89"
    mock_getaddrinfo.recvfrom.return_value = [ip]
    #
    resp = await TorCheckApiClient.async_is_tor_ip(ip)
    #
    assert resp is True


@patch("socket.getaddrinfo")
async def test_async_is_tor_ip_fails(mock_getaddrinfo) -> None:
    """Test TorCheckApiClient.async_is_tor_ip for fails."""
    ip = "123.45.67.89"

    mock_getaddrinfo.side_effect = socket.gaierror
    #
    resp = await TorCheckApiClient.async_is_tor_ip(ip)
    #
    assert resp is False

    mock_getaddrinfo.side_effect = TimeoutError
    #
    with pytest.raises(TorCheckApiClientCommunicationError):
        _ = await TorCheckApiClient.async_is_tor_ip(ip)
