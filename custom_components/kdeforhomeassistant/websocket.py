"""The API the KDE for Home Assistant panel uses."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import network, websocket_api
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .const import (
    CONF_CAPABILITIES,
    CONF_CERTIFICATE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_HIDDEN_COMMANDS,
    CONF_SCRIPTS,
    CONNECT_TIMEOUT,
    DOMAIN,
    SIGNAL_UPDATE,
    SUBENTRY_TYPE_DEVICE,
    default_name,
)
from .device import read_mac_address
from .kdeconnect import DeviceInfo, PairingError
from .kdeconnect.protocol import der_to_pem, filter_device_name

if TYPE_CHECKING:
    from . import KdeConnectConfigEntry
    from .kdeconnect import KdeConnectHub

DISCOVERY_INTERVAL = timedelta(seconds=3)
UPDATE_DELAY = 0.2
COMMAND_PREFIX = "command_"
MAC_RE = r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$"
ENTITY_KEYS = (
    "connected",
    "screen_lock",
    "media_player",
    "remote",
    "keyboard",
    "notify",
    "ring",
    "wake",
)


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register every command."""
    for command in (
        ws_subscribe,
        ws_discover,
        ws_connect,
        ws_pair,
        ws_accept,
        ws_decline,
        ws_set_name,
        ws_update_device,
        ws_remove_device,
        ws_command_setup,
    ):
        websocket_api.async_register_command(hass, command)


def _entry(hass: HomeAssistant) -> KdeConnectConfigEntry | None:
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _loaded_entry(hass: HomeAssistant) -> KdeConnectConfigEntry | None:
    entry = _entry(hass)
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        return None
    return entry


def _hub(hass: HomeAssistant) -> KdeConnectHub | None:
    entry = _loaded_entry(hass)
    return entry.runtime_data.hub if entry else None


async def _broadcast_hosts(hass: HomeAssistant) -> set[str]:
    return {
        str(address)
        for address in await network.async_get_ipv4_broadcast_addresses(hass)
    }


@callback
def build_state(hass: HomeAssistant) -> dict[str, Any]:
    """Describe everything the panel shows."""
    entry = _entry(hass)
    if entry is None:
        return {"configured": False}
    loaded = entry.state is ConfigEntryState.LOADED
    hub = entry.runtime_data.hub if loaded else None
    runtime_devices = entry.runtime_data.devices if loaded else {}
    registry = er.async_get(hass)
    entities = {
        reg.unique_id: reg
        for reg in er.async_entries_for_config_entry(registry, entry.entry_id)
    }

    devices = []
    paired: set[str] = set()
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_DEVICE:
            continue
        data = subentry.data
        device_id = data[CONF_DEVICE_ID]
        paired.add(device_id)
        device = runtime_devices.get(subentry.subentry_id)
        hidden = set(data.get(CONF_HIDDEN_COMMANDS, []))
        prefix = f"{device_id}_{COMMAND_PREFIX}"
        commands: dict[str, dict[str, Any]] = {}
        for unique_id, reg in entities.items():
            if unique_id.startswith(prefix):
                key = unique_id.removeprefix(prefix)
                commands[key] = {
                    "key": key,
                    "name": reg.name or reg.original_name or key,
                    "command": None,
                    "entity_id": reg.entity_id,
                }
        if device is not None:
            for key, command in device.remote_commands.items():
                reg = entities.get(prefix + key)
                commands[key] = {
                    "key": key,
                    "name": command["name"],
                    "command": command["command"],
                    "entity_id": reg.entity_id if reg else None,
                }
        for key, command in commands.items():
            command["hidden"] = key in hidden
            if key in hidden:
                command["entity_id"] = None
        devices.append(
            {
                "id": subentry.subentry_id,
                "device_id": device_id,
                "name": data.get(CONF_NAME) or subentry.title,
                "type": data.get(CONF_DEVICE_TYPE, "unknown"),
                "connected": bool(device and device.connected),
                "mac": data.get(CONF_MAC),
                "scripts": list(data.get(CONF_SCRIPTS, [])),
                "commands": sorted(
                    commands.values(), key=lambda item: item["name"].lower()
                ),
                "entities": {
                    key: reg.entity_id
                    for key in ENTITY_KEYS
                    if (reg := entities.get(f"{device_id}_{key}"))
                },
            }
        )

    discovered = []
    requests = []
    if hub is not None:
        discovered = [
            {
                "device_id": info.device_id,
                "name": info.name,
                "type": info.device_type,
                "host": info.host,
                "reachable": hub.is_link_connected(info.device_id),
            }
            for info in hub.discovered.values()
            if info.device_id not in paired
        ]
        requests = [
            {
                "device_id": device_id,
                "name": request.info.name,
                "type": request.info.device_type,
                "key": request.verification_key,
            }
            for device_id, request in hub.incoming.items()
        ]

    return {
        "configured": True,
        "loaded": loaded,
        "reason": None if loaded else entry.reason,
        "name": entry.options.get(CONF_NAME) or entry.title,
        "default_name": default_name(hass.config.location_name),
        "devices": sorted(devices, key=lambda item: item["name"].lower()),
        "discovered": sorted(discovered, key=lambda item: item["name"].lower()),
        "requests": requests,
    }


async def _add_device(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    info: DeviceInfo,
    certificate: bytes,
) -> str:
    """Store a freshly paired device; the entry reloads with it."""
    mac = None
    if info.host:
        mac = await hass.async_add_executor_job(read_mac_address, info.host)
    subentry = ConfigSubentry(
        data={
            CONF_DEVICE_ID: info.device_id,
            CONF_NAME: info.name,
            CONF_DEVICE_TYPE: info.device_type,
            CONF_CERTIFICATE: der_to_pem(certificate),
            CONF_CAPABILITIES: sorted(info.incoming_capabilities),
            CONF_MAC: mac,
            CONF_SCRIPTS: [],
        },
        subentry_type=SUBENTRY_TYPE_DEVICE,
        title=info.name,
        unique_id=info.device_id,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry.subentry_id


def _is_paired(entry: KdeConnectConfigEntry, device_id: str) -> bool:
    return any(
        subentry.unique_id == device_id for subentry in entry.subentries.values()
    )


def _not_loaded(connection: websocket_api.ActiveConnection, msg_id: int) -> None:
    connection.send_error(msg_id, "not_loaded", "KDE for Home Assistant is not running")


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@websocket_api.require_admin
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Send the state now and whenever it changes."""
    pending: Callable[[], None] | None = None

    @callback
    def send(_now: Any = None) -> None:
        nonlocal pending
        pending = None
        connection.send_message(
            websocket_api.event_message(msg["id"], build_state(hass))
        )

    @callback
    def schedule(*_args: Any) -> None:
        nonlocal pending
        if pending is None:
            pending = async_call_later(hass, UPDATE_DELAY, send)

    unsubs = [
        async_dispatcher_connect(hass, SIGNAL_UPDATE, schedule),
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, schedule),
    ]

    @callback
    def unsubscribe() -> None:
        for unsub in unsubs:
            unsub()
        if pending is not None:
            pending()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send()


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/discover"})
@websocket_api.require_admin
@callback
def ws_discover(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Look for unpaired devices for as long as the panel keeps this open."""
    token: tuple[KdeConnectHub, Callable[[], None]] | None = None

    async def tick(_now: Any = None) -> None:
        nonlocal token
        hub = _hub(hass)
        if token is not None and token[0] is not hub:
            token[1]()
            token = None
        if hub is None:
            return
        if token is None:
            token = (hub, hub.start_discovery())
        hub.announce(await _broadcast_hosts(hass))

    unsub_timer = async_track_time_interval(hass, tick, DISCOVERY_INTERVAL)

    @callback
    def unsubscribe() -> None:
        unsub_timer()
        if token is not None:
            token[1]()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    hass.async_create_task(tick(), eager_start=False)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/connect", vol.Required("host"): cv.string}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_connect(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Ask the device at an address to connect, and return its id."""
    host = msg["host"].strip()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + CONNECT_TIMEOUT
    while loop.time() < deadline:
        hub = _hub(hass)
        if hub is None:
            _not_loaded(connection, msg["id"])
            return
        for device_id, info in hub.discovered.items():
            if info.host == host and hub.is_link_connected(device_id):
                connection.send_result(msg["id"], {"device_id": device_id})
                return
        hub.announce([host])
        await asyncio.sleep(1)
    connection.send_error(msg["id"], "not_found", "The device did not connect")


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/pair", vol.Required("device_id"): cv.string}
)
@websocket_api.require_admin
@callback
def ws_pair(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Send a pairing request; events tell the key, then the outcome."""
    entry = _loaded_entry(hass)
    if entry is None:
        _not_loaded(connection, msg["id"])
        return
    device_id = msg["device_id"]
    if _is_paired(entry, device_id):
        connection.send_error(msg["id"], "already_paired", "Already paired")
        return

    def event(data: dict[str, Any]) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], data))

    async def wait() -> None:
        hub = entry.runtime_data.hub
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CONNECT_TIMEOUT
        # Untrusted devices only connect after we answer them; nudge it.
        while not hub.is_link_connected(device_id):
            if loop.time() > deadline:
                event({"error": "not_connected"})
                return
            info = hub.discovered.get(device_id)
            if info and info.host:
                hub.announce([info.host])
            await asyncio.sleep(1)
        try:
            pairing = hub.start_pairing(device_id)
            event({"key": pairing.verification_key})
            info, certificate = await pairing.wait()
        except PairingError as err:
            event({"error": str(err)})
            return
        subentry_id = await _add_device(hass, entry, info, certificate)
        event({"paired": subentry_id})

    task = hass.async_create_task(wait(), eager_start=False)

    @callback
    def unsubscribe() -> None:
        if not task.done():
            task.cancel()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/accept", vol.Required("device_id"): cv.string}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_accept(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Accept a pairing request a device sent."""
    entry = _loaded_entry(hass)
    if entry is None:
        _not_loaded(connection, msg["id"])
        return
    try:
        info, certificate = entry.runtime_data.hub.accept_incoming(msg["device_id"])
    except PairingError as err:
        connection.send_error(msg["id"], str(err), "The request has expired")
        return
    subentry_id = await _add_device(hass, entry, info, certificate)
    connection.send_result(msg["id"], {"id": subentry_id})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/decline", vol.Required("device_id"): cv.string}
)
@websocket_api.require_admin
@callback
def ws_decline(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Turn down a pairing request."""
    if (hub := _hub(hass)) is not None:
        hub.decline_incoming(msg["device_id"])
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/set_name", vol.Required("name"): cv.string}
)
@websocket_api.require_admin
@callback
def ws_set_name(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Change the name devices see for Home Assistant."""
    entry = _entry(hass)
    if entry is None:
        _not_loaded(connection, msg["id"])
        return
    name = filter_device_name(msg["name"])
    if not name:
        connection.send_error(msg["id"], "invalid_name", "Enter a name")
        return
    if name != (entry.options.get(CONF_NAME) or entry.title):
        hass.config_entries.async_update_entry(
            entry, title=name, options={**entry.options, CONF_NAME: name}
        )
    connection.send_result(msg["id"], {"name": name})


def _subentry(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> tuple[KdeConnectConfigEntry, ConfigSubentry] | None:
    entry = _entry(hass)
    subentry = entry.subentries.get(msg["subentry_id"]) if entry else None
    if entry is None or subentry is None:
        connection.send_error(msg["id"], "not_found", "Unknown device")
        return None
    return entry, subentry


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/update_device",
        vol.Required("subentry_id"): cv.string,
        vol.Optional("mac"): vol.Any(None, cv.string),
        vol.Optional("scripts"): [cv.entity_id],
        vol.Optional("hidden_commands"): [cv.string],
    }
)
@websocket_api.require_admin
@callback
def ws_update_device(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Change Wake-on-LAN, shared scripts and which buttons are removed."""
    if (found := _subentry(hass, connection, msg)) is None:
        return
    entry, subentry = found
    updates: dict[str, Any] = {}
    if "mac" in msg:
        mac = (msg["mac"] or "").strip()
        if mac:
            try:
                mac = format_mac(cv.matches_regex(MAC_RE)(mac))
            except vol.Invalid:
                connection.send_error(msg["id"], "invalid_mac", "Invalid MAC address")
                return
        updates[CONF_MAC] = mac or None
    if "scripts" in msg:
        if any(not script.startswith("script.") for script in msg["scripts"]):
            connection.send_error(msg["id"], "invalid_script", "Only scripts")
            return
        updates[CONF_SCRIPTS] = list(dict.fromkeys(msg["scripts"]))
    if "hidden_commands" in msg:
        updates[CONF_HIDDEN_COMMANDS] = sorted(set(msg["hidden_commands"]))
    if any(subentry.data.get(key) != value for key, value in updates.items()):
        hass.config_entries.async_update_subentry(
            entry, subentry, data={**subentry.data, **updates}
        )
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/remove_device", vol.Required("subentry_id"): cv.string}
)
@websocket_api.require_admin
@callback
def ws_remove_device(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Unpair a device and remove it from Home Assistant."""
    if (found := _subentry(hass, connection, msg)) is None:
        return
    entry, subentry = found
    if (hub := _hub(hass)) is not None:
        hub.unpair(subentry.data[CONF_DEVICE_ID])
    hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/command_setup", vol.Required("subentry_id"): cv.string}
)
@websocket_api.require_admin
@callback
def ws_command_setup(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Open the run command settings on the device."""
    entry = _loaded_entry(hass)
    device = entry.runtime_data.devices.get(msg["subentry_id"]) if entry else None
    if device is None or not device.open_command_setup():
        connection.send_error(msg["id"], "not_connected", "Not connected")
        return
    connection.send_result(msg["id"])
