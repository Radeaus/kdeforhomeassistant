"""Diagnostics for KDE Connect."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant

from . import KdeConnectConfigEntry
from .const import CONF_CERTIFICATE, CONF_PRIVATE_KEY

TO_REDACT = {CONF_CERTIFICATE, CONF_PRIVATE_KEY, CONF_MAC}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KdeConnectConfigEntry
) -> dict[str, Any]:
    """Return what is useful for debugging, without keys or certificates."""
    hub = entry.runtime_data.hub
    devices = []
    for device in entry.runtime_data.devices.values():
        info = hub.connected_info(device.device_id)
        devices.append(
            {
                "name": device.name,
                "device_type": device.device_type,
                "connected": device.connected,
                "protocol_version": info.protocol_version if info else None,
                "incoming_capabilities": sorted(info.incoming_capabilities)
                if info
                else None,
                "remote_commands": sorted(
                    command["name"] for command in device.remote_commands.values()
                ),
                "scripts": device.scripts,
                "has_mac": device.mac is not None,
                "locked": device.locked,
            }
        )
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "tcp_port": hub.tcp_port,
        "discovered": sorted(info.name for info in hub.discovered.values()),
        "devices": devices,
    }
