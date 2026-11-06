"""Tests for the entities: media controls, waking up, and a device that stops listening."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.kdeforhomeassistant import device as device_module
from custom_components.kdeforhomeassistant.const import DOMAIN

from .fake_device import FakeDevice
from .test_init import _pair, _setup

MEDIA = "media_player.fake_pc_media"
MPRIS = "kdeconnect.mpris.request"


async def _settle(hass: HomeAssistant) -> None:
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()


async def _connected(hass: HomeAssistant) -> tuple[FakeDevice, object]:
    """Pair a device with a player and a command, and give it a MAC address."""
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=8)
    device.players = {
        "VLC": {
            "title": "Song",
            "isPlaying": True,
            "volume": 50,
            "canGoNext": True,
            "canGoPrevious": True,
        }
    }
    device.commands = {"c1": {"name": "Spotify", "command": "spotify"}}
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry = next(iter(entry.subentries.values()))
    hass.config_entries.async_update_subentry(
        entry, subentry, data={**subentry.data, "mac": "aa:bb:cc:dd:ee:ff"}
    )
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for(MPRIS, player="VLC")
    await device.wait_for("kdeconnect.runcommand.request", requestCommandList=True)
    await _settle(hass)
    return device, entry


async def test_media_controls_and_wake(hass: HomeAssistant) -> None:
    """Player controls send their action; wake sends the magic packet."""
    device, entry = await _connected(hass)

    # No audio output: the player volume can be set, not muted.
    state = hass.states.get(MEDIA)
    assert state.state == "playing"
    features = state.attributes["supported_features"]
    assert features & MediaPlayerEntityFeature.VOLUME_SET
    assert not features & MediaPlayerEntityFeature.VOLUME_MUTE
    assert state.attributes["volume_level"] == 0.5

    for service, action in (
        ("media_play", "Play"),
        ("media_pause", "Pause"),
        ("media_stop", "Stop"),
        ("media_next_track", "Next"),
        ("media_previous_track", "Previous"),
    ):
        await hass.services.async_call(
            "media_player", service, {"entity_id": MEDIA}, blocking=True
        )
        await device.wait_for(MPRIS, player="VLC", action=action)

    with patch.object(device_module, "_send_magic_packet") as send:
        await hass.services.async_call(
            "remote", "turn_on", {"entity_id": "remote.fake_pc_remote"}, blocking=True
        )
        await hass.services.async_call(
            "button", "press", {"entity_id": "button.fake_pc_wake_up"}, blocking=True
        )
    assert send.call_count == 2
    assert send.call_args.args[0].endswith(bytes.fromhex("aabbccddeeff"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "remote", "turn_off", {"entity_id": "remote.fake_pc_remote"}, blocking=True
        )

    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    ("domain", "service", "entity_id", "data"),
    [
        ("lock", "lock", "lock.fake_pc_screen", {}),
        ("notify", "send_message", "notify.fake_pc", {"message": "Hi"}),
        ("text", "set_value", "text.fake_pc_keyboard", {"value": "Hi"}),
        ("button", "press", "button.fake_pc_ring", {}),
        ("button", "press", "button.fake_pc_spotify", {}),
        ("media_player", "media_play", MEDIA, {}),
    ],
)
async def test_send_fails(
    hass: HomeAssistant, domain: str, service: str, entity_id: str, data: dict
) -> None:
    """When a packet cannot be sent, the action fails with a clear error."""
    device, entry = await _connected(hass)
    assert hass.states.get(entity_id).state != "unavailable"
    hub = entry.runtime_data.hub
    with (
        patch.object(hub, "send", return_value=False),
        pytest.raises(HomeAssistantError) as err,
    ):
        await hass.services.async_call(
            domain, service, {"entity_id": entity_id, **data}, blocking=True
        )
    assert err.value.translation_key == "not_connected"
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)
