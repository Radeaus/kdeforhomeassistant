"""Constants for the KDE Connect integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from .kdeconnect.protocol import (
    PACKET_TYPE_FINDMYPHONE_REQUEST,
    PACKET_TYPE_LOCK,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_NOTIFICATION,
    PACKET_TYPE_PING,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
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

DEFAULT_NAME: Final = "Home Assistant"

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
)
OUTGOING_CAPABILITIES: Final = (
    PACKET_TYPE_PING,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    PACKET_TYPE_NOTIFICATION,
    PACKET_TYPE_FINDMYPHONE_REQUEST,
    PACKET_TYPE_LOCK_REQUEST,
)
