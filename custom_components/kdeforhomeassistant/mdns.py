"""Advertise KDE Connect over mDNS for IPv6 discovery.

KDE Connect uses mDNS/DNS-SD to find peers on IPv6 networks: it publishes the
``_kdeconnect._udp`` service and resolves the addresses of other devices.
"""

from __future__ import annotations

import contextlib
import ipaddress
import logging
import socket

from homeassistant.components import network, zeroconf
from homeassistant.core import HomeAssistant
from zeroconf import ServiceInfo

from .kdeconnect import KdeConnectHub
from .kdeconnect.protocol import PROTOCOL_VERSION

_LOGGER = logging.getLogger(__name__)

SERVICE_TYPE = "_kdeconnect._udp.local."


class KdeConnectMdns:
    """Publish Home Assistant's KDE Connect service via mDNS."""

    def __init__(self, hass: HomeAssistant, hub: KdeConnectHub) -> None:
        self.hass = hass
        self._hub = hub
        self._aiozc = None
        self._info: ServiceInfo | None = None

    async def async_start(self) -> None:
        """Register the service, never letting mDNS break setup."""
        try:
            aiozc = await zeroconf.async_get_async_instance(self.hass)
            addresses = await self._async_addresses()
            if not addresses:
                _LOGGER.debug("No addresses available to advertise over mDNS")
                return
            info = self._service_info(addresses)
            await aiozc.async_register_service(info)
        except Exception:
            _LOGGER.exception("Could not advertise KDE Connect over mDNS")
            return
        self._aiozc = aiozc
        self._info = info

    def _service_info(self, addresses: list[str]) -> ServiceInfo:
        """Build the DNS-SD record KDE Connect devices expect."""
        identity = self._hub.identity
        device_id = identity.device_id
        return ServiceInfo(
            type_=SERVICE_TYPE,
            name=f"{device_id}.{SERVICE_TYPE}",
            port=self._hub.tcp_port,
            properties={
                "id": device_id,
                "name": identity.name,
                "type": identity.device_type,
                "protocol": str(PROTOCOL_VERSION),
            },
            server=f"{socket.gethostname().split('.')[0] or 'home-assistant'}.local.",
            parsed_addresses=addresses,
        )

    async def _async_addresses(self) -> list[str]:
        """Return the enabled, non-loopback addresses of this host."""
        addresses: list[str] = []
        for adapter in await network.async_get_adapters(self.hass):
            if not adapter["enabled"]:
                continue
            for entry in (*adapter["ipv4"], *adapter["ipv6"]):
                address = entry["address"]
                if ipaddress.ip_address(address).is_loopback:
                    continue
                if address not in addresses:
                    addresses.append(address)
        return addresses

    async def async_stop(self) -> None:
        """Unregister the service; safe to call more than once."""
        if self._info is not None and self._aiozc is not None:
            with contextlib.suppress(Exception):
                await self._aiozc.async_unregister_service(self._info)
        self._aiozc = None
        self._info = None
