"""Base entity for KDE Connect devices."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .device import KdeConnectDevice

MODELS = {
    "desktop": "Desktop",
    "laptop": "Laptop",
    "phone": "Phone",
    "smartphone": "Phone",
    "tablet": "Tablet",
    "tv": "TV",
}


class KdeConnectEntity(Entity):
    """An entity that belongs to one paired device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: KdeConnectDevice, key: str) -> None:
        self.device = device
        self._attr_unique_id = f"{device.device_id}_{key}"
        connections = set()
        if device.mac:
            connections.add((dr.CONNECTION_NETWORK_MAC, dr.format_mac(device.mac)))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            connections=connections,
            name=device.name,
            manufacturer="KDE Connect",
            model=MODELS.get(device.device_type, "Device"),
        )

    @property
    def available(self) -> bool:
        """Most features only work while the device is connected."""
        return self.device.connected

    async def async_added_to_hass(self) -> None:
        """Follow the device state."""
        self.async_on_remove(self.device.async_add_listener(self.async_write_ha_state))
