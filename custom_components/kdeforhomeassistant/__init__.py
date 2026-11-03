"""The KDE Connect integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    ANNOUNCE_INTERVAL,
    CONF_CERTIFICATE,
    CONF_DEVICE_ID,
    CONF_PRIVATE_KEY,
    DEFAULT_NAME,
    DOMAIN,
    INCOMING_CAPABILITIES,
    OUTGOING_CAPABILITIES,
    SUBENTRY_TYPE_DEVICE,
)
from .device import KdeConnectDevice
from .kdeconnect import DeviceInfo, Identity, KdeConnectHub
from .kdeconnect.protocol import UDP_PORT

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LOCK,
    Platform.NOTIFY,
]


@dataclass
class KdeConnectData:
    """What a loaded entry keeps at runtime."""

    hub: KdeConnectHub
    devices: dict[str, KdeConnectDevice]


type KdeConnectConfigEntry = ConfigEntry[KdeConnectData]


def identity_from_entry(entry: ConfigEntry) -> Identity:
    """Build our identity from the entry data and options."""
    return Identity(
        device_id=entry.data[CONF_DEVICE_ID],
        name=entry.options.get(CONF_NAME) or entry.title or DEFAULT_NAME,
        certificate_pem=entry.data[CONF_CERTIFICATE],
        private_key_pem=entry.data[CONF_PRIVATE_KEY],
    )


async def async_setup_entry(hass: HomeAssistant, entry: KdeConnectConfigEntry) -> bool:
    """Start listening for KDE Connect devices."""
    hub = KdeConnectHub(
        identity_from_entry(entry),
        incoming_capabilities=INCOMING_CAPABILITIES,
        outgoing_capabilities=OUTGOING_CAPABILITIES,
        udp_port=UDP_PORT,
    )
    try:
        await hub.start()
    except OSError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="port_in_use",
            translation_placeholders={"error": str(err)},
        ) from err

    devices = {
        subentry.subentry_id: KdeConnectDevice(hass, entry, subentry, hub)
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_DEVICE
    }
    hub.set_trusted(
        {device.device_id: device.certificate_der for device in devices.values()}
    )
    by_device_id = {device.device_id: device for device in devices.values()}

    @callback
    def unpaired(device_id: str) -> None:
        if device := by_device_id.get(device_id):
            _LOGGER.warning("%s removed the pairing with Home Assistant", device.name)
            ir.async_create_issue(
                hass,
                DOMAIN,
                f"unpaired_{device_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="device_unpaired",
                translation_placeholders={"name": device.name},
            )

    @callback
    def pair_request(info: DeviceInfo) -> None:
        _LOGGER.info(
            "%s asked to pair; add it from the KDE Connect integration in Home Assistant",
            info.name,
        )

    hub.on_unpaired = unpaired
    hub.on_pair_request = pair_request

    entry.runtime_data = KdeConnectData(hub=hub, devices=devices)
    for device in devices.values():
        entry.async_on_unload(device.async_start())

    async def announce(_now: datetime | None = None) -> None:
        """Ask disconnected devices to connect to us."""
        if devices and all(device.connected for device in devices.values()):
            return
        hosts = {
            str(address)
            for address in await network.async_get_ipv4_broadcast_addresses(hass)
        }
        for device in devices.values():
            info = hub.discovered.get(device.device_id)
            if not device.connected and info and info.host:
                hosts.add(info.host)
        hub.announce(hosts)

    entry.async_on_unload(async_track_time_interval(hass, announce, ANNOUNCE_INTERVAL))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    hass.async_create_task(announce(), eager_start=True)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KdeConnectConfigEntry) -> bool:
    """Close all connections."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.hub.stop()
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant, entry: KdeConnectConfigEntry
) -> None:
    """Reload when devices or options change."""
    await hass.config_entries.async_reload(entry.entry_id)
