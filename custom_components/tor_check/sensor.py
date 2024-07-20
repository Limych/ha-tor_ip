"""Sensor platform for TOR Check custom component."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

from .const import ATTR_REAL_IP, ATTR_TOR_CONNECTED
from .coordinator import KEY_MY_IP, KEY_MY_TOR_IP, KEY_TOR_CONNECTED
from .entity import TorCheckEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TorCheckDataUpdateCoordinator
    from .data import TorCheckConfigEntry

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="tor_ip",
        name="TOR IP",
        icon="mdi:ip",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: TorCheckConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        TorCheckSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class TorCheckSensor(TorCheckEntity, SensorEntity):
    """TOR Check Sensor class."""

    def __init__(
        self,
        coordinator: TorCheckDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(KEY_MY_TOR_IP)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return entity specific state attributes."""
        attrs = {
            ATTR_REAL_IP: self.coordinator.data.get(KEY_MY_IP),
            ATTR_TOR_CONNECTED: self.coordinator.data.get(KEY_TOR_CONNECTED),
        }
        attrs.update(super().extra_state_attributes or {})
        return attrs
