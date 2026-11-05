"""Tests for the remote and keyboard: keys, text and mouse actions."""

from __future__ import annotations

import asyncio

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.kdeforhomeassistant.const import DOMAIN
from custom_components.kdeforhomeassistant.kdeconnect.protocol import Packet
from custom_components.kdeforhomeassistant.remote import SCROLL_STEP, parse_command

from .fake_device import FakeDevice
from .test_init import _pair, _setup

REMOTE = "remote.fake_pc_remote"
KEYBOARD = "text.fake_pc_keyboard"
MOUSEPAD = "kdeconnect.mousepad.request"


@pytest.mark.parametrize(
    ("command", "body"),
    [
        # The remote of the KDE Connect app, as it sends its buttons.
        ("up", {"specialKey": 5}),
        ("down", {"specialKey": 7}),
        ("left", {"specialKey": 4}),
        ("right", {"specialKey": 6}),
        ("select", {"specialKey": 12}),
        ("back", {"specialKey": 14}),
        ("home", {"super": True, "specialKey": 20}),
        ("close", {"alt": True, "specialKey": 24}),
        # Keys and combinations.
        ("enter", {"specialKey": 12}),
        ("ESCAPE", {"specialKey": 14}),
        ("home_key", {"specialKey": 10}),
        ("f12", {"specialKey": 32}),
        ("a", {"key": "a"}),
        ("A", {"key": "A"}),
        ("+", {"key": "+"}),
        ("ctrl+c", {"ctrl": True, "key": "c"}),
        ("alt+f4", {"alt": True, "specialKey": 24}),
        ("ctrl+shift+t", {"ctrl": True, "shift": True, "key": "t"}),
        ("super+e", {"super": True, "key": "e"}),
        ("text:Hello World", {"key": "Hello World"}),
        ("text:a:b", {"key": "a:b"}),
        # Mouse.
        ("click", {"singleclick": True}),
        ("double_click", {"doubleclick": True}),
        ("right_click", {"rightclick": True}),
        ("middle_click", {"middleclick": True}),
        ("scroll_up", {"scroll": True, "dx": 0, "dy": SCROLL_STEP}),
        ("scroll_down", {"scroll": True, "dx": 0, "dy": -SCROLL_STEP}),
        ("scroll_left", {"scroll": True, "dx": -SCROLL_STEP, "dy": 0}),
        ("scroll_down:120", {"scroll": True, "dx": 0, "dy": -120}),
        ("move:10,-5", {"dx": 10, "dy": -5}),
        # Android.
        ("android_back", {"backclick": True}),
        ("android_home", {"middleclick": True}),
        ("android_recents", {"forwardclick": True}),
    ],
)
def test_parse_command(command: str, body: dict) -> None:
    """Every command becomes the packet the KDE Connect apps understand."""
    assert parse_command(command) == body


@pytest.mark.parametrize(
    "command",
    ["", "nope", "ctrl+", "hyper+a", "text:", "move:1", "move:0,0", "scroll_up:-1",
     "scroll_up:x", "up:2", "ctrl+nope"],
)
def test_parse_command_rejects(command: str) -> None:
    """Unknown commands are refused."""
    with pytest.raises(ValueError):
        parse_command(command)


async def test_remote_and_keyboard(hass: HomeAssistant) -> None:
    """The remote and keyboard send their packets to the device."""
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=8)
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    device.send(Packet("kdeconnect.mousepad.keyboardstate", {"state": True}))
    await asyncio.sleep(0.3)
    await hass.async_block_till_done()

    assert hass.states.get(REMOTE).state == "on"
    kde = entry.runtime_data.devices[next(iter(entry.runtime_data.devices))]
    assert kde.can_type is True

    device.packets.clear()
    await hass.services.async_call(
        "remote",
        "send_command",
        {"entity_id": REMOTE, "command": ["down", "select"], "num_repeats": 2,
         "delay_secs": 0},
        blocking=True,
    )
    await device.wait_for(MOUSEPAD, specialKey=12)
    await asyncio.sleep(0.2)
    sent = [p.body for p in device.packets if p.type == MOUSEPAD]
    assert sent == [{"specialKey": 7}, {"specialKey": 12}] * 2

    # Nothing is sent when one of the commands is not understood.
    device.packets.clear()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": REMOTE, "command": ["up", "fly"]},
            blocking=True,
        )
    await asyncio.sleep(0.2)
    assert not [p for p in device.packets if p.type == MOUSEPAD]

    await hass.services.async_call(
        "text", "set_value", {"entity_id": KEYBOARD, "value": "Hallo"}, blocking=True
    )
    await device.wait_for(MOUSEPAD, key="Hallo")

    # No MAC address: turning on explains why it cannot.
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "remote", "turn_on", {"entity_id": REMOTE}, blocking=True
        )

    device.close()
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    assert hass.states.get(REMOTE).state == "off"
    assert hass.states.get(KEYBOARD).state == "unavailable"
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": REMOTE, "command": "up"},
            blocking=True,
        )
    assert await hass.config_entries.async_unload(entry.entry_id)
