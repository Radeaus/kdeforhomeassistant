"""Advertise and browse KDE Connect over mDNS for IPv6 discovery.

KDE Connect uses mDNS/DNS-SD to find peers on IPv6 networks: it publishes the
``_kdeconnect._udp`` service and resolves the addresses of other devices.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import socket
import time

from homeassistant.components import network, zeroconf
from homeassistant.core import HomeAssistant
from zeroconf import ServiceInfo, ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

from .kdeconnect import KdeConnectHub
from .kdeconnect.protocol import PROTOCOL_VERSION

_LOGGER = logging.getLogger(__name__)

SERVICE_TYPE = "_kdeconnect._udp.local."
RESOLVE_TIMEOUT = 3000
ANNOUNCE_INTERVAL = 5
_VIRTUAL_INTERFACE_PREFIXES = (
    "virbr",
    "vnet",
    "vmnet",
    "vboxnet",
    "docker",
    "br-",
    "veth",
    "hassio",
    "podman",
    "cni",
    "flannel",
    "awdl",
    "llw",
)


def _is_virtual_interface(name: str) -> bool:
    """Return whether an interface is a virtual/bridge device peers cannot reach."""
    return name.startswith(_VIRTUAL_INTERFACE_PREFIXES)


async def _async_adapters(
    hass: HomeAssistant,
) -> tuple[list[network.Adapter], set[str]]:
    """Return the enabled adapters and the names the user configured."""
    configured = set((await network.async_get_network(hass)).configured_adapters)
    return await network.async_get_adapters(hass), configured


def _adapter_addresses(adapter: network.Adapter) -> list[str]:
    """Return the enabled adapter's non-loopback addresses, in order."""
    addresses: list[str] = []
    for entry in (*adapter["ipv4"], *adapter["ipv6"]):
        address = entry["address"].split("%", 1)[0]
        if ipaddress.ip_address(address).is_loopback:
            continue
        addresses.append(address)
    return addresses


class KdeConnectMdns:
    """Publish Home Assistant's KDE Connect service via mDNS."""

    def __init__(self, hass: HomeAssistant, hub: KdeConnectHub) -> None:
        self.hass = hass
        self._hub = hub
        self._aiozc = None
        self._info: ServiceInfo | None = None
        self._browser: AsyncServiceBrowser | None = None
        self._tasks: set[asyncio.Task] = set()
        self._last_announced: dict[str, float] = {}

    async def async_start(self) -> None:
        """Advertise and browse, never letting mDNS break setup."""
        try:
            aiozc = await zeroconf.async_get_async_instance(self.hass)
        except Exception:
            _LOGGER.exception("Could not set up mDNS for KDE Connect")
            return
        self._aiozc = aiozc
        try:
            addresses = await self._async_addresses()
            if not addresses:
                _LOGGER.debug("No addresses available to advertise over mDNS")
            else:
                info = self._service_info(addresses)
                await aiozc.async_register_service(info)
                self._info = info
        except Exception:
            _LOGGER.exception("Could not advertise KDE Connect over mDNS")
        try:
            self._start_browser()
        except Exception:
            _LOGGER.exception("Could not browse for KDE Connect devices over mDNS")

    def _start_browser(self) -> None:
        """Browse for devices advertising the KDE Connect service."""
        self._browser = AsyncServiceBrowser(
            self._aiozc.zeroconf,
            SERVICE_TYPE,
            handlers=[self._service_state_changed],
        )

    def _service_state_changed(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Resolve new or updated peers and forget vanished ones."""
        if state_change in (
            ServiceStateChange.Added,
            ServiceStateChange.Updated,
        ):
            task = self.hass.async_create_task(self._async_service_added(name))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        elif state_change is ServiceStateChange.Removed:
            self._last_announced.pop(name.split(".", 1)[0], None)

    async def _async_service_added(self, name: str) -> None:
        """Ask a discovered device to reconnect to us."""
        device_id = name.split(".", 1)[0]
        if (
            device_id == self._hub.identity.device_id
            or self._hub.is_link_connected(device_id)
        ):
            return
        info = AsyncServiceInfo(SERVICE_TYPE, name)
        try:
            if not await info.async_request(self._aiozc.zeroconf, RESOLVE_TIMEOUT):
                return
        except Exception as err:
            _LOGGER.debug("Could not resolve %s: %s", name, err)
            return
        if (
            device_id == self._hub.identity.device_id
            or self._hub.is_link_connected(device_id)
        ):
            return
        addresses = info.parsed_scoped_addresses()
        if not addresses:
            return
        now = time.monotonic()
        last = self._last_announced.get(device_id)
        if last is not None and now - last < ANNOUNCE_INTERVAL:
            return
        self._last_announced[device_id] = now
        self._hub.announce(addresses)

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
        default: list[str] = []
        physical: list[str] = []
        virtual: list[str] = []
        adapters, configured = await _async_adapters(self.hass)
        for adapter in adapters:
            if not adapter["enabled"]:
                continue
            addresses = _adapter_addresses(adapter)
            if adapter["default"]:
                default.extend(addresses)
            if (
                _is_virtual_interface(adapter["name"])
                and adapter["name"] not in configured
            ):
                virtual.extend(addresses)
                continue
            physical.extend(addresses)
        chosen = [*default, *physical] if default or physical else virtual
        return list(dict.fromkeys(chosen))

    async def async_stop(self) -> None:
        """Stop browsing and unregister the service; safe to call more than once."""
        if self._browser is not None:
            with contextlib.suppress(Exception):
                await self._browser.async_cancel()
            self._browser = None
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        if self._info is not None and self._aiozc is not None:
            with contextlib.suppress(Exception):
                await self._aiozc.async_unregister_service(self._info)
        self._aiozc = None
        self._info = None
        self._last_announced.clear()
