"""Tests for the screen: a device shares a screenshot and it is shown."""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant

from custom_components.kdeforhomeassistant.const import DOMAIN
from custom_components.kdeforhomeassistant.kdeconnect.protocol import Packet

from .fake_device import FakeDevice
from .test_init import _pair, _setup

SCREEN = "image.fake_pc_screen"
PNG = b"\x89PNG\r\n\x1a\n" + b"pixels" * 1000


async def test_screen(hass: HomeAssistant, hass_client, hass_ws_client) -> None:
    """Asking for a screenshot runs the command; the shared image is shown."""
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=8)
    device.commands = {"shot": {"name": "Screenshot", "command": "take-and-share"}}
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for("kdeconnect.runcommand.request", requestCommandList=True)
    await asyncio.sleep(0.3)
    await hass.async_block_till_done()
    assert hass.states.get(SCREEN).state == "unknown"
    subentry_id = next(iter(entry.subentries))

    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    await ws.receive_json()
    state = (await ws.receive_json())["event"]
    assert state["devices"][0]["can_screenshot"] is True
    assert state["self_id"] == entry.data["device_id"]

    await ws.send_json_auto_id({"type": f"{DOMAIN}/screenshot", "subentry_id": subentry_id})
    while (reply := await ws.receive_json())["type"] != "result":
        pass
    assert reply["success"], reply
    await device.wait_for("kdeconnect.runcommand.request", key="shot")

    # What the command does on the computer: share the picture with us.
    await device.share("screen.png", PNG)
    await asyncio.sleep(0.3)
    await hass.async_block_till_done()
    assert hass.states.get(SCREEN).state not in ("unknown", "unavailable")
    client = await hass_client()
    resp = await client.get(f"/api/image_proxy/{SCREEN}")
    assert resp.status == 200
    assert await resp.read() == PNG
    assert resp.content_type == "image/png"

    # Other files are not kept.
    before = hass.states.get(SCREEN).state
    task = asyncio.create_task(device.share("notes.txt", b"hello"))
    await asyncio.sleep(0.5)
    task.cancel()
    await hass.async_block_till_done()
    assert hass.states.get(SCREEN).state == before

    # The last screenshot stays visible while the device is away.
    device.close()
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert hass.states.get(SCREEN).state == before
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_screenshot_without_command(hass: HomeAssistant, hass_ws_client) -> None:
    """Without a Screenshot command the panel is told so."""
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=8)
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    await asyncio.sleep(0.3)
    await hass.async_block_till_done()
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/screenshot", "subentry_id": next(iter(entry.subentries))}
    )
    reply = await ws.receive_json()
    assert reply["error"]["code"] == "no_screenshot_command"
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)
