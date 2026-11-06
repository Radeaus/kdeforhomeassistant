"""Diagnostics must not leak keys, certificates or MAC addresses."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.kdeforhomeassistant.const import (
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_RUNCOMMAND_REQUEST,
)

from .fake_device import CAPABILITIES, FakeDevice
from .test_init import _pair, _setup


async def test_diagnostics(hass: HomeAssistant, hass_client) -> None:
    """A connected and a disconnected device, with secrets redacted."""
    assert await async_setup_component(
        hass, "script", {"script": {"hello": {"sequence": []}}}
    )
    entry = await _setup(hass)
    online = FakeDevice("Online PC", protocol_version=8)
    online.commands = {"abc": {"name": "Unlock", "command": "true"}}
    offline = FakeDevice("Offline PC", protocol_version=7)
    await _pair(hass, entry, online)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await _pair(hass, entry, offline)
    offline.close()
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    # Give the online device Wake-on-LAN and a script.
    subentry = next(
        sub for sub in entry.subentries.values() if sub.title == "Online PC"
    )
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"mac": "aa:bb:cc:dd:ee:ff", "scripts": ["script.hello"]}
    )
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    online.packets.clear()
    await online.connect(entry.runtime_data.hub.tcp_port)
    await online.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, requestCommandList=True)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["entry"]["certificate"] == "**REDACTED**"
    assert diagnostics["entry"]["private_key"] == "**REDACTED**"
    assert diagnostics["entry"]["device_id"] == entry.data["device_id"]
    text = str(diagnostics)
    assert "BEGIN" not in text
    assert "aa:bb:cc:dd:ee:ff" not in text
    assert diagnostics["options"] == {"name": "Test - Home Assistant"}
    assert diagnostics["tcp_port"] == entry.runtime_data.hub.tcp_port
    assert "Online PC" in diagnostics["discovered"]

    devices = {device["name"]: device for device in diagnostics["devices"]}
    assert devices["Online PC"] == {
        "name": "Online PC",
        "device_type": "desktop",
        "connected": True,
        "protocol_version": 8,
        "incoming_capabilities": sorted(CAPABILITIES),
        "remote_commands": ["Unlock"],
        "scripts": ["script.hello"],
        "has_mac": True,
        "locked": False,
    }
    assert devices["Offline PC"]["connected"] is False
    assert devices["Offline PC"]["protocol_version"] is None
    assert devices["Offline PC"]["incoming_capabilities"] is None
    assert devices["Offline PC"]["has_mac"] is False

    online.close()
    assert await hass.config_entries.async_unload(entry.entry_id)
