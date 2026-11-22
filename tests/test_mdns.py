"""Tests for the KDE Connect mDNS advertisement."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from zeroconf import ServiceStateChange

from custom_components.kdeforhomeassistant.const import (
    INCOMING_CAPABILITIES,
    OUTGOING_CAPABILITIES,
)
from custom_components.kdeforhomeassistant.kdeconnect import (
    KdeConnectHub,
    generate_identity,
)
from custom_components.kdeforhomeassistant.mdns import (
    RESOLVE_TIMEOUT,
    SERVICE_TYPE,
    KdeConnectMdns,
    _async_adapters,
)

from .test_init import _setup

ADDRESSES = ["192.0.2.10", "2001:db8::10"]


@pytest.fixture(autouse=True)
def no_mdns(mock_async_zeroconf) -> None:
    """Use the real mDNS methods in this module."""


def _hub() -> KdeConnectHub:
    hub = KdeConnectHub(
        generate_identity("Test"),
        incoming_capabilities=INCOMING_CAPABILITIES,
        outgoing_capabilities=OUTGOING_CAPABILITIES,
    )
    hub.tcp_port = 1716
    return hub


async def _start(hass: HomeAssistant, hub: KdeConnectHub, addresses=None, aiozc=None):
    mdns = KdeConnectMdns(hass, hub)
    aiozc = aiozc or AsyncMock()
    browser = AsyncMock()
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.zeroconf.async_get_async_instance",
            AsyncMock(return_value=aiozc),
        ),
        patch.object(
            KdeConnectMdns,
            "_async_addresses",
            AsyncMock(return_value=ADDRESSES if addresses is None else addresses),
        ),
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceBrowser",
            return_value=browser,
        ) as browser_cls,
    ):
        await mdns.async_start()
    return mdns, aiozc, browser_cls


async def test_advertises_service(hass: HomeAssistant) -> None:
    """The service has the identity fields and the TCP port from KDE Connect."""
    hub = _hub()
    mdns, aiozc, _ = await _start(hass, hub)
    aiozc.async_register_service.assert_awaited_once()
    info = aiozc.async_register_service.await_args.args[0]
    assert info.type == SERVICE_TYPE
    assert info.name == f"{hub.identity.device_id}.{SERVICE_TYPE}"
    assert info.port == 1716
    assert info.properties == {
        b"id": hub.identity.device_id.encode(),
        b"name": b"Test",
        b"type": b"desktop",
        b"protocol": b"8",
    }
    assert info.server.endswith(".local.")
    assert info.parsed_addresses() == ADDRESSES
    assert mdns._info is info


async def test_no_addresses_skips_registration(hass: HomeAssistant) -> None:
    """Without addresses there is nothing to advertise, and no error."""
    mdns, aiozc, browser_cls = await _start(hass, _hub(), addresses=[])
    aiozc.async_register_service.assert_not_awaited()
    assert mdns._info is None
    browser_cls.assert_called_once()


async def test_registration_error_is_logged_and_swallowed(
    hass: HomeAssistant, caplog
) -> None:
    """mDNS trouble never propagates into integration setup."""
    aiozc = AsyncMock()
    aiozc.async_register_service.side_effect = OSError("boom")
    with caplog.at_level(logging.ERROR):
        mdns, _, browser_cls = await _start(hass, _hub(), aiozc=aiozc)
    assert "mDNS" in caplog.text
    assert mdns._aiozc is aiozc
    assert mdns._info is None
    browser_cls.assert_called_once()
    assert mdns._browser is browser_cls.return_value


async def test_zeroconf_error_is_logged_and_swallowed(
    hass: HomeAssistant, caplog
) -> None:
    """Without the shared zeroconf instance there is nothing to start."""
    mdns = KdeConnectMdns(hass, _hub())
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.zeroconf.async_get_async_instance",
            AsyncMock(side_effect=OSError("boom")),
        ),
        caplog.at_level(logging.ERROR),
    ):
        await mdns.async_start()
    assert "Could not set up mDNS" in caplog.text
    assert mdns._aiozc is None
    assert mdns._browser is None


async def test_browser_error_is_logged_and_swallowed(
    hass: HomeAssistant, caplog
) -> None:
    """A browser failure does not undo the advertisement."""
    aiozc = AsyncMock()
    mdns = KdeConnectMdns(hass, _hub())
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.zeroconf.async_get_async_instance",
            AsyncMock(return_value=aiozc),
        ),
        patch.object(
            KdeConnectMdns,
            "_async_addresses",
            AsyncMock(return_value=ADDRESSES),
        ),
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceBrowser",
            side_effect=OSError("boom"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        await mdns.async_start()
    assert "Could not browse" in caplog.text
    assert mdns._info is not None
    assert mdns._browser is None


async def test_stop_unregisters_and_is_idempotent(hass: HomeAssistant) -> None:
    """Stopping cancels browsing, removes the record, and a second call is safe."""
    mdns, aiozc, _ = await _start(hass, _hub())
    info = mdns._info
    browser = mdns._browser
    task = hass.async_create_task(asyncio.sleep(60))
    mdns._tasks.add(task)
    mdns._last_announced["device"] = 1.0
    await mdns.async_stop()
    browser.async_cancel.assert_awaited_once()
    aiozc.async_unregister_service.assert_awaited_once_with(info)
    assert task.cancelled()
    assert not mdns._tasks
    assert mdns._last_announced == {}
    assert mdns._browser is None
    assert mdns._aiozc is None
    assert mdns._info is None
    await mdns.async_stop()
    assert browser.async_cancel.await_count == 1
    assert aiozc.async_unregister_service.await_count == 1


async def test_addresses_filter_adapters(hass: HomeAssistant) -> None:
    """Only enabled adapters, no loopback, IPv4 and IPv6, without duplicates."""
    adapters = [
        {
            "name": "eth0",
            "enabled": True,
            "default": True,
            "ipv4": [
                {"address": "192.0.2.10"},
                {"address": "127.0.0.1"},
                {"address": "192.0.2.10"},
            ],
            "ipv6": [
                {"address": "2001:db8::10"},
                {"address": "fe80::10%2"},
                {"address": "::1"},
            ],
        },
        {
            "name": "eth1",
            "enabled": False,
            "default": False,
            "ipv4": [{"address": "198.51.100.5"}],
            "ipv6": [{"address": "2001:db8::20"}],
        },
    ]
    mdns = KdeConnectMdns(hass, _hub())
    with patch(
        "custom_components.kdeforhomeassistant.mdns._async_adapters",
        AsyncMock(return_value=(adapters, set())),
    ):
        assert await mdns._async_addresses() == [*ADDRESSES, "fe80::10"]


async def test_addresses_prefer_physical_and_default(hass: HomeAssistant) -> None:
    """Virtual interfaces are skipped and the default adapter comes first."""
    adapters = [
        {
            "name": "docker0",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "172.17.0.1"}],
            "ipv6": [],
        },
        {
            "name": "eth0",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "192.0.2.10"}],
            "ipv6": [{"address": "2001:db8::10"}],
        },
        {
            "name": "eth1",
            "enabled": True,
            "default": True,
            "ipv4": [{"address": "198.51.100.5"}],
            "ipv6": [],
        },
        {
            "name": "hassio",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "172.30.32.1"}],
            "ipv6": [],
        },
        {
            "name": "veth0",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "172.18.0.1"}],
            "ipv6": [],
        },
    ]
    mdns = KdeConnectMdns(hass, _hub())
    with patch(
        "custom_components.kdeforhomeassistant.mdns._async_adapters",
        AsyncMock(return_value=(adapters, set())),
    ):
        assert await mdns._async_addresses() == [
            "198.51.100.5",
            "192.0.2.10",
            "2001:db8::10",
        ]


async def test_addresses_fall_back_to_virtual(hass: HomeAssistant) -> None:
    """Virtual addresses are advertised when no physical interface exists."""
    adapters = [
        {
            "name": "docker0",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "172.17.0.1"}],
            "ipv6": [],
        },
        {
            "name": "hassio",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "172.30.32.1"}],
            "ipv6": [],
        },
    ]
    mdns = KdeConnectMdns(hass, _hub())
    with patch(
        "custom_components.kdeforhomeassistant.mdns._async_adapters",
        AsyncMock(return_value=(adapters, set())),
    ):
        assert await mdns._async_addresses() == ["172.17.0.1", "172.30.32.1"]


async def test_addresses_keep_virtual_default(hass: HomeAssistant) -> None:
    """A virtual interface carrying the default route is still advertised."""
    adapters = [
        {
            "name": "docker0",
            "enabled": True,
            "default": True,
            "ipv4": [{"address": "172.17.0.1"}],
            "ipv6": [],
        },
        {
            "name": "eth0",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "192.0.2.10"}],
            "ipv6": [],
        },
    ]
    mdns = KdeConnectMdns(hass, _hub())
    with patch(
        "custom_components.kdeforhomeassistant.mdns._async_adapters",
        AsyncMock(return_value=(adapters, set())),
    ):
        assert await mdns._async_addresses() == ["172.17.0.1", "192.0.2.10"]


async def test_addresses_keep_configured_virtual(hass: HomeAssistant) -> None:
    """An explicitly configured virtual adapter is not filtered out."""
    adapters = [
        {
            "name": "docker0",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "172.17.0.1"}],
            "ipv6": [],
        },
        {
            "name": "eth0",
            "enabled": True,
            "default": False,
            "ipv4": [{"address": "192.0.2.10"}],
            "ipv6": [],
        },
    ]
    mdns = KdeConnectMdns(hass, _hub())
    with patch(
        "custom_components.kdeforhomeassistant.mdns._async_adapters",
        AsyncMock(return_value=(adapters, {"docker0"})),
    ):
        assert await mdns._async_addresses() == ["172.17.0.1", "192.0.2.10"]


async def test_adapters_include_configured_names(hass: HomeAssistant) -> None:
    """The network integration's adapters and configured names are returned."""
    adapters = [
        {
            "name": "eth0",
            "enabled": True,
            "default": True,
            "ipv4": [{"address": "192.0.2.10"}],
            "ipv6": [],
        }
    ]
    net = MagicMock()
    net.configured_adapters = ["eth0"]
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.network.async_get_network",
            AsyncMock(return_value=net),
        ),
        patch(
            "custom_components.kdeforhomeassistant.mdns.network.async_get_adapters",
            AsyncMock(return_value=adapters),
        ),
    ):
        loaded, configured = await _async_adapters(hass)
    assert loaded is adapters
    assert configured == {"eth0"}


async def test_setup_starts_and_unload_stops_mdns(hass: HomeAssistant) -> None:
    """The config entry owns the advertisement for its whole lifetime."""
    with (
        patch.object(KdeConnectMdns, "async_start", AsyncMock()) as start,
        patch.object(KdeConnectMdns, "async_stop", AsyncMock()) as stop,
    ):
        entry = await _setup(hass)
        start.assert_awaited_once()
        assert await hass.config_entries.async_unload(entry.entry_id)
        stop.assert_awaited_once()


def _resolved(addresses: list[str]) -> MagicMock:
    info = MagicMock()
    info.async_request = AsyncMock(return_value=True)
    info.parsed_scoped_addresses.return_value = addresses
    return info


def _added(mdns: KdeConnectMdns, device_id: str) -> None:
    mdns._service_state_changed(
        mdns._aiozc.zeroconf,
        SERVICE_TYPE,
        f"{device_id}.{SERVICE_TYPE}",
        ServiceStateChange.Added,
    )


async def test_browse_announces_resolved_addresses(hass: HomeAssistant) -> None:
    """A discovered peer is asked to reconnect to the resolved addresses."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved(["192.0.2.10", "fe80::1%2"])
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ) as info_cls,
        patch.object(hub, "announce") as announce,
    ):
        _added(mdns, "device")
        await hass.async_block_till_done()
    info_cls.assert_called_once_with(SERVICE_TYPE, f"device.{SERVICE_TYPE}")
    info.async_request.assert_awaited_once_with(
        mdns._aiozc.zeroconf, RESOLVE_TIMEOUT
    )
    announce.assert_called_once_with(["192.0.2.10", "fe80::1%2"])


async def test_browse_announces_updated_service(hass: HomeAssistant) -> None:
    """An updated service is re-announced so the device can reconnect."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved(["fe80::10%2"])
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ),
        patch.object(hub, "announce") as announce,
    ):
        mdns._service_state_changed(
            mdns._aiozc.zeroconf,
            SERVICE_TYPE,
            f"device.{SERVICE_TYPE}",
            ServiceStateChange.Updated,
        )
        await hass.async_block_till_done()
    announce.assert_called_once_with(["fe80::10%2"])


async def test_browse_ignores_own_device(hass: HomeAssistant) -> None:
    """The integration never announces to itself."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    with (
        patch("custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo") as cls,
        patch.object(hub, "announce") as announce,
    ):
        _added(mdns, hub.identity.device_id)
        await hass.async_block_till_done()
    cls.assert_not_called()
    announce.assert_not_called()


async def test_browse_ignores_connected_device(hass: HomeAssistant) -> None:
    """A device that already has a link does not need another announcement."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    hub._links["device"] = MagicMock()
    with (
        patch("custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo") as cls,
        patch.object(hub, "announce") as announce,
    ):
        _added(mdns, "device")
        await hass.async_block_till_done()
    cls.assert_not_called()
    announce.assert_not_called()


async def test_browse_ignores_resolution_failure(hass: HomeAssistant) -> None:
    """An unresolved service is skipped."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved([])
    info.async_request.return_value = False
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ),
        patch.object(hub, "announce") as announce,
    ):
        _added(mdns, "device")
        await hass.async_block_till_done()
    info.parsed_scoped_addresses.assert_not_called()
    announce.assert_not_called()


async def test_browse_ignores_resolution_error(
    hass: HomeAssistant, caplog
) -> None:
    """A resolver error is logged at debug and does not announce."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved([])
    info.async_request.side_effect = OSError("boom")
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ),
        patch.object(hub, "announce") as announce,
        caplog.at_level(logging.DEBUG),
    ):
        _added(mdns, "device")
        await hass.async_block_till_done()
    assert "Could not resolve" in caplog.text
    announce.assert_not_called()


async def test_browse_ignores_device_connected_during_resolve(
    hass: HomeAssistant,
) -> None:
    """A device that connects while resolving is not announced to."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved(["192.0.2.10"])
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ),
        patch.object(hub, "is_link_connected", side_effect=[False, True]),
        patch.object(hub, "announce") as announce,
    ):
        _added(mdns, "device")
        await hass.async_block_till_done()
    announce.assert_not_called()


async def test_browse_ignores_empty_addresses(hass: HomeAssistant) -> None:
    """A resolved service without usable addresses is skipped."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved([])
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ),
        patch.object(hub, "announce") as announce,
    ):
        _added(mdns, "device")
        await hass.async_block_till_done()
    announce.assert_not_called()


async def test_browse_throttles_announcements(hass: HomeAssistant) -> None:
    """Repeated discovery within the interval announces once."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved(["192.0.2.10"])
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ),
        patch("custom_components.kdeforhomeassistant.mdns.time") as mdns_time,
        patch.object(hub, "announce") as announce,
    ):
        mdns_time.monotonic.side_effect = [0.0, 1.0, 10.0]
        for _ in range(3):
            _added(mdns, "device")
            await hass.async_block_till_done()
    assert announce.call_count == 2


async def test_removed_clears_throttle(hass: HomeAssistant) -> None:
    """A service that disappears can be announced again immediately."""
    hub = _hub()
    mdns, _, _ = await _start(hass, hub)
    info = _resolved(["192.0.2.10"])
    with (
        patch(
            "custom_components.kdeforhomeassistant.mdns.AsyncServiceInfo",
            return_value=info,
        ),
        patch("custom_components.kdeforhomeassistant.mdns.time") as mdns_time,
        patch.object(hub, "announce") as announce,
    ):
        mdns_time.monotonic.return_value = 0.0
        _added(mdns, "device")
        await hass.async_block_till_done()
        mdns._service_state_changed(
            mdns._aiozc.zeroconf,
            SERVICE_TYPE,
            f"device.{SERVICE_TYPE}",
            ServiceStateChange.Removed,
        )
        _added(mdns, "device")
        await hass.async_block_till_done()
    assert announce.call_count == 2
