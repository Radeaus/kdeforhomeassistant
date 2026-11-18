"""Notifications a KDE Connect device shares with Home Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .notifications import ACTION_ADDED, ACTION_REMOVED, ACTION_UPDATED

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a notification event for every device.

    Any device can share notifications; whether it does is chosen on the panel.
    """
    for subentry_id, device in entry.runtime_data.devices.items():
        async_add_entities(
            [KdeConnectNotificationEvent(device)], config_subentry_id=subentry_id
        )


class KdeConnectNotificationEvent(KdeConnectEntity, EventEntity):
    """Fires when the device shares, updates or removes a notification."""

    _attr_translation_key = "notification"

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "notification")
        self._attr_event_types = [ACTION_ADDED, ACTION_UPDATED, ACTION_REMOVED]

    @property
    def available(self) -> bool:
        """Keep showing the last notification while the device is away."""
        return True

    async def async_added_to_hass(self) -> None:
        """Follow the notifications of the device."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.device.async_add_notification_listener(self._handle_notification)
        )

    @callback
    def _handle_notification(self, data: dict[str, Any]) -> None:
        attributes = {
            key: value
            for key, value in data.items()
            if key not in ("action", "device_id", "device_name")
        }
        self._trigger_event(data["action"], attributes)
        self.async_write_ha_state()
