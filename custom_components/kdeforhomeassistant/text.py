"""Type text on a KDE Connect device."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .const import DOMAIN
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .kdeconnect.protocol import PACKET_TYPE_MOUSEPAD_REQUEST

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a keyboard for devices that accept keyboard input."""
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.supports(PACKET_TYPE_MOUSEPAD_REQUEST):
            async_add_entities(
                [KdeConnectKeyboard(device)], config_subentry_id=subentry_id
            )


class KdeConnectKeyboard(KdeConnectEntity, TextEntity):
    """Whatever is set here is typed on the device, then the field clears."""

    _attr_translation_key = "keyboard"
    _attr_mode = TextMode.TEXT
    _attr_native_max = 255
    _attr_native_value = ""

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "keyboard")

    async def async_set_value(self, value: str) -> None:
        """Type the text on the device."""
        if value and not self.device.send_input({"key": value}):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_connected",
                translation_placeholders={"name": self.device.name},
            )
