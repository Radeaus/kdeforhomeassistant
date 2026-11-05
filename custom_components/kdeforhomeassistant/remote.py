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
from .const import DOMAIN
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .kdeconnect.protocol import PACKET_TYPE_MOUSEPAD_REQUEST, SPECIAL_KEYS

PARALLEL_UPDATES = 0

MODIFIERS = ("ctrl", "alt", "shift", "super")

# Scroll distance of one step. Windows reads it as wheel units (120 is one
# notch), Wayland as pixels; X11 and GNOME scroll one notch per packet.
SCROLL_STEP = 60

# The buttons of the remote in the KDE Connect app, sent the same way.
REMOTE_BUTTONS: dict[str, dict[str, Any]] = {
    "up": {"specialKey": SPECIAL_KEYS["up"]},
    "down": {"specialKey": SPECIAL_KEYS["down"]},
    "left": {"specialKey": SPECIAL_KEYS["left"]},
    "right": {"specialKey": SPECIAL_KEYS["right"]},
    "select": {"specialKey": SPECIAL_KEYS["enter"]},
    "back": {"specialKey": SPECIAL_KEYS["escape"]},
    "home": {"super": True, "specialKey": SPECIAL_KEYS["super"]},
    "close": {"alt": True, "specialKey": SPECIAL_KEYS["f4"]},
}

MOUSE_ACTIONS: dict[str, dict[str, Any]] = {
    "click": {"singleclick": True},
    "double_click": {"doubleclick": True},
    "right_click": {"rightclick": True},
    "middle_click": {"middleclick": True},
    # Only the Android app reads these; middle click is home there.
    "android_back": {"backclick": True},
    "android_home": {"middleclick": True},
    "android_recents": {"forwardclick": True},
}

SCROLL_DIRECTIONS: dict[str, tuple[int, int]] = {
    "scroll_up": (0, 1),
    "scroll_down": (0, -1),
    "scroll_left": (-1, 0),
    "scroll_right": (1, 0),
}

COMMAND_NAMES = sorted(
    {*REMOTE_BUTTONS, *SPECIAL_KEYS, *MOUSE_ACTIONS, *SCROLL_DIRECTIONS}
)


def parse_command(command: str) -> dict[str, Any]:
    """Turn a command into the body of a mousepad packet.

    Raises ValueError for a command that is not understood.
    """
    if command.startswith("text:"):
        if not (text := command[len("text:") :]):
            raise ValueError(command)
        return {"key": text}
    name, _, argument = command.strip().partition(":")
    name = name.lower()
    if name == "move":
        try:
            dx, dy = (float(part) for part in argument.split(","))
        except ValueError:
            raise ValueError(command) from None
        if not dx and not dy:
            raise ValueError(command)
        return {"dx": dx, "dy": dy}
    if name in SCROLL_DIRECTIONS:
        try:
            step = float(argument) if argument else SCROLL_STEP
        except ValueError:
            raise ValueError(command) from None
        if step <= 0:
            raise ValueError(command)
        x, y = SCROLL_DIRECTIONS[name]
        return {"scroll": True, "dx": x * step, "dy": y * step}
    if argument:
        raise ValueError(command)
    if name in REMOTE_BUTTONS:
        return dict(REMOTE_BUTTONS[name])
    if name in MOUSE_ACTIONS:
        return dict(MOUSE_ACTIONS[name])

    # A key, with modifiers in front: "enter", "a", "ctrl+c", "alt+f4".
    stripped = command.strip()
    *modifiers, key = ["+"] if stripped == "+" else stripped.split("+")
    body: dict[str, Any] = {}
    for modifier in modifiers:
        if modifier.lower() not in MODIFIERS:
            raise ValueError(command)
        body[modifier.lower()] = True
    if key.lower() in SPECIAL_KEYS:
        body["specialKey"] = SPECIAL_KEYS[key.lower()]
    elif len(key) == 1:
        body["key"] = key
    else:
        raise ValueError(command)
    return body


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
