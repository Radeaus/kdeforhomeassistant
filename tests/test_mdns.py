"""Tests for the KDE Connect mDNS advertisement."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kdeforhomeassistant.const import (
    INCOMING_CAPABILITIES,
    OUTGOING_CAPABILITIES,
)
from custom_components.kdeforhomeassistant.kdeconnect import (
    KdeConnectHub,
    generate_identity,
)
from custom_components.kdeforhomeassistant.mdns import (
    SERVICE_TYPE,
    KdeConnectMdns,
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
    ):
        await mdns.async_start()
    return mdns, aiozc


async def test_advertises_service(hass: HomeAssistant) -> None:
    """The service has the identity fields and the TCP port from KDE Connect."""
    hub = _hub()
    mdns, aiozc = await _start(hass, hub)
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
    mdns, aiozc = await _start(hass, _hub(), addresses=[])
    aiozc.async_register_service.assert_not_awaited()
    assert mdns._info is None


async def test_registration_error_is_logged_and_swallowed(
    hass: HomeAssistant, caplog
) -> None:
    """mDNS trouble never propagates into integration setup."""
    aiozc = AsyncMock()
    aiozc.async_register_service.side_effect = OSError("boom")
    with caplog.at_level(logging.ERROR):
        mdns, _ = await _start(hass, _hub(), aiozc=aiozc)
    assert "mDNS" in caplog.text
    assert mdns._aiozc is None
    assert mdns._info is None


async def test_stop_unregisters_and_is_idempotent(hass: HomeAssistant) -> None:
    """Stopping removes the exact record and a second call does nothing."""
    mdns, aiozc = await _start(hass, _hub())
    info = mdns._info
    await mdns.async_stop()
    aiozc.async_unregister_service.assert_awaited_once_with(info)
    assert mdns._aiozc is None
    assert mdns._info is None
    await mdns.async_stop()
    assert aiozc.async_unregister_service.await_count == 1


async def test_addresses_filter_adapters(hass: HomeAssistant) -> None:
    """Only enabled adapters, no loopback, IPv4 and IPv6, without duplicates."""
    adapters = [
        {
            "name": "eth0",
            "enabled": True,
            "ipv4": [
                {"address": "192.0.2.10"},
                {"address": "127.0.0.1"},
                {"address": "192.0.2.10"},
            ],
            "ipv6": [
                {"address": "2001:db8::10"},
                {"address": "::1"},
            ],
        },
        {
            "name": "eth1",
            "enabled": False,
            "ipv4": [{"address": "198.51.100.5"}],
            "ipv6": [{"address": "2001:db8::20"}],
        },
    ]
    mdns = KdeConnectMdns(hass, _hub())
    with patch(
        "custom_components.kdeforhomeassistant.mdns.network.async_get_adapters",
        AsyncMock(return_value=adapters),
    ):
        assert await mdns._async_addresses() == ADDRESSES


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
