"""Error and recovery paths of the config, options and device flows."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryDisabler, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kdeforhomeassistant.const import (
    DEFAULT_NAME,
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.kdeforhomeassistant.kdeconnect import PendingPairing
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_PAIR,
    generate_identity,
    pem_to_der,
)

from .fake_device import FakeDevice
from .test_init import _pair, _progress_until, _setup
from .test_legacy import _start_old, old_integration  # noqa: F401

FLOW = "custom_components.kdeforhomeassistant.config_flow"


@pytest.fixture
def config_dir(hass: HomeAssistant, tmp_path) -> str:
    """Keep the legacy folder out of the configuration folder all tests share."""
    hass.config.config_dir = str(tmp_path)
    return str(tmp_path)


async def _wait(predicate, timeout: float = 5) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.05)


async def _start(hass: HomeAssistant, entry):
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE), context={"source": "user"}
    )


async def _to_pick(hass: HomeAssistant, entry):
    result = await _start(hass, entry)
    result = await _progress_until(hass, result["flow_id"], result, "pick")
    assert result["step_id"] == "pick"
    return result


# Legacy import


def _write_legacy(folder: str, certificate: str, key: str | None, rows=None) -> None:
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "certificate.pem"), "w") as file:
        file.write(certificate)
    if key is not None:
        with open(os.path.join(folder, "privateKey.pem"), "w") as file:
            file.write(key)
    if rows is not None:
        conn = sqlite3.connect(os.path.join(folder, "konnect.db"))
        conn.execute(
            "CREATE TABLE trusted_devices (identifier TEXT PRIMARY KEY, "
            "certificate TEXT, name TEXT, type TEXT)"
        )
        conn.executemany("INSERT INTO trusted_devices VALUES (?, ?, ?, ?)", rows)
        conn.commit()
        conn.close()


async def _legacy_menu(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["import_legacy", "identity"]
    return result


async def test_import_legacy_unreadable(hass: HomeAssistant, config_dir) -> None:
    """A missing private key aborts the import."""
    identity = await hass.async_add_executor_job(generate_identity, "Old")
    await hass.async_add_executor_job(
        _write_legacy, os.path.join(config_dir, "kde_connect"), identity.certificate_pem, None
    )
    result = await _legacy_menu(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "import_failed"


async def test_import_legacy_invalid_device_id(
    hass: HomeAssistant, config_dir
) -> None:
    """A certificate without a usable device id aborts the import."""

    class _Uuid:
        hex = "not a device id"

    with patch(
        "custom_components.kdeforhomeassistant.kdeconnect.protocol.uuid.uuid4",
        return_value=_Uuid(),
    ):
        identity = await hass.async_add_executor_job(generate_identity, "Old")
    await hass.async_add_executor_job(
        _write_legacy,
        os.path.join(config_dir, "kde_connect"),
        identity.certificate_pem,
        identity.private_key_pem,
    )
    result = await _legacy_menu(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "import_failed"


async def test_import_legacy_certificate_formats(
    hass: HomeAssistant, config_dir
) -> None:
    """Certificates stored as PEM text or DER bytes are read; broken ones skipped."""
    legacy = await hass.async_add_executor_job(generate_identity, "Old HA")
    peers = [
        await hass.async_add_executor_job(generate_identity, f"Peer {i}")
        for i in range(3)
    ]
    rows = [
        (peers[0].device_id, peers[0].certificate_pem, "PEM, PC", "desktop"),
        (peers[1].device_id, pem_to_der(peers[1].certificate_pem), "", None),
        (peers[2].device_id, peers[2].certificate_pem.encode(), "Bytes", "phone"),
        ("broken_text_" + "0" * 24, "not a certificate", "Broken", "phone"),
        ("broken_null_" + "0" * 24, None, "Null", "phone"),
    ]
    await hass.async_add_executor_job(
        _write_legacy,
        os.path.join(config_dir, "kde_connect"),
        legacy.certificate_pem,
        legacy.private_key_pem,
        rows,
    )
    result = await _legacy_menu(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["step_id"] == "import_legacy"
    assert result["description_placeholders"]["devices"] == (
        f"PEM PC, {peers[1].device_id}, Bytes"
    )
    with patch(
        "custom_components.kdeforhomeassistant.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "..."}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == DEFAULT_NAME
        await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    devices = {sub.unique_id: sub.data for sub in entry.subentries.values()}
    assert set(devices) == {peer.device_id for peer in peers}
    assert devices[peers[1].device_id]["device_type"] == "unknown"
    assert pem_to_der(devices[peers[1].device_id]["certificate"]) == pem_to_der(
        peers[1].certificate_pem
    )


async def test_import_legacy_while_old_runs(
    hass: HomeAssistant, config_dir, old_integration  # noqa: F811
) -> None:
    """The import waits until the older integration has stopped."""
    old, _ = old_integration
    legacy = await hass.async_add_executor_job(generate_identity, "Old HA")
    await hass.async_add_executor_job(
        _write_legacy,
        os.path.join(config_dir, "kde_connect"),
        legacy.certificate_pem,
        legacy.private_key_pem,
    )
    # Disabled: the menu offers the import.
    await hass.config_entries.async_set_disabled_by(
        old.entry_id, ConfigEntryDisabler.USER
    )
    result = await _legacy_menu(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "import_legacy"}
    )
    assert result["step_id"] == "import_legacy"
    assert result["description_placeholders"]["devices"] == "-"

    # Started again before the form is sent.
    await hass.config_entries.async_set_disabled_by(old.entry_id, None)
    await hass.async_block_till_done()
    assert old.state is ConfigEntryState.LOADED
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "New"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "legacy_running"}

    await hass.config_entries.async_set_disabled_by(
        old.entry_id, ConfigEntryDisabler.USER
    )
    await hass.async_block_till_done()
    with patch(
        "custom_components.kdeforhomeassistant.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "New"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "New"
        await hass.async_block_till_done()


async def test_identity_when_legacy_folder_exists(
    hass: HomeAssistant, config_dir
) -> None:
    """Starting fresh is still possible when the old folder exists."""
    legacy = await hass.async_add_executor_job(generate_identity, "Old HA")
    await hass.async_add_executor_job(
        _write_legacy,
        os.path.join(config_dir, "kde_connect"),
        legacy.certificate_pem,
        legacy.private_key_pem,
    )
    result = await _legacy_menu(hass)
    with patch(
        "custom_components.kdeforhomeassistant.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "identity"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.data["device_id"] != legacy.device_id


# Options


async def test_options_flow(hass: HomeAssistant) -> None:
    """The name can be changed; an empty name falls back to the default."""
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    key = next(iter(schema))
    assert key.description["suggested_value"] == "Test - Home Assistant"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: "Living room!"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {CONF_NAME: "Living room"}
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.hub.identity.name == "Living room"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: "  "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {CONF_NAME: DEFAULT_NAME}
    assert await hass.config_entries.async_unload(entry.entry_id)


# Device subentry flow


async def test_not_loaded(hass: HomeAssistant) -> None:
    """Devices can only be added while the integration runs."""
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    result = await _start(hass, entry)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_loaded"


async def test_unloaded_while_picking(hass: HomeAssistant) -> None:
    """The entry stops while the user picks a device."""
    entry = await _setup(hass)
    result = await _to_pick(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device": "manual"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_loaded"


async def test_unloaded_on_manual_form(hass: HomeAssistant) -> None:
    """The entry stops while the user types an address."""
    entry = await _setup(hass)
    result = await _to_pick(hass, entry)
    flow_id = result["flow_id"]
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {"device": "manual"}
    )
    assert result["step_id"] == "manual"
    assert await hass.config_entries.async_unload(entry.entry_id)
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {CONF_HOST: "127.0.0.1"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_loaded"


async def test_unloaded_while_connecting(hass: HomeAssistant) -> None:
    """The entry stops while waiting for the device to connect."""
    entry = await _setup(hass)
    result = await _to_pick(hass, entry)
    flow_id = result["flow_id"]
    await hass.config_entries.subentries.async_configure(flow_id, {"device": "manual"})
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {CONF_HOST: " 127.0.0.1 "}
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["step_id"] == "connect"
    assert await hass.config_entries.async_unload(entry.entry_id)
    result = await hass.config_entries.subentries.async_configure(flow_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_loaded"


async def test_manual_host(hass: HomeAssistant) -> None:
    """A device that discovery missed is reached by its address."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    device = FakeDevice("Hidden PC")
    result = await _to_pick(hass, entry)
    assert result["description_placeholders"]["count"] == "0"
    flow_id = result["flow_id"]
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {"device": "manual"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {CONF_HOST: "127.0.0.1"}
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["step_id"] == "connect"
    # Still waiting.
    await asyncio.sleep(0.2)
    result = await hass.config_entries.subentries.async_configure(flow_id)
    assert result["step_id"] == "connect"
    await device.connect(hub.tcp_port)
    result = await _progress_until(hass, flow_id, result, "finish")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Hidden PC"
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert {sub.unique_id for sub in entry.subentries.values()} == {
        device.identity.device_id
    }
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_manual_host_not_found(hass: HomeAssistant) -> None:
    """Nothing connects from the address that was entered."""
    entry = await _setup(hass)
    result = await _to_pick(hass, entry)
    flow_id = result["flow_id"]
    await hass.config_entries.subentries.async_configure(flow_id, {"device": "manual"})
    with patch(f"{FLOW}.CONNECT_TIMEOUT", 0.3):
        result = await hass.config_entries.subentries.async_configure(
            flow_id, {CONF_HOST: "127.0.0.2"}
        )
        result = await _progress_until(hass, flow_id, result, "x")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_already_configured(hass: HomeAssistant) -> None:
    """A device that is already paired cannot be added again."""
    entry = await _setup(hass)
    device = FakeDevice("Desk PC")
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    hub = entry.runtime_data.hub
    await _wait(lambda: hub.is_link_connected(device.identity.device_id))

    result = await _to_pick(hass, entry)
    # Paired devices are not offered.
    assert result["description_placeholders"]["count"] == "0"
    flow_id = result["flow_id"]
    await hass.config_entries.subentries.async_configure(flow_id, {"device": "manual"})
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {CONF_HOST: "127.0.0.1"}
    )
    result = await _progress_until(hass, flow_id, result, "x")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_disconnects_before_pairing(hass: HomeAssistant) -> None:
    """The device goes away after connecting but before the request is sent."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    device = FakeDevice("Desk PC")
    result = await _to_pick(hass, entry)
    flow_id = result["flow_id"]
    await hass.config_entries.subentries.async_configure(flow_id, {"device": "manual"})
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {CONF_HOST: "127.0.0.1"}
    )
    assert result["step_id"] == "connect"
    task = hass.config_entries.subentries._progress[flow_id]._task
    await device.connect(hub.tcp_port)
    await asyncio.wait_for(asyncio.shield(task), 5)
    device.close()
    await _wait(lambda: not hub.is_link_connected(device.identity.device_id))
    result = await hass.config_entries.subentries.async_configure(flow_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def _to_pairing(hass: HomeAssistant, entry, device: FakeDevice):
    result = await _start(hass, entry)
    flow_id = result["flow_id"]
    await device.connect(entry.runtime_data.hub.tcp_port)
    result = await _progress_until(hass, flow_id, result, "pick")
    result = await hass.config_entries.subentries.async_configure(
        flow_id, {"device": device.identity.device_id}
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["step_id"] == "pair"
    assert result["description_placeholders"]["name"] == device.identity.name
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    return result


async def test_pair_timeout(hass: HomeAssistant) -> None:
    """The user does not accept on the device in time."""
    entry = await _setup(hass)
    device = FakeDevice("Desk PC", protocol_version=8)
    device.auto_accept = False
    wait = PendingPairing.wait

    async def short_wait(self, timeout: float = 30):
        return await wait(self, 0.3)

    with patch.object(PendingPairing, "wait", short_wait):
        result = await _to_pairing(hass, entry, device)
        result = await _progress_until(hass, result["flow_id"], result, "x")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "pair_timeout"
    # The device is told the request is over.
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    assert not entry.subentries
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_pair_connection_lost(hass: HomeAssistant) -> None:
    """The device disconnects while the pairing request is open."""
    entry = await _setup(hass)
    device = FakeDevice("Desk PC", protocol_version=8)
    device.auto_accept = False
    result = await _to_pairing(hass, entry, device)
    device.close()
    result = await _progress_until(hass, result["flow_id"], result, "x")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_flow_closed_while_discovering(hass: HomeAssistant) -> None:
    """Closing the dialog stops discovery and the running task."""
    entry = await _setup(hass)
    hub = entry.runtime_data.hub
    result = await _start(hass, entry)
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert hub._discovering == 1
    flow = hass.config_entries.subentries._progress[result["flow_id"]]
    task = flow._task
    hass.config_entries.subentries.async_abort(result["flow_id"])
    await asyncio.sleep(0)
    assert hub._discovering == 0
    assert task.cancelled() or task.done()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_reconfigure_invalid_mac(hass: HomeAssistant) -> None:
    """A malformed MAC address is refused; an empty one turns Wake-on-LAN off."""
    entry = await _setup(hass)
    device = FakeDevice("Desk PC")
    await _pair(hass, entry, device)
    device.close()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry = next(iter(entry.subentries.values()))
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert result["step_id"] == "reconfigure"
    assert result["description_placeholders"] == {"name": "Desk PC"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"mac": "not-a-mac"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"mac": "invalid_mac"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"mac": " "}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry = next(iter(entry.subentries.values()))
    assert subentry.data["mac"] is None
    assert subentry.data["scripts"] == []
    assert await hass.config_entries.async_unload(entry.entry_id)
