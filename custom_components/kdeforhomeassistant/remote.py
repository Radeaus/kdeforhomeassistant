"""Control a KDE Connect device with keys and mouse actions, like a remote."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .commands import COMMAND_NAMES, parse_command
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
    """Add a remote for devices that accept keyboard and mouse input."""
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.supports(PACKET_TYPE_MOUSEPAD_REQUEST):
            async_add_entities(
                [KdeConnectRemote(device)], config_subentry_id=subentry_id
            )


class KdeConnectRemote(KdeConnectEntity, RemoteEntity):
    """Send keys, text and mouse actions to a computer or phone."""

    _attr_translation_key = "remote"

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "remote")

    @property
    def available(self) -> bool:
        """Stay available, so the device can be woken up with turn_on."""
        return True

    @property
    def is_on(self) -> bool:
        """Return whether the device is connected."""
        return self.device.connected

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Wake the device up, when it has a MAC address."""
        if not self.device.mac:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="no_wake",
                translation_placeholders={"name": self.device.name},
            )
        await self.device.async_wake()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turning a device off is not possible through KDE Connect."""
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="not_supported",
            translation_placeholders={"name": self.device.name},
        )

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send the commands in order, num_repeats times."""
        bodies = []
        for item in command:
            try:
                bodies.append(parse_command(item))
            except ValueError:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="unknown_command",
                    translation_placeholders={
                        "command": item,
                        "commands": ", ".join(COMMAND_NAMES),
                    },
                ) from None
        repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)
        for repeat in range(repeats):
            for index, body in enumerate(bodies):
                if repeat or index:
                    await asyncio.sleep(delay)
                if not self.device.send_input(body):
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="not_connected",
                        translation_placeholders={"name": self.device.name},
                    )
