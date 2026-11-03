"""Send notifications to KDE Connect devices."""

from __future__ import annotations

from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .const import DOMAIN
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .kdeconnect.protocol import PACKET_TYPE_NOTIFICATION

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a notifier for devices that can show notifications."""
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.supports(PACKET_TYPE_NOTIFICATION):
            async_add_entities(
                [KdeConnectNotifier(device)], config_subentry_id=subentry_id
            )


class KdeConnectNotifier(KdeConnectEntity, NotifyEntity):
    """Shows a notification on the device."""

    _attr_name = None

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "notify")

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send the notification."""
        if not self.device.send_notification(message, title):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_connected",
                translation_placeholders={"name": self.device.name},
            )
