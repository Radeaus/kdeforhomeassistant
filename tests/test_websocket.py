"""Tests for the panel API: what it answers when things are missing or wrong."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.kdeforhomeassistant import websocket
from custom_components.kdeforhomeassistant.const import (
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_PAIR,
    DeviceInfo,
    Packet,
)
from custom_components.kdeforhomeassistant.websocket import build_state

from .fake_device import FakeDevice
from .test_init import _pair, _setup


async def _wait(predicate, timeout: float = 5) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.05)


async def _result(client) -> dict:
    """Return the next result, skipping events of subscriptions."""
    async with asyncio.timeout(10):
        while (msg := await client.receive_json())["type"] != "result":
            pass
    return msg


async def _event(client, msg_id: int) -> dict:
    async with asyncio.timeout(10):
        while True:
            msg = await client.receive_json()
            if msg["id"] == msg_id and msg["type"] == "event":
                return msg["event"]


async def _call(client, payload: dict) -> dict:
    await client.send_json_auto_id(payload)
    return await _result(client)


def _unloaded_entry(hass: HomeAssistant) -> MockConfigEntry:
    """An entry with a device that was never loaded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test - Home Assistant",
        data={"device_id": "self"},
        subentries_data=[
            {
                "data": {
                    "device_id": "desk",
                    "name": "Desk",
                    "hidden_commands": ["hide"],
                },
                "subentry_id": "sub_desk",
                "subentry_type": SUBENTRY_TYPE_DEVICE,
                "title": "Desk",
                "unique_id": "desk",
            },
            {
                "data": {},
                "subentry_id": "sub_other",
                "subentry_type": "something_else",
                "title": "Other",
                "unique_id": "other",
            },
        ],
    )
    entry.add_to_hass(hass)
    return entry


async def test_without_entry(hass: HomeAssistant, hass_ws_client) -> None:
    """Before setup, the panel is told nothing is configured."""
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    msg = await _result(client)
    assert msg["success"]
    assert await _event(client, msg["id"]) == {"configured": False}

    msg = await _call(client, {"type": f"{DOMAIN}/set_name", "name": "X"})
    assert msg["error"]["code"] == "not_loaded"
    for command in ("update_device", "remove_device"):
        msg = await _call(
            client, {"type": f"{DOMAIN}/{command}", "subentry_id": "nope"}
        )
        assert msg["error"]["code"] == "not_found"


async def test_not_loaded(hass: HomeAssistant, hass_ws_client) -> None:
    """An entry that is not loaded: commands that need the hub say so."""
    assert await async_setup_component(hass, DOMAIN, {})
    entry = _unloaded_entry(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "button", DOMAIN, "desk_command_hide", config_entry=entry,
        config_subentry_id="sub_desk", original_name="Hidden",
    )
    registry.async_get_or_create(
        "button", DOMAIN, "desk_command_shown", config_entry=entry,
        config_subentry_id="sub_desk", original_name="Shown",
    )

    state = build_state(hass)
    assert state["loaded"] is False
    # Only devices are listed, not other kinds of subentries.
    assert [device["id"] for device in state["devices"]] == ["sub_desk"]
    commands = {c["key"]: c for c in state["devices"][0]["commands"]}
    assert commands["hide"]["hidden"] is True
    assert commands["hide"]["entity_id"] is None
    assert commands["shown"]["hidden"] is False
    assert commands["shown"]["entity_id"]
    assert state["discovered"] == []

    client = await hass_ws_client(hass)
    for payload in (
        {"type": f"{DOMAIN}/connect", "host": "10.0.0.2"},
        {"type": f"{DOMAIN}/pair", "device_id": "desk"},
        {"type": f"{DOMAIN}/accept", "device_id": "desk"},
    ):
        msg = await _call(client, payload)
        assert msg["error"]["code"] == "not_loaded", payload
    for command in ("command_setup", "screenshot"):
        msg = await _call(
            client, {"type": f"{DOMAIN}/{command}", "subentry_id": "sub_desk"}
        )
        assert msg["error"]["code"] == "not_connected"
    # Declining without a hub does nothing, but does not fail.
    msg = await _call(client, {"type": f"{DOMAIN}/decline", "device_id": "desk"})
    assert msg["success"]

    msg = await _call(client, {"type": f"{DOMAIN}/set_name", "name": "<>"})
    assert msg["error"]["code"] == "invalid_name"
    msg = await _call(
        client,
        {
            "type": f"{DOMAIN}/update_device",
            "subentry_id": "sub_desk",
            "scripts": ["light.kitchen"],
        },
    )
    assert msg["error"]["code"] == "invalid_script"
    # Clearing the MAC address, which was not set, changes nothing.
    msg = await _call(
        client,
        {"type": f"{DOMAIN}/update_device", "subentry_id": "sub_desk", "mac": None},
    )
    assert msg["success"]

    # Removing a device without a hub only removes it here.
    msg = await _call(
        client, {"type": f"{DOMAIN}/remove_device", "subentry_id": "sub_desk"}
    )
    assert msg["success"]
    assert "sub_desk" not in entry.subentries


async def test_discover_follows_reload(hass: HomeAssistant, hass_ws_client) -> None:
    """Discovery moves to the new hub after a reload, and stops on unload."""
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    msg = await _call(client, {"type": f"{DOMAIN}/discover"})
    assert msg["success"]
    await hass.async_block_till_done()
    old_hub = entry.runtime_data.hub
    assert old_hub._discovering == 1

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    new_hub = entry.runtime_data.hub
    assert new_hub is not old_hub
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=4))
    await hass.async_block_till_done()
    assert old_hub._discovering == 0
    assert new_hub._discovering == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=8))
    await hass.async_block_till_done()
    assert new_hub._discovering == 0

    await client.send_json_auto_id(
        {"type": "unsubscribe_events", "subscription": msg["id"]}
    )
    assert (await _result(client))["success"]


async def test_connect(hass: HomeAssistant, hass_ws_client) -> None:
    """Connect by address: found when the device links up, else not found."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    device = FakeDevice("Desk", protocol_version=8)
    await device.connect(hub.tcp_port)
    device_id = device.identity.device_id
    await _wait(lambda: hub.is_link_connected(device_id))
    client = await hass_ws_client(hass)

    msg = await _call(client, {"type": f"{DOMAIN}/connect", "host": " 127.0.0.1 "})
    assert msg["result"] == {"device_id": device_id}

    with patch.object(websocket, "CONNECT_TIMEOUT", 0.5):
        msg = await _call(client, {"type": f"{DOMAIN}/connect", "host": "127.0.0.9"})
    assert msg["error"]["code"] == "not_found"

    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_pair_errors(hass: HomeAssistant, hass_ws_client) -> None:
    """Pairing a device that never connects, declines, or is already paired."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    client = await hass_ws_client(hass)

    # A device that was seen but never connects.
    hub.discovered["ghost"] = DeviceInfo(
        device_id="ghost", name="Ghost", device_type="desktop", host="127.0.0.9"
    )
    with patch.object(websocket, "CONNECT_TIMEOUT", 1.2):
        msg = await _call(client, {"type": f"{DOMAIN}/pair", "device_id": "ghost"})
        assert msg["success"]
        assert await _event(client, msg["id"]) == {"error": "not_connected"}

    # Leaving the page stops the wait.
    msg = await _call(client, {"type": f"{DOMAIN}/pair", "device_id": "ghost"})
    await client.send_json_auto_id(
        {"type": "unsubscribe_events", "subscription": msg["id"]}
    )
    assert (await _result(client))["success"]
    await hass.async_block_till_done()

    # A device that turns the request down.
    device = FakeDevice("Desk", protocol_version=8)
    device.auto_accept = False
    await device.connect(hub.tcp_port)
    device_id = device.identity.device_id
    await _wait(lambda: hub.is_link_connected(device_id))
    msg = await _call(client, {"type": f"{DOMAIN}/pair", "device_id": device_id})
    assert "key" in await _event(client, msg["id"])
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    assert "error" in await _event(client, msg["id"])
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_pair_paired_device(hass: HomeAssistant, hass_ws_client) -> None:
    """Pairing a paired device again is refused."""
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    paired = FakeDevice("Laptop", protocol_version=8)
    await _pair(hass, entry, paired)
    msg = await _call(
        client, {"type": f"{DOMAIN}/pair", "device_id": paired.identity.device_id}
    )
    assert msg["error"]["code"] == "already_paired"
    paired.close()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_offline_device(hass: HomeAssistant, hass_ws_client) -> None:
    """A paired device that is offline cannot be set up or asked for its screen."""
    entry = await _setup(hass)
    device = FakeDevice("Desk", protocol_version=8)
    await _pair(hass, entry, device)
    device.close()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry_id = next(iter(entry.subentries))
    client = await hass_ws_client(hass)
    for command in ("command_setup", "screenshot"):
        msg = await _call(
            client, {"type": f"{DOMAIN}/{command}", "subentry_id": subentry_id}
        )
        assert msg["error"]["code"] == "not_connected"
    assert await hass.config_entries.async_unload(entry.entry_id)
