"""Buttons for KDE Connect devices: ring, wake up and run commands."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .const import DOMAIN
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .kdeconnect.protocol import PACKET_TYPE_FINDMYPHONE_REQUEST

PARALLEL_UPDATES = 0

COMMAND_PREFIX = "command_"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add buttons for every device."""
    registry = er.async_get(hass)
    for subentry_id, device in entry.runtime_data.devices.items():
        entities: list[ButtonEntity] = []
        if device.supports(PACKET_TYPE_FINDMYPHONE_REQUEST):
            entities.append(KdeConnectRingButton(device))
        if device.mac:
            entities.append(KdeConnectWakeButton(device))

        # Commands are only known once the device connects, so bring back
        # the ones we saw before; they stay unavailable until it does.
        prefix = f"{device.device_id}_{COMMAND_PREFIX}"
        known: set[str] = set()
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if reg_entry.domain == "button" and reg_entry.unique_id.startswith(prefix):
                key = reg_entry.unique_id.removeprefix(prefix)
                if key in device.hidden_commands:
                    # Removed from Home Assistant on the panel.
                    registry.async_remove(reg_entry.entity_id)
                    continue
                known.add(key)
                entities.append(
                    KdeConnectCommandButton(device, key, reg_entry.original_name or key)
                )
        async_add_entities(entities, config_subentry_id=subentry_id)

        def make_listener(
            device: KdeConnectDevice, subentry_id: str, known: set[str], prefix: str
        ) -> Callable[[], None]:
            @callback
            def commands_changed() -> None:
                wanted = {
                    key: command
                    for key, command in device.remote_commands.items()
                    if key not in device.hidden_commands
                }
                new = [
                    KdeConnectCommandButton(device, key, command["name"])
                    for key, command in wanted.items()
                    if key not in known
                ]
                known.update(wanted)
                if new:
                    async_add_entities(new, config_subentry_id=subentry_id)
                for key in list(known - set(wanted)):
                    known.discard(key)
                    if entity_id := registry.async_get_entity_id(
                        "button", DOMAIN, prefix + key
                    ):
                        registry.async_remove(entity_id)

            return commands_changed

        entry.async_on_unload(
            device.async_add_command_listener(
                make_listener(device, subentry_id, known, prefix)
            )
        )


def _not_connected(device: KdeConnectDevice) -> HomeAssistantError:
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="not_connected",
        translation_placeholders={"name": device.name},
    )


class KdeConnectRingButton(KdeConnectEntity, ButtonEntity):
    """Makes the device ring so you can find it."""

    _attr_translation_key = "ring"

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "ring")

    async def async_press(self) -> None:
        """Ring the device."""
        if not self.device.ring():
            raise _not_connected(self.device)


class KdeConnectWakeButton(KdeConnectEntity, ButtonEntity):
    """Turns the device on with Wake-on-LAN."""

    _attr_translation_key = "wake"

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "wake")

    @property
    def available(self) -> bool:
        """Waking only makes sense, and works, while the device is offline."""
        return True

    async def async_press(self) -> None:
        """Send the magic packet."""
        await self.device.async_wake()


class KdeConnectCommandButton(KdeConnectEntity, ButtonEntity):
    """Runs one of the commands set up on the device."""

    _attr_translation_key = "run_command"

    def __init__(self, device: KdeConnectDevice, key: str, name: str) -> None:
        super().__init__(device, f"{COMMAND_PREFIX}{key}")
        self._key = key
        self._attr_name = name

    @property
    def available(self) -> bool:
        """Only while the device is connected and still offers the command."""
        return self.device.connected and self._key in self.device.remote_commands

    @callback
    def _handle_update(self) -> None:
        if command := self.device.remote_commands.get(self._key):
            self._attr_name = command["name"]
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Follow the device, including renamed commands."""
        self.async_on_remove(self.device.async_add_listener(self._handle_update))

    async def async_press(self) -> None:
        """Run the command on the device."""
        if not self.available or not self.device.run_command(self._key):
            raise _not_connected(self.device)
