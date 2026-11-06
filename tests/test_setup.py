"""Setup, unload and removal of the entry, the sidebar panel and repairs."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.kdeforhomeassistant.const import (
    ANNOUNCE_INTERVAL,
    DOMAIN,
    PANEL_URL_PATH,
)
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_PAIR,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    Packet,
)
from custom_components.kdeforhomeassistant.legacy import (
    LEGACY_ISSUE_ID,
    async_disable_legacy,
)
from custom_components.kdeforhomeassistant.repairs import async_create_fix_flow

from .fake_device import FakeDevice
from .test_init import _pair, _setup
from .test_legacy import _start_old, old_integration  # noqa: F401


async def _wait(predicate, timeout: float = 5) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.05)


async def _paired(hass: HomeAssistant, device: FakeDevice):
    """Pair the device and connect it to the reloaded entry."""
    entry = await _setup(hass)
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    device.packets.clear()
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for(PACKET_TYPE_RUNCOMMAND_REQUEST, requestCommandList=True)
    await hass.async_block_till_done()
    return entry


async def test_device_removes_pairing(hass: HomeAssistant) -> None:
    """A paired device that unpairs on its side raises a repair issue."""
    device = FakeDevice("Desk PC")
    entry = await _paired(hass, device)
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    issue_id = f"unpaired_{device.identity.device_id}"
    registry = ir.async_get(hass)
    await _wait(lambda: registry.async_get_issue(DOMAIN, issue_id) is not None)
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue.translation_key == "device_unpaired"
    assert issue.translation_placeholders == {"name": "Desk PC"}
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_announce(hass: HomeAssistant) -> None:
    """Disconnected devices are asked to connect; nothing is sent when all are."""
    device = FakeDevice("Desk PC")
    entry = await _paired(hass, device)
    hub = entry.runtime_data.hub
    with patch.object(hub, "announce") as announce:
        async_fire_time_changed(hass, dt_util.utcnow() + ANNOUNCE_INTERVAL)
        await hass.async_block_till_done()
        announce.assert_not_called()

        device.close()
        await _wait(lambda: not hub.is_link_connected(device.identity.device_id))
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + 2 * ANNOUNCE_INTERVAL)
        await hass.async_block_till_done()
        announce.assert_called_once()
        assert announce.call_args.args[0] == {"127.255.255.255", "127.0.0.1"}
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_panel_added_and_removed(hass: HomeAssistant) -> None:
    """The sidebar page is added once and goes away with the entry."""
    assert await async_setup_component(hass, "frontend", {})
    entry = await _setup(hass)
    panels = hass.data[frontend.DATA_PANELS]
    panel = panels[PANEL_URL_PATH]
    assert panel.require_admin
    assert "kde-panel.js?v=" in panel.config["_panel_custom"]["module_url"]

    # A reload keeps the same page.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[frontend.DATA_PANELS][PANEL_URL_PATH] is panel

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data[frontend.DATA_PANELS]


async def test_panel_removed_without_frontend(hass: HomeAssistant) -> None:
    """Without the frontend there is no page to add or remove."""
    entry = await _setup(hass)
    assert "frontend" not in hass.config.components
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_unknown_repair(hass: HomeAssistant) -> None:
    """Only the legacy issue has a fix flow."""
    with pytest.raises(ValueError):
        await async_create_fix_flow(hass, "something_else", None)


async def test_retry_after_legacy_disabled(
    hass: HomeAssistant, old_integration  # noqa: F811
) -> None:
    """Disabling the older integration starts ours right away."""
    old, _ = old_integration
    await _start_old(hass, old)
    hass.config.location_name = "Test"
    with patch(
        "custom_components.kdeforhomeassistant.KdeConnectHub.start",
        side_effect=OSError("Address in use"),
    ):
        # Set up through the import of an identity, not the flow, which
        # would stop the older one first.
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        from custom_components.kdeforhomeassistant.const import (
            CONF_CERTIFICATE,
            CONF_DEVICE_ID,
            CONF_PRIVATE_KEY,
        )
        from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
            generate_identity,
        )

        identity = await hass.async_add_executor_job(generate_identity, "HA")
        ours = MockConfigEntry(
            domain=DOMAIN,
            title="HA",
            data={
                CONF_DEVICE_ID: identity.device_id,
                CONF_CERTIFICATE: identity.certificate_pem,
                CONF_PRIVATE_KEY: identity.private_key_pem,
            },
        )
        ours.add_to_hass(hass)
        await hass.config_entries.async_setup(ours.entry_id)
        await hass.async_block_till_done()
        assert ours.state is ConfigEntryState.SETUP_RETRY

    await async_disable_legacy(hass)
    await hass.async_block_till_done()
    assert ours.state is ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(DOMAIN, LEGACY_ISSUE_ID) is None
    assert await hass.config_entries.async_unload(ours.entry_id)
