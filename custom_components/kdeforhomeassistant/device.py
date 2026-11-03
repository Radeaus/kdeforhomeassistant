"""State and actions for one paired KDE Connect device."""

from __future__ import annotations

import json
import logging
import socket
import uuid
from collections.abc import Callable
from typing import Any

from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_CAPABILITIES,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_SCRIPTS,
    DOMAIN,
)
from .kdeconnect import KdeConnectHub, Packet
from .kdeconnect.protocol import (
    PACKET_TYPE_FINDMYPHONE_REQUEST,
    PACKET_TYPE_LOCK,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_NOTIFICATION,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    pem_to_der,
)

_LOGGER = logging.getLogger(__name__)

WAKE_ON_LAN_PORT = 9


class KdeConnectDevice:
    """A paired device, as seen from Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
        hub: KdeConnectHub,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.subentry = subentry
        self.subentry_id = subentry.subentry_id
        self.hub = hub
        data = subentry.data
        self.device_id: str = data[CONF_DEVICE_ID]
        self.name: str = data.get(CONF_NAME) or subentry.title
        self.device_type: str = data.get(CONF_DEVICE_TYPE, "unknown")
        self.certificate_der = pem_to_der(data["certificate"])
        self.capabilities: frozenset[str] = frozenset(data.get(CONF_CAPABILITIES, ()))
        self.mac: str | None = data.get(CONF_MAC) or None
        self.scripts: list[str] = list(data.get(CONF_SCRIPTS, ()))
        self.remote_commands: dict[str, dict[str, str]] = {}
        self.locked: bool | None = None
        self._listeners: list[Callable[[], None]] = []
        self._command_listeners: list[Callable[[], None]] = []

    @property
    def connected(self) -> bool:
        """Return whether the device is connected right now."""
        return self.hub.is_connected(self.device_id)

    def supports(self, packet_type: str) -> bool:
        """Return whether the device accepts this packet type."""
        info = self.hub.connected_info(self.device_id)
        if info is not None and info.incoming_capabilities:
            return packet_type in info.incoming_capabilities
        return packet_type in self.capabilities

    @callback
    def async_start(self) -> Callable[[], None]:
        """Start listening to the hub; returns a function that stops it."""
        unsubs = [
            self.hub.add_packet_listener(self.device_id, self._handle_packet),
            self.hub.add_connection_listener(self.device_id, self._handle_connection),
        ]
        if self.connected:
            self._handle_connection(True)

        def stop() -> None:
            for unsub in unsubs:
                unsub()

        return stop

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Call the listener on every state change."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def async_add_command_listener(
        self, listener: Callable[[], None]
    ) -> Callable[[], None]:
        """Call the listener when the device sends a new command list."""
        self._command_listeners.append(listener)
        return lambda: self._command_listeners.remove(listener)

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def _handle_connection(self, connected: bool) -> None:
        if connected:
            ir.async_delete_issue(self.hass, DOMAIN, f"unpaired_{self.device_id}")
            info = self.hub.connected_info(self.device_id)
            if (
                info
                and info.incoming_capabilities
                and info.incoming_capabilities != self.capabilities
            ):
                # Entities depend on what the device supports; this reloads the entry.
                self.hass.config_entries.async_update_subentry(
                    self.entry,
                    self.subentry,
                    data={
                        **self.subentry.data,
                        CONF_CAPABILITIES: sorted(info.incoming_capabilities),
                    },
                )
                return
            self.send_command_list()
            self._send(PACKET_TYPE_RUNCOMMAND_REQUEST, {"requestCommandList": True})
            self._send(PACKET_TYPE_LOCK_REQUEST, {"requestLocked": True})
        else:
            self.locked = None
        self._notify()

    @callback
    def _handle_packet(self, packet: Packet) -> None:
        body = packet.body
        if packet.type == PACKET_TYPE_RUNCOMMAND:
            self._handle_command_list(body.get("commandList"))
        elif packet.type == PACKET_TYPE_RUNCOMMAND_REQUEST:
            if body.get("requestCommandList"):
                self.send_command_list()
            elif isinstance(key := body.get("key"), str):
                self._run_script(key)
        elif packet.type == PACKET_TYPE_LOCK:
            if isinstance(locked := body.get("isLocked"), bool):
                self.locked = locked
                self._notify()
            elif body.get("lockResult") is not None:
                self._send(PACKET_TYPE_LOCK_REQUEST, {"requestLocked": True})

    def _handle_command_list(self, raw: Any) -> None:
        try:
            commands = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return
        if not isinstance(commands, dict):
            return
        self.remote_commands = {
            key: {
                "name": str(value.get("name") or key),
                "command": str(value.get("command", "")),
            }
            for key, value in commands.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
        for listener in list(self._command_listeners):
            listener()
        self._notify()

    # Actions

    def _send(self, packet_type: str, body: dict[str, Any]) -> bool:
        return self.hub.send(self.device_id, Packet(packet_type, body))

    @callback
    def send_command_list(self) -> None:
        """Offer the configured scripts as commands the device can run."""
        commands = {}
        for entity_id in self.scripts:
            state = self.hass.states.get(entity_id)
            name = state.name if state else entity_id
            commands[entity_id] = {
                "name": name,
                "command": f"Home Assistant: {entity_id}",
            }
        self._send(
            PACKET_TYPE_RUNCOMMAND,
            {"commandList": json.dumps(commands), "canAddCommand": False},
        )

    @callback
    def _run_script(self, entity_id: str) -> None:
        if entity_id not in self.scripts:
            _LOGGER.warning(
                "%s asked to run %s, which is not shared with it", self.name, entity_id
            )
            return
        self.hass.async_create_task(
            self.hass.services.async_call(
                "script", "turn_on", {"entity_id": entity_id}, blocking=False
            )
        )

    def run_command(self, key: str) -> bool:
        """Run one of the commands the device offers."""
        return self._send(PACKET_TYPE_RUNCOMMAND_REQUEST, {"key": key})

    def ring(self) -> bool:
        """Make the device play its find-my-device sound."""
        return self._send(PACKET_TYPE_FINDMYPHONE_REQUEST, {})

    def set_locked(self, locked: bool) -> bool:
        """Lock or unlock the device's screen."""
        return self._send(PACKET_TYPE_LOCK_REQUEST, {"setLocked": locked})

    def send_notification(self, message: str, title: str | None) -> bool:
        """Show a notification on the device."""
        title = title or "Home Assistant"
        return self._send(
            PACKET_TYPE_NOTIFICATION,
            {
                "id": uuid.uuid4().hex,
                "appName": "Home Assistant",
                "title": title,
                "text": message,
                "ticker": f"{title}: {message}",
                "isClearable": True,
            },
        )

    async def async_wake(self) -> None:
        """Send a Wake-on-LAN magic packet."""
        if not self.mac:
            return
        mac = bytes.fromhex(self.mac.replace(":", "").replace("-", ""))
        packet = b"\xff" * 6 + mac * 16
        addresses = {
            str(address)
            for address in await network.async_get_ipv4_broadcast_addresses(self.hass)
        }
        if (info := self.hub.discovered.get(self.device_id)) and info.host:
            addresses.add(info.host)
        await self.hass.async_add_executor_job(_send_magic_packet, packet, addresses)


def _send_magic_packet(packet: bytes, addresses: set[str]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for address in addresses or {"255.255.255.255"}:
            try:
                sock.sendto(packet, (address, WAKE_ON_LAN_PORT))
            except OSError as err:
                _LOGGER.debug(
                    "Could not send Wake-on-LAN packet to %s: %s", address, err
                )


def read_mac_address(host: str) -> str | None:
    """Look up the MAC address of a host in the ARP table."""
    try:
        with open("/proc/net/arp", encoding="ascii") as file:
            next(file)
            for line in file:
                fields = line.split()
                if (
                    len(fields) >= 4
                    and fields[0] == host
                    and fields[3] != "00:00:00:00:00:00"
                ):
                    return fields[3].lower()
    except (OSError, StopIteration):
        pass
    return None
