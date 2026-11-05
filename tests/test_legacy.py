"""The older KDE Connect integration (bartv2/kde_connect) must not run alongside."""

from __future__ import annotations

import socket

import pytest
from homeassistant.config_entries import (
    ConfigEntryDisabler,
    ConfigEntryState,
    ConfigFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

from custom_components.kdeforhomeassistant.const import DOMAIN
from custom_components.kdeforhomeassistant.legacy import LEGACY_ISSUE_ID


@pytest.fixture
def old_integration(hass: HomeAssistant):
    """A stand-in for bartv2/kde_connect that holds a port while it runs."""
    held: list[socket.socket] = []

    async def setup_entry(hass, entry):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", 0))
        held.append(sock)
        return True

    async def unload_entry(hass, entry):
        for sock in held:
            sock.close()
        held.clear()
        return True

    mock_integration(
        hass,
        MockModule(
            "kde_connect",
            async_setup_entry=setup_entry,
            async_unload_entry=unload_entry,
        ),
    )
    mock_platform(hass, "kde_connect.config_flow", None)
    entry = MockConfigEntry(
        domain="kde_connect", title="HomeAssistant", data={"name": "HomeAssistant"}
    )
    entry.add_to_hass(hass)

    class OldFlow(ConfigFlow):
        VERSION = 1

    with mock_config_flow("kde_connect", OldFlow):
        yield entry, held


async def _start_old(hass: HomeAssistant, entry) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.parametrize(
    ("choice", "removed"), [("legacy_disable", False), ("legacy_remove", True)]
)
async def test_setup_offers_disable_or_remove(
    hass: HomeAssistant, old_integration, choice: str, removed: bool
) -> None:
    """Adding the integration first asks what to do with the older one."""
    old, held = old_integration
    await _start_old(hass, old)
    hass.config.location_name = "Test"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "old_integration"
    assert result["description_placeholders"] == {"name": "HomeAssistant"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": choice}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test - Home Assistant"
    await hass.async_block_till_done()

    assert not held, "the older integration still holds its port"
    if removed:
        assert hass.config_entries.async_get_entry(old.entry_id) is None
    else:
        assert old.disabled_by is ConfigEntryDisabler.USER
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(DOMAIN, LEGACY_ISSUE_ID) is None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_disabled_old_integration_is_left_alone(
    hass: HomeAssistant, old_integration
) -> None:
    """A disabled older integration cannot start, so nothing is asked."""
    old, _ = old_integration
    await hass.config_entries.async_set_disabled_by(
        old.entry_id, ConfigEntryDisabler.USER
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, LEGACY_ISSUE_ID) is None
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("choice", ["legacy_disable", "legacy_remove"])
async def test_repair_for_existing_setups(
    hass: HomeAssistant, hass_client, old_integration, choice: str
) -> None:
    """Someone who already has both gets a repair that fixes it in one step."""
    from custom_components.kdeforhomeassistant.const import (
        CONF_CERTIFICATE,
        CONF_DEVICE_ID,
        CONF_PRIVATE_KEY,
    )
    from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
        generate_identity,
    )

    old, held = old_integration
    await _start_old(hass, old)
    identity = await hass.async_add_executor_job(generate_identity, "HomeAssistant")
    ours = MockConfigEntry(
        domain=DOMAIN,
        title="HomeAssistant",
        data={
            CONF_DEVICE_ID: identity.device_id,
            CONF_CERTIFICATE: identity.certificate_pem,
            CONF_PRIVATE_KEY: identity.private_key_pem,
        },
    )
    ours.add_to_hass(hass)
    assert await hass.config_entries.async_setup(ours.entry_id)
    await hass.async_block_till_done()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, LEGACY_ISSUE_ID)
    assert issue is not None
    assert issue.is_fixable
    assert issue.translation_placeholders == {"name": "HomeAssistant"}

    assert await async_setup_component(hass, "repairs", {})
    client = await hass_client()
    resp = await client.post(
        "/api/repairs/issues/fix", json={"handler": DOMAIN, "issue_id": LEGACY_ISSUE_ID}
    )
    flow = await resp.json()
    assert flow["type"] == "menu"
    assert flow["menu_options"] == ["legacy_disable", "legacy_remove"]
    resp = await client.post(
        f"/api/repairs/issues/fix/{flow['flow_id']}", json={"next_step_id": choice}
    )
    assert (await resp.json())["type"] == "create_entry"
    await hass.async_block_till_done()

    assert not held
    assert ir.async_get(hass).async_get_issue(DOMAIN, LEGACY_ISSUE_ID) is None
    assert ours.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(ours.entry_id)


async def test_repair_follows_manual_changes(
    hass: HomeAssistant, old_integration
) -> None:
    """Disabling the older one by hand also clears the repair."""
    old, _ = old_integration
    await _start_old(hass, old)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "legacy_disable"}
    )
    await hass.async_block_till_done()
    # Turned on again by hand: the repair comes back.
    await hass.config_entries.async_set_disabled_by(old.entry_id, None)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, LEGACY_ISSUE_ID) is not None
    await hass.config_entries.async_set_disabled_by(
        old.entry_id, ConfigEntryDisabler.USER
    )
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, LEGACY_ISSUE_ID) is None
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_unload(entry.entry_id)
