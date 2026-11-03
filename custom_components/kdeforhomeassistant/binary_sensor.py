"""Connection state of KDE Connect devices."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .device import KdeConnectDevice
from .entity import KdeConnectEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a connectivity sensor for every device."""
    for subentry_id, device in entry.runtime_data.devices.items():
        async_add_entities(
            [KdeConnectConnectedSensor(device)], config_subentry_id=subentry_id
        )


class KdeConnectConnectedSensor(KdeConnectEntity, BinarySensorEntity):
    """Whether the device is connected to Home Assistant."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connected"

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "connected")

    @property
    def available(self) -> bool:
        """The sensor itself is always available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return whether the device is connected."""
        return self.device.connected
