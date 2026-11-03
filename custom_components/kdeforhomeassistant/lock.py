"""Lock and unlock the screen of KDE Connect devices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .const import DOMAIN
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .kdeconnect.protocol import PACKET_TYPE_LOCK_REQUEST

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a screen lock for devices that support it."""
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.supports(PACKET_TYPE_LOCK_REQUEST):
            async_add_entities(
                [KdeConnectScreenLock(device)], config_subentry_id=subentry_id
            )


class KdeConnectScreenLock(KdeConnectEntity, LockEntity):
    """The screen lock of a computer or phone."""

    _attr_translation_key = "screen"

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "screen_lock")

    @property
    def is_locked(self) -> bool | None:
        """Return whether the screen is locked."""
        return self.device.locked

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the screen."""
        self._set(True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the screen."""
        self._set(False)

    def _set(self, locked: bool) -> None:
        if not self.device.set_locked(locked):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_connected",
                translation_placeholders={"name": self.device.name},
            )
