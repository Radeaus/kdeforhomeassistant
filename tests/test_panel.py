"""Tests for the panel API and pairing requests that devices send."""

from __future__ import annotations

import asyncio
import time

from homeassistant.core import HomeAssistant

from custom_components.kdeforhomeassistant.const import (
    DOMAIN,
    default_name,
)
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_PAIR,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    Packet,
)

from .fake_device import FakeDevice
from .test_init import _setup


async def _wait(predicate, timeout: float = 5) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.05)


async def _next_event(client, msg_id: int, predicate=lambda event: True):
    async with asyncio.timeout(10):
        while True:
            msg = await client.receive_json()
            if msg["id"] == msg_id and msg["type"] == "event" and predicate(msg["event"]):
                return msg["event"]


def test_default_name() -> None:
    """The name devices see is based on the location name."""
    assert default_name("Thuis") == "Thuis - Home Assistant"
    assert default_name("") == "Home Assistant"
    assert default_name("Home Assistant") == "Home Assistant"
    assert len(default_name("A very long location name for a house")) <= 32


async def test_device_asks_to_pair(hass: HomeAssistant, hass_ws_client) -> None:
    """Pressing Pair on the device shows a request that can be accepted."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    device = FakeDevice("Desk PC", protocol_version=8)
    await device.connect(hub.tcp_port)
    await _wait(lambda: hub.is_link_connected(device.identity.device_id))

    device.send(Packet(PACKET_TYPE_PAIR, {"pair": True, "timestamp": int(time.time())}))
    await _wait(lambda: device.identity.device_id in hub.incoming)
    await hass.async_block_till_done()
    # It is not turned down right away.
    assert not any(p.type == PACKET_TYPE_PAIR for p in device.packets)

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    msg = await client.receive_json()
    assert msg["success"]
    state = await _next_event(client, msg["id"])
    assert state["requests"][0]["name"] == "Desk PC"
    assert len(state["requests"][0]["key"]) == 8

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/accept", "device_id": device.identity.device_id}
    )
    result = await client.receive_json()
    while result.get("type") == "event":
        result = await client.receive_json()
    assert result["success"], result
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    await hass.async_block_till_done()

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert len(entry.subentries) == 1
    subentry_id = result["result"]["id"]
    assert subentry_id in entry.subentries

    # The device reconnects after the reload and is trusted.
    device.packets.clear()
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, requestCommandList=True)
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.desk_pc_connected").state == "on"

    # Open the command settings on the device.
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/command_setup", "subentry_id": subentry_id}
    )
    result = await client.receive_json()
    while result.get("type") == "event":
        result = await client.receive_json()
    assert result["success"], result
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, setup=True)

    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_request_declined_and_expired(hass: HomeAssistant, hass_ws_client) -> None:
    """Declining, or the device giving up, ends the request."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    device = FakeDevice("Laptop", protocol_version=7)
    await device.connect(hub.tcp_port)
    device_id = device.identity.device_id
    await _wait(lambda: hub.is_link_connected(device_id))

    device.send(Packet(PACKET_TYPE_PAIR, {"pair": True}))
    await _wait(lambda: device_id in hub.incoming)
    # The device cancels.
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    await _wait(lambda: device_id not in hub.incoming)

    device.send(Packet(PACKET_TYPE_PAIR, {"pair": True}))
    await _wait(lambda: device_id in hub.incoming)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/decline", "device_id": device_id})
    result = await client.receive_json()
    assert result["success"]
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    assert device_id not in hub.incoming
    await hass.async_block_till_done()

    # Accepting after it is gone fails cleanly.
    await client.send_json_auto_id({"type": f"{DOMAIN}/accept", "device_id": device_id})
    result = await client.receive_json()
    assert not result["success"]
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_pair_and_manage_from_panel(hass: HomeAssistant, hass_ws_client) -> None:
    """Pair from the panel, then change the name, scripts, MAC and remove it."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    device = FakeDevice("Office PC", protocol_version=8)
    await device.connect(hub.tcp_port)
    device_id = device.identity.device_id
    await _wait(lambda: hub.is_link_connected(device_id))

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/discover"})
    assert (await client.receive_json())["success"]

    await client.send_json_auto_id({"type": f"{DOMAIN}/pair", "device_id": device_id})
    msg = await client.receive_json()
    assert msg["success"], msg
    pair_id = msg["id"]
    key = await _next_event(client, pair_id, lambda e: "key" in e)
    assert len(key["key"]) == 8
    paired = await _next_event(client, pair_id, lambda e: "paired" in e or "error" in e)
    assert "paired" in paired, paired
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry_id = paired["paired"]
    assert entry.subentries[subentry_id].unique_id == device_id

    await client.send_json_auto_id({"type": f"{DOMAIN}/set_name", "name": "Thuis"})
    msg = await client.receive_json()
    assert msg["success"]
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.title == "Thuis"

    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/update_device",
            "subentry_id": subentry_id,
            "mac": "nope",
        }
    )
    msg = await client.receive_json()
    assert msg["error"]["code"] == "invalid_mac"

    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/update_device",
            "subentry_id": subentry_id,
            "mac": "AA-BB-CC-DD-EE-FF",
            "scripts": ["script.hello"],
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    data = entry.subentries[subentry_id].data
    assert data["mac"] == "aa:bb:cc:dd:ee:ff"
    assert data["scripts"] == ["script.hello"]

    await client.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    msg = await client.receive_json()
    state = await _next_event(client, msg["id"])
    assert state["name"] == "Thuis"
    assert state["devices"][0]["mac"] == "aa:bb:cc:dd:ee:ff"
    assert "connected" in state["devices"][0]["entities"]

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/remove_device", "subentry_id": subentry_id}
    )
    msg = await client.receive_json()
    while msg.get("type") == "event":
        msg = await client.receive_json()
    assert msg["success"]
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert not entry.subentries
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)
