"""End-to-end tests: set up, pair a fake device, and use its entities."""

from __future__ import annotations

import asyncio
import json
import shutil

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.kdeforhomeassistant.const import DOMAIN, SUBENTRY_TYPE_DEVICE
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_NOTIFICATION,
    PACKET_TYPE_PAIR,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    Packet,
)

from .fake_device import FakeDevice


async def _setup(hass: HomeAssistant):
    hass.config.location_name = "Test"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test - Home Assistant"
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def _progress_until(hass, flow_id, result, step_id):
    """Advance a subentry flow through progress steps until step_id shows."""
    for _ in range(40):
        if result["type"] is FlowResultType.SHOW_PROGRESS:
            await hass.async_block_till_done(wait_background_tasks=False)
            await asyncio.sleep(0.25)
            result = await hass.config_entries.subentries.async_configure(flow_id)
            continue
        if result["type"] is FlowResultType.SHOW_PROGRESS_DONE:
            result = await hass.config_entries.subentries.async_configure(flow_id)
            continue
        if result.get("step_id") == step_id or result["type"] in (
            FlowResultType.CREATE_ENTRY,
            FlowResultType.ABORT,
        ):
            return result
        break
    return result


async def _pair(hass: HomeAssistant, entry, device: FakeDevice):
    hub = entry.runtime_data.hub
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE), context={"source": "user"}
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    flow_id = result["flow_id"]
    await device.connect(hub.tcp_port)
    result = await _progress_until(hass, flow_id, result, "pick")
    assert result["step_id"] == "pick"
    assert result["description_placeholders"]["count"] == "1"
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {"device": device.identity.device_id}
    )
    result = await _progress_until(hass, flow_id, result, "finish")
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    await hass.async_block_till_done()
    return result


async def test_pair_and_control(hass: HomeAssistant) -> None:
    """Pair a protocol 7 device and use lock, notify and run command buttons."""
    assert await async_setup_component(
        hass, "script", {"script": {"hello": {"sequence": []}}}
    )
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=7)
    device.commands = {"abc": {"name": "Unlock", "command": "loginctl unlock-session"}}
    await _pair(hass, entry, device)
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)

    # The entry reloaded with the new device; the old link was closed.
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    assert len(entry.subentries) == 1
    hub = entry.runtime_data.hub
    device.packets.clear()
    await device.connect(hub.tcp_port)
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, requestCommandList=True)
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities = {
        e.entity_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    assert "binary_sensor.fake_pc_connected" in entities
    assert "lock.fake_pc_screen" in entities
    assert "notify.fake_pc" in entities
    assert "button.fake_pc_ring" in entities
    assert "button.fake_pc_unlock" in entities

    assert hass.states.get("binary_sensor.fake_pc_connected").state == "on"
    assert hass.states.get("lock.fake_pc_screen").state == "unlocked"

    await hass.services.async_call(
        "lock", "lock", {"entity_id": "lock.fake_pc_screen"}, blocking=True
    )
    await device.wait_for(PACKET_TYPE_LOCK_REQUEST, setLocked=True)
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    assert hass.states.get("lock.fake_pc_screen").state == "locked"

    await hass.services.async_call(
        "button", "press", {"entity_id": "button.fake_pc_unlock"}, blocking=True
    )
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, key="abc")

    await hass.services.async_call(
        "notify",
        "send_message",
        {"entity_id": "notify.fake_pc", "message": "Hi", "title": "T"},
        blocking=True,
    )
    note = await device.wait_for(PACKET_TYPE_NOTIFICATION)
    assert note.body["text"] == "Hi"

    # A command removed on the device disappears from Home Assistant.
    device.commands = {}
    device.send_commands()
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert registry.async_get("button.fake_pc_unlock") is None

    # Share a script, and let the device run it.
    subentry = next(iter(entry.subentries.values()))
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"mac": "AA-BB-CC-DD-EE-FF", "scripts": ["script.hello"]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["mac"] == "aa:bb:cc:dd:ee:ff"
    hub = entry.runtime_data.hub
    device.packets.clear()
    await device.connect(hub.tcp_port)
    offered = await device.wait_for(PACKET_TYPE_RUNCOMMAND)
    assert "script.hello" in json.loads(offered.body["commandList"])
    calls = []
    hass.bus.async_listen("script_started", lambda event: calls.append(event))
    device.send(Packet(PACKET_TYPE_RUNCOMMAND_REQUEST, {"key": "script.hello"}))
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert calls
    assert hass.states.get("button.fake_pc_wake_up") is not None

    device.close()
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.fake_pc_connected").state == "off"
    assert hass.states.get("lock.fake_pc_screen").state == "unavailable"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_own_commands_take_over(hass: HomeAssistant) -> None:
    """Run commands named after ring and lock replace the built-in way."""
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=7)
    device.commands = {
        "l1": {"name": "Scherm vergrendelen", "command": "cinnamon-screensaver-command -l"},
        "r1": {"name": " ring ", "command": "paplay ring.oga"},
    }
    await _pair(hass, entry, device)
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    device.packets.clear()
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, requestCommandList=True)
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert hass.states.get("lock.fake_pc_screen").state == "unlocked"

    # Lock runs the command and assumes the screen is locked now.
    await hass.services.async_call(
        "lock", "lock", {"entity_id": "lock.fake_pc_screen"}, blocking=True
    )
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, key="l1")
    await hass.async_block_till_done()
    assert hass.states.get("lock.fake_pc_screen").state == "locked"
    assert not any(
        p.type == PACKET_TYPE_LOCK_REQUEST and "setLocked" in p.body
        for p in device.packets
    )

    # No unlock command: unlocking falls back to the built-in way.
    await hass.services.async_call(
        "lock", "unlock", {"entity_id": "lock.fake_pc_screen"}, blocking=True
    )
    await device.wait_for(PACKET_TYPE_LOCK_REQUEST, setLocked=False)

    await hass.services.async_call(
        "button", "press", {"entity_id": "button.fake_pc_ring"}, blocking=True
    )
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, key="r1")

    device.close()
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_pair_protocol_8_and_decline(hass: HomeAssistant) -> None:
    """A protocol 8 device that declines pairing aborts the flow."""
    entry = await _setup(hass)
    device = FakeDevice("Phone", protocol_version=8)
    device.auto_accept = False
    hub = entry.runtime_data.hub
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE), context={"source": "user"}
    )
    flow_id = result["flow_id"]
    await device.connect(hub.tcp_port)
    result = await _progress_until(hass, flow_id, result, "pick")
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {"device": device.identity.device_id}
    )
    for _ in range(20):
        if (
            result["type"] is FlowResultType.SHOW_PROGRESS
            and result["step_id"] == "pair"
        ):
            break
        result = await _progress_until(hass, flow_id, result, "pair")
    assert result["step_id"] == "pair"
    assert len(result["description_placeholders"]["key"]) == 8
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    result = await _progress_until(hass, flow_id, result, "x")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "pair_rejected"
    assert not entry.subentries
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_single_instance(hass: HomeAssistant) -> None:
    """Only one KDE Connect identity can exist."""
    entry = await _setup(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_import_legacy(hass: HomeAssistant) -> None:
    """Take over the identity and paired devices of bartv2/kde_connect."""
    import os
    import sqlite3

    from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
        generate_identity,
    )

    legacy = generate_identity("Old HA")
    folder = hass.config.path("kde_connect")
    peer = FakeDevice("Old PC", protocol_version=7)

    def write() -> None:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "certificate.pem"), "w") as file:
            file.write(legacy.certificate_pem)
        with open(os.path.join(folder, "privateKey.pem"), "w") as file:
            file.write(legacy.private_key_pem)
        conn = sqlite3.connect(os.path.join(folder, "konnect.db"))
        conn.execute(
            "CREATE TABLE trusted_devices (identifier TEXT PRIMARY KEY, certificate TEXT, name TEXT, type TEXT)"
        )
        conn.execute(
            "INSERT INTO trusted_devices VALUES (?, ?, ?, ?)",
            (
                peer.identity.device_id,
                peer.identity.certificate_pem.encode(),
                "Old PC",
                "desktop",
            ),
        )
        conn.commit()
        conn.close()

    await hass.async_add_executor_job(write)
    try:
        await _import_legacy(hass, legacy, peer)
    finally:
        await hass.async_add_executor_job(shutil.rmtree, folder)


async def _import_legacy(hass: HomeAssistant, legacy, peer: FakeDevice) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["step_id"] == "import_legacy"
    assert result["description_placeholders"]["devices"] == "Old PC"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "HomeAssistant"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.data["device_id"] == legacy.device_id
    assert len(entry.subentries) == 1

    # The old peer connects without pairing again; its capabilities get stored.
    await peer.connect(entry.runtime_data.hub.tcp_port)
    await asyncio.sleep(0.5)
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry = next(iter(entry.subentries.values()))
    assert "kdeconnect.lock.request" in subentry.data["capabilities"]
    await peer.connect(entry.runtime_data.hub.tcp_port)
    await asyncio.sleep(0.3)
    await hass.async_block_till_done()
    assert hass.states.get("lock.old_pc_screen") is not None
    assert hass.states.get("binary_sensor.old_pc_connected").state == "on"
    peer.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_no_pair_ping_pong(hass: HomeAssistant) -> None:
    """A paired device that re-sends "pair" gets one answer, not an endless loop.

    KDE Connect answers a "pair" from a device it already trusts with its own
    "pair", just like we do, so answering every time keeps both busy forever.
    """
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=8)
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, requestCommandList=True)

    device.packets.clear()
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": True}))
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    await asyncio.sleep(0.5)
    assert sum(p.type == PACKET_TYPE_PAIR for p in device.packets) == 1
    device.close()


async def test_panel_shown_when_ports_busy(hass: HomeAssistant) -> None:
    """The sidebar page appears and explains why, even when setup fails."""
    from unittest.mock import AsyncMock, patch

    from custom_components.kdeforhomeassistant.websocket import build_state

    with (
        patch(
            "custom_components.kdeforhomeassistant.KdeConnectHub.start",
            side_effect=OSError("Address in use"),
        ),
        patch(
            "custom_components.kdeforhomeassistant.async_register_panel",
            new=AsyncMock(),
        ) as register,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        assert entry.state is ConfigEntryState.SETUP_RETRY
        assert register.await_count >= 1
        state = build_state(hass)
        assert state["loaded"] is False
        assert "Address in use" in state["reason"]
        await hass.config_entries.async_unload(entry.entry_id)

