"""State and actions for one paired KDE Connect device."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import socket
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import PurePath
from typing import Any
from urllib.parse import urlsplit

from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CAPABILITIES,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_HIDDEN_COMMANDS,
    CONF_SCRIPTS,
    DOMAIN,
)
from .kdeconnect import KdeConnectHub, Packet
from .kdeconnect.protocol import (
    PACKET_TYPE_FINDMYPHONE_REQUEST,
    PACKET_TYPE_LOCK,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_MOUSEPAD_KEYBOARDSTATE,
    PACKET_TYPE_MOUSEPAD_REQUEST,
    PACKET_TYPE_MPRIS,
    PACKET_TYPE_MPRIS_REQUEST,
    PACKET_TYPE_NOTIFICATION,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    PACKET_TYPE_SHARE_REQUEST,
    PACKET_TYPE_SYSTEMVOLUME,
    PACKET_TYPE_SYSTEMVOLUME_REQUEST,
    pem_to_der,
)
from .notifications import (
    ACTION_ADDED,
    ACTION_REMOVED,
    ACTION_UPDATED,
    EVENT_NOTIFICATION,
    ICON_URL,
    MAX_ICON_SIZE,
    MAX_SHARED,
    DesktopNotificationChats,
    NotificationStore,
    async_get_icons,
    clean_app_name,
    is_chat_notification,
    notification_content,
)

_LOGGER = logging.getLogger(__name__)

WAKE_ON_LAN_PORT = 9

# PulseAudio and PipeWire report 100% as this value; their maxVolume is higher
# when volumes above 100% are allowed.
NORMAL_SINK_VOLUME = 65536

# The fields of a "kdeconnect.mpris" packet we keep per player.
PLAYER_FIELDS = (
    "title",
    "artist",
    "album",
    "albumArtUrl",
    "isPlaying",
    "pos",
    "length",
    "volume",
    "canPlay",
    "canPause",
    "canGoNext",
    "canGoPrevious",
    "canSeek",
)

# Run commands with one of these names take over the built-in ring and screen
# lock, which do not work on every desktop. The names are the ones the button
# helper on the panel asks the AI to use, in each language of the panel.
OWN_COMMAND_NAMES: dict[str, frozenset[str]] = {
    "ring": frozenset({"ring", "laten rinkelen"}),
    "lock": frozenset({"lock screen", "scherm vergrendelen"}),
    "unlock": frozenset({"unlock screen", "scherm ontgrendelen"}),
    "screenshot": frozenset({"screenshot", "schermafbeelding"}),
}

# Images a device may send us (its screen); anything else it shares is ignored.
IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
MAX_IMAGE_SIZE = 25 * 1024 * 1024
MAX_ARTWORK_SIZE = 5 * 1024 * 1024
MAX_ARTWORK_CACHE = 16
# Players may announce a new track before rewriting a reused artwork file.
ARTWORK_RETRY_DELAY = 2.0
ARTWORK_RETRIES = 3


class KdeConnectDevice:
    """A paired device, as seen from Home Assistant."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
        hub: KdeConnectHub,
        notifications: NotificationStore | None = None,
    ) -> None:
        self.hass = hass
        self.notifications = notifications
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
        self.hidden_commands: frozenset[str] = frozenset(
            data.get(CONF_HIDDEN_COMMANDS, ())
        )
        self.remote_commands: dict[str, dict[str, str]] = {}
        self.locked: bool | None = None
        self.players: dict[str, dict[str, Any]] = {}
        self.media_artwork: dict[str, tuple[str, bytes, str, str]] = {}
        self._requested_artwork: dict[str, tuple[str, str, str, str]] = {}
        self._artwork_retries: dict[str, tuple[tuple[str, str, str, str], int]] = {}
        self._artwork_retry_unsubs: dict[str, Callable[[], None]] = {}
        self.selected_player: str | None = None
        self.sinks: dict[str, dict[str, Any]] = {}
        self.can_type: bool | None = None
        # The last image the device shared, shown as its screen.
        self.screen: bytes | None = None
        self.screen_type = "image/png"
        self.screen_time: datetime | None = None
        self._listeners: list[Callable[[], None]] = []
        self._command_listeners: list[Callable[[], None]] = []
        self._notification_listeners: list[Callable[[dict[str, Any]], None]] = []
        # Notifications we passed on, by id, to report when they go away.
        self._shared_notifications: dict[str, str] = {}
        self._desktop_chats = DesktopNotificationChats()
        self._notification_icon_urls: dict[str, str] = {}
        self._notification_tokens: dict[str, object] = {}
        # Log a lost connection once, and once when it comes back.
        self._logged_unavailable = False

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
            self._cancel_artwork_retries()

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
    def async_add_notification_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        """Call the listener with every notification the device shares."""
        self._notification_listeners.append(listener)
        return lambda: self._notification_listeners.remove(listener)

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def _handle_connection(self, connected: bool) -> None:
        if connected and self._logged_unavailable:
            _LOGGER.info("%s is connected again", self.name)
            self._logged_unavailable = False
        elif not connected and not self._logged_unavailable:
            _LOGGER.info("%s is no longer connected", self.name)
            self._logged_unavailable = True
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
            if self.supports(PACKET_TYPE_MPRIS_REQUEST):
                self._send(PACKET_TYPE_MPRIS_REQUEST, {"requestPlayerList": True})
            if self.supports(PACKET_TYPE_SYSTEMVOLUME_REQUEST):
                self._send(PACKET_TYPE_SYSTEMVOLUME_REQUEST, {"requestSinks": True})
        else:
            self.locked = None
            self.players = {}
            self.media_artwork.clear()
            self._requested_artwork.clear()
            self._cancel_artwork_retries()
            self.sinks = {}
            self.can_type = None
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
        elif packet.type == PACKET_TYPE_MOUSEPAD_KEYBOARDSTATE:
            if isinstance(state := body.get("state"), bool):
                self.can_type = state
                self._notify()
        elif packet.type == PACKET_TYPE_SHARE_REQUEST:
            self._handle_share(packet)
        elif packet.type == PACKET_TYPE_MPRIS:
            self._handle_mpris(packet)
        elif packet.type == PACKET_TYPE_SYSTEMVOLUME:
            self._handle_systemvolume(body)
        elif packet.type == PACKET_TYPE_NOTIFICATION:
            self._handle_notification(packet)

    # Notifications the device shares with us

    @callback
    def _handle_notification(self, packet: Packet) -> None:
        body = packet.body
        notification_id = body.get("id")
        if self.notifications is None or not isinstance(notification_id, str):
            return
        source_id = notification_id
        if body.get("isCancel"):
            notification_id, keep_chat = self._desktop_chats.remove(source_id)
            if keep_chat:
                return
            self._notification_tokens.pop(notification_id, None)
            self._notification_icon_urls.pop(notification_id, None)
            if (
                app := self._shared_notifications.pop(notification_id, None)
            ) is not None:
                self._fire_notification(
                    {"action": ACTION_REMOVED, "id": notification_id, "app": app}
                )
            return
        app = clean_app_name(body.get("appName"))
        if self.notifications.async_seen(self.device_id, app):
            # A new app to choose on the panel.
            self._notify()
        silent = body.get("silent") is True
        if not self.notifications.get(self.device_id).shares(app, silent):
            return
        title, text = notification_content(body)
        if self.device_type in ("desktop", "laptop") and is_chat_notification(
            app, body
        ):
            notification_id, text = self._desktop_chats.add(
                source_id,
                app,
                title,
                text,
                complete=isinstance(body.get("conversation"), list)
                and bool(body["conversation"]),
            )
        if self._shared_notifications.get(notification_id) != app:
            self._notification_icon_urls.pop(notification_id, None)
        action = (
            ACTION_UPDATED
            if self._shared_notifications.get(notification_id) == app
            else ACTION_ADDED
        )
        self._shared_notifications.pop(notification_id, None)
        self._shared_notifications[notification_id] = app
        revision = self._notification_tokens[notification_id] = object()
        while len(self._shared_notifications) > MAX_SHARED:
            expired_id = next(iter(self._shared_notifications))
            del self._shared_notifications[expired_id]
            self._notification_icon_urls.pop(expired_id, None)
            self._notification_tokens.pop(expired_id, None)
        data: dict[str, Any] = {
            "action": action,
            "id": notification_id,
            "app": app,
            "title": title,
            "text": text,
            "ticker": _text(body.get("ticker")),
            "silent": silent,
            "icon_url": self._notification_icon_urls.get(notification_id),
        }
        if notification_id != source_id:
            data["source_id"] = source_id
        size, port = packet.payload_size, packet.payload_port
        if size is not None and port is not None and 0 < size <= MAX_ICON_SIZE:
            self.entry.async_create_background_task(
                self.hass,
                self._async_notification_with_icon(data, port, size, revision),
                f"{self.name} notification icon",
            )
        else:
            self._fire_notification(data)

    async def _async_notification_with_icon(
        self, data: dict[str, Any], port: int, size: int, revision: object
    ) -> None:
        try:
            icon = await self.hub.async_download_payload(self.device_id, port, size)
        except (OSError, TimeoutError) as err:
            _LOGGER.debug("No icon for a notification of %s: %s", self.name, err)
        else:
            if self._notification_tokens.get(data["id"]) is not revision:
                return
            token = async_get_icons(self.hass).add(icon)
            path = f"{ICON_URL}/{token}.png"
            try:
                base = get_url(self.hass, prefer_external=False)
            except NoURLAvailableError:
                base = ""
            data["icon_url"] = base + path
            if data["id"] in self._shared_notifications:
                self._notification_icon_urls[data["id"]] = data["icon_url"]
        if self._notification_tokens.get(data["id"]) is revision:
            self._fire_notification(data)

    @callback
    def _fire_notification(self, data: dict[str, Any]) -> None:
        registry_device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, self.device_id)}
        )
        data = {
            "device_id": registry_device.id if registry_device else None,
            "device_name": self.name,
            **data,
        }
        self.hass.bus.async_fire(EVENT_NOTIFICATION, data)
        for listener in list(self._notification_listeners):
            listener(data)

    def _handle_share(self, packet: Packet) -> None:
        filename = packet.body.get("filename")
        size, port = packet.payload_size, packet.payload_port
        if not isinstance(filename, str) or size is None or port is None:
            return
        content_type = IMAGE_TYPES.get(PurePath(filename).suffix.lower())
        if content_type is None or not 0 < size <= MAX_IMAGE_SIZE:
            _LOGGER.debug("Ignoring %s shared by %s", filename, self.name)
            return
        self.entry.async_create_background_task(
            self.hass,
            self._async_receive_screen(port, size, content_type),
            f"{self.name} screen",
        )

    async def _async_receive_screen(
        self, port: int, size: int, content_type: str
    ) -> None:
        try:
            data = await self.hub.async_download_payload(self.device_id, port, size)
        except OSError as err:
            _LOGGER.warning("Could not receive the screen of %s: %s", self.name, err)
            return
        self.screen = data
        self.screen_type = content_type
        self.screen_time = dt_util.utcnow()
        self._notify()

    def take_screenshot(self) -> bool:
        """Run the device's Screenshot command, which shares its screen with us."""
        if (key := self.own_command("screenshot")) is None:
            return False
        return self.run_command(key)

    def _handle_mpris(self, packet: Packet) -> None:
        body = packet.body
        if body.get("transferringAlbumArt") is True:
            self._handle_artwork(packet)
            return
        if isinstance(names := body.get("playerList"), list):
            names = [name for name in names if isinstance(name, str)]
            self.players = {name: self.players.get(name, {}) for name in names}
            self.media_artwork = {
                name: art
                for name, art in self.media_artwork.items()
                if name in self.players
            }
            self._requested_artwork = {
                name: request
                for name, request in self._requested_artwork.items()
                if name in self.players
            }
            for name in names:
                self._send(
                    PACKET_TYPE_MPRIS_REQUEST,
                    {"player": name, "requestNowPlaying": True, "requestVolume": True},
                )
        elif isinstance(name := body.get("player"), str) and name in self.players:
            player = self.players[name]
            player.update({key: body[key] for key in PLAYER_FIELDS if key in body})
            if "pos" in body:
                player["posUpdatedAt"] = dt_util.utcnow()
            if "albumArtUrl" in body:
                url = body["albumArtUrl"]
                if name in self.media_artwork and self.media_artwork[name][0] != url:
                    self.media_artwork.pop(name)
                if isinstance(url, str) and url.startswith("file://"):
                    request = (
                        url,
                        str(player.get("title", "")),
                        str(player.get("artist", "")),
                        str(player.get("album", "")),
                    )
                    if self._requested_artwork.get(name) != request:
                        self._requested_artwork[name] = request
                        self._send(
                            PACKET_TYPE_MPRIS_REQUEST,
                            {"player": name, "albumArtUrl": url},
                        )
                else:
                    self._requested_artwork.pop(name, None)
                    self._store_inline_artwork(name, url)
        else:
            return
        self._notify()

    def _store_inline_artwork(self, name: str, url: Any) -> None:
        """Decode artwork that a player embeds as a base64 data: URL."""
        if not isinstance(url, str) or not url.startswith("data:image/"):
            return
        header, _, encoded = url.partition(",")
        content_type, _, encoding = header[5:].partition(";")
        if encoding != "base64" or len(encoded) > MAX_ARTWORK_SIZE * 4 // 3 + 4:
            return
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            return
        if not data or content_type not in IMAGE_TYPES.values():
            return
        self.media_artwork[name] = (
            url,
            data,
            content_type,
            hashlib.sha256(data).hexdigest()[:16],
        )
        while len(self.media_artwork) > MAX_ARTWORK_CACHE:
            self.media_artwork.pop(next(iter(self.media_artwork)))

    def _handle_artwork(self, packet: Packet) -> None:
        name, url = packet.body.get("player"), packet.body.get("albumArtUrl")
        if not isinstance(name, str) or not isinstance(url, str):
            return
        request = self._requested_artwork.get(name)
        if (
            not request
            or request[0] != url
            or self.players.get(name, {}).get("albumArtUrl") != url
        ):
            return
        size, port = packet.payload_size, packet.payload_port
        if size is None or port is None or not 0 < size <= MAX_ARTWORK_SIZE:
            return
        self.entry.async_create_background_task(
            self.hass,
            self._async_receive_artwork(name, url, port, size, request),
            f"{self.name} media artwork",
        )

    async def _async_receive_artwork(
        self,
        name: str,
        url: str,
        port: int,
        size: int,
        request: tuple[str, str, str, str],
    ) -> None:
        try:
            data = await self.hub.async_download_payload(self.device_id, port, size)
        except (OSError, TimeoutError) as err:
            _LOGGER.debug("Could not receive artwork from %s: %s", self.name, err)
            return
        if (
            self.players.get(name, {}).get("albumArtUrl") != url
            or self._requested_artwork.get(name) != request
        ):
            return
        content_type = IMAGE_TYPES.get(PurePath(urlsplit(url).path).suffix.lower())
        if content_type is None:
            return
        previous = self.media_artwork.get(name)
        if previous and previous[0] == url and previous[1] == data:
            self._schedule_artwork_retry(name, url, request)
            return
        self._artwork_retries.pop(name, None)
        self.media_artwork[name] = (
            url,
            data,
            content_type,
            hashlib.sha256(data).hexdigest()[:16],
        )
        while len(self.media_artwork) > MAX_ARTWORK_CACHE:
            self.media_artwork.pop(next(iter(self.media_artwork)))
        self._notify()

    def _schedule_artwork_retry(
        self, name: str, url: str, request: tuple[str, str, str, str]
    ) -> None:
        """Ask again for a reused artwork file that still holds the old image."""
        previous_request, count = self._artwork_retries.get(name, (request, 0))
        if previous_request != request:
            count = 0
        if count >= ARTWORK_RETRIES:
            return
        self._artwork_retries[name] = (request, count + 1)
        if unsub := self._artwork_retry_unsubs.pop(name, None):
            unsub()

        @callback
        def _retry(_now: datetime) -> None:
            self._artwork_retry_unsubs.pop(name, None)
            if (
                self._requested_artwork.get(name) == request
                and self.players.get(name, {}).get("albumArtUrl") == url
            ):
                self._send(
                    PACKET_TYPE_MPRIS_REQUEST, {"player": name, "albumArtUrl": url}
                )

        self._artwork_retry_unsubs[name] = async_call_later(
            self.hass, ARTWORK_RETRY_DELAY, _retry
        )

    def _cancel_artwork_retries(self) -> None:
        for unsub in self._artwork_retry_unsubs.values():
            unsub()
        self._artwork_retry_unsubs.clear()
        self._artwork_retries.clear()

    def _handle_systemvolume(self, body: dict[str, Any]) -> None:
        if isinstance(sink_list := body.get("sinkList"), list):
            self.sinks = {
                sink["name"]: dict(sink)
                for sink in sink_list
                if isinstance(sink, dict) and isinstance(sink.get("name"), str)
            }
        elif isinstance(name := body.get("name"), str) and name in self.sinks:
            if body.get("enabled") is True:
                for sink in self.sinks.values():
                    sink["enabled"] = False
            self.sinks[name].update(
                {
                    key: body[key]
                    for key in ("volume", "muted", "enabled", "maxVolume")
                    if key in body
                }
            )
        else:
            return
        self._notify()

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

    def open_command_setup(self) -> bool:
        """Open the run command settings on the device, to add commands."""
        return self._send(PACKET_TYPE_RUNCOMMAND_REQUEST, {"setup": True})

    def own_command(self, role: str) -> str | None:
        """Return the key of the run command that takes over ring, lock or unlock."""
        names = OWN_COMMAND_NAMES[role]
        for key, command in self.remote_commands.items():
            if command["name"].strip().casefold() in names:
                return key
        return None

    def ring(self) -> bool:
        """Make the device ring, with its own command or the find-my-device sound."""
        if key := self.own_command("ring"):
            return self.run_command(key)
        return self._send(PACKET_TYPE_FINDMYPHONE_REQUEST, {})

    def set_locked(self, locked: bool) -> bool:
        """Lock or unlock the device's screen."""
        if key := self.own_command("lock" if locked else "unlock"):
            # A command does not report back, so assume it worked.
            if not self.run_command(key):
                return False
            self.locked = locked
            self._notify()
            return True
        return self._send(PACKET_TYPE_LOCK_REQUEST, {"setLocked": locked})

    # Keyboard and mouse

    def send_input(self, body: dict[str, Any]) -> bool:
        """Send a key, text or mouse action, like the KDE Connect remote does."""
        return self._send(PACKET_TYPE_MOUSEPAD_REQUEST, body)

    # Media

    @property
    def active_player(self) -> str | None:
        """Return the player that media controls act on."""
        if self.selected_player in self.players:
            return self.selected_player
        for name, player in self.players.items():
            if player.get("isPlaying"):
                return name
        return next(iter(self.players), None)

    @property
    def default_sink(self) -> dict[str, Any] | None:
        """Return the audio output the device uses, if it reports one."""
        for sink in self.sinks.values():
            if sink.get("enabled"):
                return sink
        return next(iter(self.sinks.values()), None)

    @property
    def volume_level(self) -> float | None:
        """Return the volume from 0 to 1."""
        if (sink := self.default_sink) is not None:
            volume = sink.get("volume")
            if isinstance(volume, int | float):
                return max(0.0, min(1.0, volume / _normal_volume(sink)))
            return None
        if (name := self.active_player) is not None:
            volume = self.players[name].get("volume")
            if isinstance(volume, int | float):
                return max(0.0, min(1.0, volume / 100))
        return None

    @property
    def muted(self) -> bool | None:
        """Return whether the audio output is muted."""
        if (sink := self.default_sink) is not None:
            muted = sink.get("muted")
            return muted if isinstance(muted, bool) else None
        return None

    def select_player(self, name: str) -> None:
        """Make media controls act on this player."""
        self.selected_player = name
        self._notify()

    def media_action(self, action: str) -> bool:
        """Send Play, Pause, PlayPause, Stop, Next or Previous to the player."""
        if (name := self.active_player) is None:
            return False
        return self._send(PACKET_TYPE_MPRIS_REQUEST, {"player": name, "action": action})

    def media_seek(self, position_ms: int) -> bool:
        """Jump to a position in the current track."""
        if (name := self.active_player) is None:
            return False
        return self._send(
            PACKET_TYPE_MPRIS_REQUEST, {"player": name, "SetPosition": position_ms}
        )

    def set_volume(self, level: float) -> bool:
        """Set the volume of the audio output, or else of the player."""
        if (sink := self.default_sink) is not None:
            return self._send(
                PACKET_TYPE_SYSTEMVOLUME_REQUEST,
                {"name": sink["name"], "volume": round(level * _normal_volume(sink))},
            )
        if (name := self.active_player) is not None:
            return self._send(
                PACKET_TYPE_MPRIS_REQUEST,
                {"player": name, "setVolume": round(level * 100)},
            )
        return False

    def set_muted(self, muted: bool) -> bool:
        """Mute or unmute the audio output."""
        if (sink := self.default_sink) is None:
            return False
        return self._send(
            PACKET_TYPE_SYSTEMVOLUME_REQUEST, {"name": sink["name"], "muted": muted}
        )

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


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _normal_volume(sink: dict[str, Any]) -> int:
    """Return the sink volume that means 100%."""
    maximum = sink.get("maxVolume")
    if not isinstance(maximum, int) or maximum <= 0:
        return NORMAL_SINK_VOLUME
    return min(maximum, NORMAL_SINK_VOLUME)


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
