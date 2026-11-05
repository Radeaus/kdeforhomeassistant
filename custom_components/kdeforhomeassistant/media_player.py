"""Control media playback and volume on KDE Connect devices."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KdeConnectConfigEntry
from .const import DOMAIN
from .device import KdeConnectDevice
from .entity import KdeConnectEntity
from .kdeconnect.protocol import (
    PACKET_TYPE_MPRIS_REQUEST,
    PACKET_TYPE_SYSTEMVOLUME_REQUEST,
)

PARALLEL_UPDATES = 0

VOLUME_FEATURES = (
    MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KdeConnectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a media player for devices that share their players or volume."""
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.supports(PACKET_TYPE_MPRIS_REQUEST) or device.supports(
            PACKET_TYPE_SYSTEMVOLUME_REQUEST
        ):
            async_add_entities(
                [KdeConnectMediaPlayer(device)], config_subentry_id=subentry_id
            )


class KdeConnectMediaPlayer(KdeConnectEntity, MediaPlayerEntity):
    """What plays on a computer or phone, and how loud."""

    _attr_translation_key = "media"

    def __init__(self, device: KdeConnectDevice) -> None:
        super().__init__(device, "media_player")

    @property
    def _player(self) -> dict[str, Any]:
        name = self.device.active_player
        return self.device.players.get(name, {}) if name else {}

    @property
    def state(self) -> MediaPlayerState:
        """Return whether something plays."""
        player = self._player
        if player.get("isPlaying"):
            return MediaPlayerState.PLAYING
        if player.get("title"):
            return MediaPlayerState.PAUSED
        return MediaPlayerState.IDLE

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return what the current player and audio output allow."""
        features = MediaPlayerEntityFeature(0)
        player = self._player
        if self.device.players:
            features |= MediaPlayerEntityFeature.SELECT_SOURCE
        if player:
            features |= MediaPlayerEntityFeature.STOP
            if player.get("canPlay", True):
                features |= MediaPlayerEntityFeature.PLAY
            if player.get("canPause", True):
                features |= MediaPlayerEntityFeature.PAUSE
            if player.get("canGoNext"):
                features |= MediaPlayerEntityFeature.NEXT_TRACK
            if player.get("canGoPrevious"):
                features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
            if player.get("canSeek"):
                features |= MediaPlayerEntityFeature.SEEK
        if self.device.default_sink is not None:
            features |= VOLUME_FEATURES | MediaPlayerEntityFeature.VOLUME_MUTE
        elif isinstance(player.get("volume"), int | float):
            features |= VOLUME_FEATURES
        return features

    @property
    def source(self) -> str | None:
        """Return the player the controls act on."""
        return self.device.active_player

    @property
    def source_list(self) -> list[str] | None:
        """Return the players on the device."""
        return list(self.device.players) or None

    @property
    def media_title(self) -> str | None:
        """Return the title of the track."""
        return self._player.get("title") or None

    @property
    def media_artist(self) -> str | None:
        """Return the artist of the track."""
        return self._player.get("artist") or None

    @property
    def media_album_name(self) -> str | None:
        """Return the album of the track."""
        return self._player.get("album") or None

    @property
    def media_duration(self) -> int | None:
        """Return the length of the track in seconds."""
        length = self._player.get("length")
        return length // 1000 if isinstance(length, int) and length > 0 else None

    @property
    def media_position(self) -> int | None:
        """Return the position in the track in seconds."""
        pos = self._player.get("pos")
        return pos // 1000 if isinstance(pos, int) and pos >= 0 else None

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return when the position was reported."""
        return self._player.get("posUpdatedAt")

    @property
    def media_image_url(self) -> str | None:
        """Return the album art, when the device shares a web address for it."""
        url = self._player.get("albumArtUrl")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
        return None

    @property
    def volume_level(self) -> float | None:
        """Return the volume from 0 to 1."""
        return self.device.volume_level

    @property
    def is_volume_muted(self) -> bool | None:
        """Return whether the sound is muted."""
        return self.device.muted

    async def async_media_play(self) -> None:
        """Start playing."""
        self._check(self.device.media_action("Play"))

    async def async_media_pause(self) -> None:
        """Pause."""
        self._check(self.device.media_action("Pause"))

    async def async_media_play_pause(self) -> None:
        """Toggle between play and pause."""
        self._check(self.device.media_action("PlayPause"))

    async def async_media_stop(self) -> None:
        """Stop playing."""
        self._check(self.device.media_action("Stop"))

    async def async_media_next_track(self) -> None:
        """Go to the next track."""
        self._check(self.device.media_action("Next"))

    async def async_media_previous_track(self) -> None:
        """Go to the previous track."""
        self._check(self.device.media_action("Previous"))

    async def async_media_seek(self, position: float) -> None:
        """Jump to a position in seconds."""
        self._check(self.device.media_seek(int(position * 1000)))

    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume from 0 to 1."""
        self._check(self.device.set_volume(volume))

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute."""
        self._check(self.device.set_muted(mute))

    async def async_select_source(self, source: str) -> None:
        """Choose the player the controls act on."""
        self.device.select_player(source)

    def _check(self, sent: bool) -> None:
        if not sent:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_connected",
                translation_placeholders={"name": self.device.name},
            )
