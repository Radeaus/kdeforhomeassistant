"""Constants for the KDE for Home Assistant integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from .kdeconnect.protocol import (
    PACKET_TYPE_FINDMYPHONE_REQUEST,
    PACKET_TYPE_LOCK,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_MOUSEPAD_KEYBOARDSTATE,
    PACKET_TYPE_MOUSEPAD_REQUEST,
    PACKET_TYPE_MPRIS,
    PACKET_TYPE_MPRIS_REQUEST,
    PACKET_TYPE_NOTIFICATION,
    PACKET_TYPE_PING,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    PACKET_TYPE_SYSTEMVOLUME,
    PACKET_TYPE_SYSTEMVOLUME_REQUEST,
    filter_device_name,
)

DOMAIN: Final = "kdeforhomeassistant"

SUBENTRY_TYPE_DEVICE: Final = "device"

# Main entry: our own identity.
CONF_DEVICE_ID: Final = "device_id"
CONF_CERTIFICATE: Final = "certificate"
CONF_PRIVATE_KEY: Final = "private_key"

# Device subentries.
CONF_DEVICE_TYPE: Final = "device_type"
CONF_CAPABILITIES: Final = "capabilities"
CONF_SCRIPTS: Final = "scripts"
CONF_HIDDEN_COMMANDS: Final = "hidden_commands"

DEFAULT_NAME: Final = "Home Assistant"
NAME_SUFFIX: Final = " - Home Assistant"

PANEL_URL_PATH: Final = "kde-for-home-assistant"
PANEL_ELEMENT: Final = "kde-for-home-assistant-panel"
PANEL_STATIC_URL: Final = "/kdeforhomeassistant_static"
SIGNAL_UPDATE: Final = f"{DOMAIN}_update"
PAIR_NOTIFICATION_ID: Final = f"{DOMAIN}_pair_request"

# Folder used by the older "KDE Connect" custom integration (bartv2/kde_connect).
LEGACY_CONFIG_DIR: Final = "kde_connect"
LEGACY_DOMAIN: Final = "kde_connect"

ANNOUNCE_INTERVAL: Final = timedelta(seconds=30)
DISCOVERY_TIME: Final = 4
CONNECT_TIMEOUT: Final = 15

INCOMING_CAPABILITIES: Final = (
    PACKET_TYPE_PING,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    PACKET_TYPE_LOCK,
    PACKET_TYPE_MOUSEPAD_KEYBOARDSTATE,
    PACKET_TYPE_MPRIS,
    PACKET_TYPE_SYSTEMVOLUME,
)
OUTGOING_CAPABILITIES: Final = (
    PACKET_TYPE_PING,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    PACKET_TYPE_NOTIFICATION,
    PACKET_TYPE_FINDMYPHONE_REQUEST,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_MOUSEPAD_REQUEST,
    PACKET_TYPE_MPRIS_REQUEST,
    PACKET_TYPE_SYSTEMVOLUME_REQUEST,
)


def default_name(location_name: str | None) -> str:
    """Return the name devices see, like "Home - Home Assistant"."""
    base = filter_device_name(location_name)
    if not base or base == DEFAULT_NAME:
        return DEFAULT_NAME
    return base[: 32 - len(NAME_SUFFIX)].rstrip() + NAME_SUFFIX
