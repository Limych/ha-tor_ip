"""Constants for TOR Check custom component."""
from logging import Logger, getLogger
from typing import Any, Final

LOGGER: Logger = getLogger(__package__)

NAME: Final = "TOR Check"
DOMAIN: Final = "tor_check"
VERSION: Final = "0.2.0"
ATTRIBUTION: Final = "Data provided by TOR network"
ISSUE_URL: Final = "https://github.com/Limych/ha-tor_check/issues"

STARTUP_MESSAGE: Final = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have ANY issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

CONF_TOR_HOST: Final = "tor_host"
CONF_TOR_PORT: Final = "tor_port"

ATTR_REAL_IP = "Real IP"
ATTR_TOR_IP = "TOR IP"
ATTR_TOR_CONNECTED = "TOR connected"

DEFAULT_CONFIG: Final = {
    CONF_TOR_HOST: "localhost",
    CONF_TOR_PORT: 9050,
}

ConfigType = dict[str, Any]
