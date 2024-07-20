"""Custom types for TOR Checker."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import TorCheckApiClient
    from .coordinator import TorCheckDataUpdateCoordinator


type TorCheckConfigEntry = ConfigEntry[TorCheckData]


@dataclass
class TorCheckData:
    """Data for the TOR Check integration."""

    client: TorCheckApiClient
    coordinator: TorCheckDataUpdateCoordinator
    integration: Integration
