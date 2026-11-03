"""Fixtures for the KDE Connect tests."""

from __future__ import annotations

from collections.abc import Generator
from ipaddress import IPv4Address
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load the integration from custom_components."""


@pytest.fixture(autouse=True)
def local_network(socket_enabled: None) -> Generator[None]:
    """Keep discovery on localhost and off the real UDP port."""
    with (
        patch("custom_components.kdeforhomeassistant.UDP_PORT", 0),
        patch(
            "homeassistant.components.network.async_get_ipv4_broadcast_addresses",
            return_value={IPv4Address("127.255.255.255")},
        ),
    ):
        yield
