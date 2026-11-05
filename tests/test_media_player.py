"""Tests for the media player: what plays on a device, and its volume."""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant

from custom_components.kdeforhomeassistant.const import DOMAIN
from custom_components.kdeforhomeassistant.kdeconnect.protocol import Packet

from .fake_device import FakeDevice
from .test_init import _pair, _setup

ENTITY = "media_player.fake_pc_media"


async def _settle(hass: HomeAssistant) -> None:
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()


async def test_media_player(hass: HomeAssistant) -> None:
    """Follow the players and volume of a device, and control them."""
    entry = await _setup(hass)
    device = FakeDevice("Fake PC", protocol_version=8)
    device.players = {
        "Spotify": {
            "title": "Song",
            "artist": "Band",
            "album": "Record",
            "isPlaying": False,
            "pos": 30000,
            "length": 200000,
            "canPlay": True,
            "canPause": True,
            "canGoNext": True,
            "canGoPrevious": True,
            "canSeek": True,
            "albumArtUrl": "https://example.com/art.jpg",
        },
        "Firefox": {"title": "Video", "isPlaying": True, "canSeek": False},
    }
    device.sinks = [
        {"name": "hdmi", "description": "HDMI", "volume": 32768, "maxVolume": 98304,
         "muted": False, "enabled": True},
        {"name": "jack", "description": "Headphones", "volume": 65536,
         "maxVolume": 65536, "muted": False, "enabled": False},
    ]
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for("kdeconnect.mpris.request", requestPlayerList=True)
    await device.wait_for("kdeconnect.systemvolume.request", requestSinks=True)
    await device.wait_for("kdeconnect.mpris.request", player="Spotify")
    await _settle(hass)

    # The playing player is the one shown.
    state = hass.states.get(ENTITY)
    assert state.state == "playing"
    assert state.attributes["source"] == "Firefox"
    assert set(state.attributes["source_list"]) == {"Spotify", "Firefox"}
    assert state.attributes["media_title"] == "Video"
    # Volume comes from the default output; 32768 of 65536 is half.
    assert state.attributes["volume_level"] == 0.5
    assert state.attributes["is_volume_muted"] is False

    # Choose another player.
    await hass.services.async_call(
        "media_player", "select_source",
        {"entity_id": ENTITY, "source": "Spotify"}, blocking=True,
    )
    state = hass.states.get(ENTITY)
    assert state.state == "paused"
    assert state.attributes["media_artist"] == "Band"
    assert state.attributes["media_duration"] == 200
    assert state.attributes["media_position"] == 30
    assert state.attributes["entity_picture"]

    device.packets.clear()
    await hass.services.async_call(
        "media_player", "media_play_pause", {"entity_id": ENTITY}, blocking=True
    )
    await device.wait_for(
        "kdeconnect.mpris.request", player="Spotify", action="PlayPause"
    )
    await _settle(hass)
    assert hass.states.get(ENTITY).state == "playing"

    await hass.services.async_call(
        "media_player", "media_seek",
        {"entity_id": ENTITY, "seek_position": 60}, blocking=True,
    )
    await device.wait_for(
        "kdeconnect.mpris.request", player="Spotify", SetPosition=60000
    )

    await hass.services.async_call(
        "media_player", "volume_set",
        {"entity_id": ENTITY, "volume_level": 0.25}, blocking=True,
    )
    await device.wait_for("kdeconnect.systemvolume.request", name="hdmi", volume=16384)
    await _settle(hass)
    assert hass.states.get(ENTITY).attributes["volume_level"] == 0.25

    await hass.services.async_call(
        "media_player", "volume_mute",
        {"entity_id": ENTITY, "is_volume_muted": True}, blocking=True,
    )
    await device.wait_for("kdeconnect.systemvolume.request", name="hdmi", muted=True)
    await _settle(hass)
    assert hass.states.get(ENTITY).attributes["is_volume_muted"] is True

    # A player that closes disappears from the list.
    del device.players["Firefox"]
    device.send(Packet("kdeconnect.mpris", {"playerList": ["Spotify"]}))
    await _settle(hass)
    assert hass.states.get(ENTITY).attributes["source_list"] == ["Spotify"]

    device.close()
    await _settle(hass)
    assert hass.states.get(ENTITY).state == "unavailable"
    assert await hass.config_entries.async_unload(entry.entry_id)
