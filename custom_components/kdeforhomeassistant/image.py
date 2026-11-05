"""Show the screen of a KDE Connect device."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .kdeconnect.protocol import PACKET_TYPE_SHARE_REQUEST

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a screen for devices that can share files."""
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.supports(PACKET_TYPE_SHARE_REQUEST):
            async_add_entities(
                [KdeConnectScreen(hass, device)], config_subentry_id=subentry_id
            )


class KdeConnectScreen(KdeConnectEntity, ImageEntity):
    """The last screenshot the device sent.

    Its Screenshot run command takes one and shares it with Home Assistant.
    """

    _attr_translation_key = "screen"

    def __init__(self, hass: HomeAssistant, device: KdeConnectDevice) -> None:
        KdeConnectEntity.__init__(self, device, "screen")
        ImageEntity.__init__(self, hass)

    @property
    def available(self) -> bool:
        """Keep showing the last screenshot while the device is away."""
        return True

    @property
    def content_type(self) -> str:
        """Return the image type."""
        return self.device.screen_type

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the screenshot arrived."""
        return self.device.screen_time

    async def async_image(self) -> bytes | None:
        """Return the screenshot."""
        return self.device.screen
