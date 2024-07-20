"""TOR Check custom component for Home Assistant.

For more details about this integration, please refer to
https://github.com/limych/ha-tor_check
"""

from __future__ import annotations

import logging
from ssl import SSLContext
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

import aiohttp
from aiohttp.hdrs import USER_AGENT
from aiohttp_socks import ProxyConnector
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_CLOSE, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import (
    ENABLE_CLEANUP_CLOSED,
    MAXIMUM_CONNECTIONS,
    MAXIMUM_CONNECTIONS_PER_HOST,
    SERVER_SOFTWARE,
    WARN_CLOSE_MSG,
    HassClientResponse,
    async_get_clientsession,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.frame import warn_use
from homeassistant.helpers.json import json_dumps
from homeassistant.loader import async_get_loaded_integration, bind_hass
from homeassistant.util import ssl as ssl_util

from .api import TorCheckApiClient
from .const import (
    CONF_TOR_HOST,
    CONF_TOR_PORT,
    DEFAULT_CONFIG,
    DOMAIN,
    STARTUP_MESSAGE,
    ConfigType,
)
from .coordinator import TorCheckDataUpdateCoordinator
from .data import TorCheckData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import TorCheckConfigEntry

_LOGGER: Final = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(
                    CONF_TOR_HOST, default=DEFAULT_CONFIG[CONF_TOR_HOST]
                ): cv.string,
                vol.Optional(CONF_TOR_PORT, default=DEFAULT_CONFIG[CONF_TOR_PORT]): int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@callback
def _async_get_proxy_connector(
    hass: HomeAssistant, proxy_url: str, verify_ssl: bool = True
) -> aiohttp.BaseConnector:
    """Return the connector pool for aiohttp.

    This method must be run in the event loop.
    """
    if verify_ssl:
        ssl_context: bool | SSLContext = ssl_util.get_default_context()
    else:
        ssl_context = ssl_util.get_default_no_verify_context()

    connector = ProxyConnector.from_url(
        url=proxy_url,
        rdns=True,
        enable_cleanup_closed=ENABLE_CLEANUP_CLOSED,
        ssl=ssl_context,
        limit=MAXIMUM_CONNECTIONS,
        limit_per_host=MAXIMUM_CONNECTIONS_PER_HOST,
    )

    async def _async_close_connector(event: Event) -> None:
        """Close connector pool."""
        await connector.close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_CLOSE, _async_close_connector)

    return connector


@callback
def _async_register_clientsession_shutdown(
    hass: HomeAssistant, clientsession: aiohttp.ClientSession
) -> None:
    """Register ClientSession close on Home Assistant shutdown or config entry unload.

    This method must be run in the event loop.
    """

    @callback
    def _async_close_websession(*_: Any) -> None:
        """Close websession."""
        clientsession.detach()

    unsub = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_CLOSE, _async_close_websession
    )

    if not (config_entry := config_entries.current_entry.get()):
        return

    config_entry.async_on_unload(unsub)
    config_entry.async_on_unload(_async_close_websession)


@callback
@bind_hass
def async_create_proxy_clientsession(
    hass: HomeAssistant,
    proxy_url: str,
    verify_ssl: bool = True,
    auto_cleanup: bool = True,
    **kwargs: Any,
) -> aiohttp.ClientSession:
    """Create a new ClientSession with kwargs, i.e. for cookies.

    If auto_cleanup is False, you need to call detach() after the session
    returned is no longer used. Default is True, the session will be
    automatically detached on homeassistant_stop or when being created
    in config entry setup, the config entry is unloaded.

    This method must be run in the event loop.
    """
    auto_cleanup_method = None
    if auto_cleanup:
        auto_cleanup_method = _async_register_clientsession_shutdown

    clientsession = aiohttp.ClientSession(
        connector=_async_get_proxy_connector(hass, proxy_url, verify_ssl),
        json_serialize=json_dumps,
        response_class=HassClientResponse,
        **kwargs,
    )
    # Prevent packages accidentally overriding our default headers
    # It's important that we identify as Home Assistant
    # If a package requires a different user agent, override it by passing a headers
    # dictionary to the request method.
    # pylint: disable-next=protected-access
    clientsession._default_headers = MappingProxyType(  # type: ignore[assignment]
        {USER_AGENT: SERVER_SOFTWARE},
    )

    clientsession.close = warn_use(  # type: ignore[method-assign]
        clientsession.close,
        WARN_CLOSE_MSG,
    )

    if auto_cleanup_method:
        auto_cleanup_method(hass, clientsession)

    return clientsession


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up this integration using YAML."""
    # Print startup message
    if DOMAIN not in hass.data:
        _LOGGER.info(STARTUP_MESSAGE)
        hass.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
        )
    )

    return True


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: TorCheckConfigEntry) -> bool:
    """Set up this integration using UI."""
    proxy_url = f"socks5://{entry.data[CONF_TOR_HOST]}:{entry.data[CONF_TOR_PORT]}"

    coordinator = TorCheckDataUpdateCoordinator(hass)
    entry.runtime_data = TorCheckData(
        client=TorCheckApiClient(
            session=async_get_clientsession(hass),
            tor_session=async_create_proxy_clientsession(hass, proxy_url),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
