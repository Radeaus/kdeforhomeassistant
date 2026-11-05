"""Config flow for KDE for Home Assistant."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sqlite3
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components import network
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlowWithReload,
    SubentryFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_CAPABILITIES,
    CONF_CERTIFICATE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_PRIVATE_KEY,
    CONF_SCRIPTS,
    CONNECT_TIMEOUT,
    DEFAULT_NAME,
    DISCOVERY_TIME,
    DOMAIN,
    LEGACY_CONFIG_DIR,
    LEGACY_DOMAIN,
    PANEL_URL_PATH,
    SUBENTRY_TYPE_DEVICE,
    default_name,
)
from .device import read_mac_address
from .legacy import (
    active_legacy_entries,
    async_disable_legacy,
    async_remove_legacy,
    legacy_name,
)
from .kdeconnect import (
    DeviceInfo,
    KdeConnectHub,
    PairingError,
    PendingPairing,
    generate_identity,
)
from .kdeconnect.protocol import (
    certificate_common_name,
    der_to_pem,
    filter_device_name,
    is_valid_device_id,
    pem_to_der,
)

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE = "device"
MANUAL = "manual"


class KdeConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Home Assistant as a KDE Connect device."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> KdeConnectOptionsFlow:
        """Return the options flow."""
        return KdeConnectOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Devices are added as subentries."""
        return {SUBENTRY_TYPE_DEVICE: DeviceSubentryFlow}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer to take over the pairing of the older integration, if there is one."""
        if active_legacy_entries(self.hass):
            return await self.async_step_old_integration()
        legacy = self.hass.config.path(LEGACY_CONFIG_DIR, "certificate.pem")
        if await self.hass.async_add_executor_job(os.path.isfile, legacy):
            return self.async_show_menu(
                step_id="user", menu_options=["import_legacy", "identity"]
            )
        return await self.async_step_identity()

    async def async_step_old_integration(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Both use the same ports, so the older one has to stop first."""
        return self.async_show_menu(
            step_id="old_integration",
            menu_options=["legacy_disable", "legacy_remove"],
            description_placeholders={"name": legacy_name(self.hass)},
        )

    async def async_step_legacy_disable(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Disable the older integration, then continue."""
        await async_disable_legacy(self.hass)
        return await self.async_step_user()

    async def async_step_legacy_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove the older integration, then continue."""
        await async_remove_legacy(self.hass)
        return await self.async_step_user()

    async def async_step_identity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create our identity; naming and pairing happen on the panel."""
        name = default_name(self.hass.config.location_name)
        identity = await self.hass.async_add_executor_job(generate_identity, name)
        return self.async_create_entry(
            title=name,
            data={
                CONF_DEVICE_ID: identity.device_id,
                CONF_CERTIFICATE: identity.certificate_pem,
                CONF_PRIVATE_KEY: identity.private_key_pem,
            },
            options={CONF_NAME: name},
            description_placeholders={"path": PANEL_URL_PATH},
        )

    async def async_step_import_legacy(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reuse the identity and paired devices of the older integration."""
        try:
            legacy = await self.hass.async_add_executor_job(
                _read_legacy, self.hass.config.path(LEGACY_CONFIG_DIR)
            )
        except (OSError, ValueError, sqlite3.Error) as err:
            _LOGGER.warning("Could not read the old KDE Connect configuration: %s", err)
            return self.async_abort(reason="import_failed")
        errors: dict[str, str] = {}
        if user_input is not None:
            if _legacy_running(self.hass):
                errors["base"] = "legacy_running"
            else:
                name = filter_device_name(user_input[CONF_NAME]) or DEFAULT_NAME
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_DEVICE_ID: legacy["device_id"],
                        CONF_CERTIFICATE: legacy["certificate"],
                        CONF_PRIVATE_KEY: legacy["private_key"],
                    },
                    options={CONF_NAME: name},
                    description_placeholders={"path": PANEL_URL_PATH},
                    subentries=[
                        ConfigSubentryData(
                            data=device,
                            subentry_type=SUBENTRY_TYPE_DEVICE,
                            title=device[CONF_NAME],
                            unique_id=device[CONF_DEVICE_ID],
                        )
                        for device in legacy["devices"]
                    ],
                )
        # Not the old name: devices pick up the new one when they connect.
        default = default_name(self.hass.config.location_name)
        names = ", ".join(device[CONF_NAME] for device in legacy["devices"]) or "-"
        return self.async_show_form(
            step_id="import_legacy",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_NAME): TextSelector()}),
                user_input or {CONF_NAME: default},
            ),
            errors=errors,
            description_placeholders={"devices": names},
        )


def _legacy_running(hass: HomeAssistant) -> bool:
    """Return whether the older integration is running and holds the ports."""
    return any(
        entry.state is ConfigEntryState.LOADED
        for entry in hass.config_entries.async_entries(LEGACY_DOMAIN)
    )


def _read_legacy(path: str) -> dict[str, Any]:
    """Read the certificate, key and trusted devices of bartv2/kde_connect."""
    with open(os.path.join(path, "certificate.pem"), encoding="ascii") as file:
        certificate = file.read()
    with open(os.path.join(path, "privateKey.pem"), encoding="ascii") as file:
        private_key = file.read()
    device_id = certificate_common_name(pem_to_der(certificate))
    if not is_valid_device_id(device_id):
        raise ValueError("certificate has no valid device id")
    devices = []
    database = os.path.join(path, "konnect.db")
    if os.path.isfile(database):
        with contextlib.closing(
            sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        ) as conn:
            for identifier, cert, device_name, device_type in conn.execute(
                "SELECT identifier, certificate, name, type FROM trusted_devices"
            ):
                try:
                    pem = _normalize_certificate(cert)
                except ValueError:
                    continue
                devices.append(
                    {
                        CONF_DEVICE_ID: identifier,
                        CONF_NAME: filter_device_name(device_name) or identifier,
                        CONF_DEVICE_TYPE: device_type or "unknown",
                        CONF_CERTIFICATE: pem,
                        CONF_CAPABILITIES: [],
                        CONF_MAC: None,
                        CONF_SCRIPTS: [],
                    }
                )
    return {
        "device_id": device_id,
        "certificate": certificate,
        "private_key": private_key,
        "devices": devices,
    }


def _normalize_certificate(value: Any) -> str:
    """Turn a stored certificate in PEM or DER form into PEM."""
    if isinstance(value, bytes) and b"BEGIN CERTIFICATE" in value:
        value = value.decode("ascii")
    if isinstance(value, str) and "BEGIN CERTIFICATE" in value:
        return der_to_pem(pem_to_der(value))
    if isinstance(value, str):
        value = value.encode()
    if isinstance(value, bytes):
        return der_to_pem(value)
    raise ValueError("unknown certificate format")


class KdeConnectOptionsFlow(OptionsFlowWithReload):
    """Change how Home Assistant shows up on other devices."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options."""
        if user_input is not None:
            name = filter_device_name(user_input[CONF_NAME]) or DEFAULT_NAME
            return self.async_create_entry(data={CONF_NAME: name})
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_NAME): TextSelector()}),
                {
                    CONF_NAME: self.config_entry.options.get(
                        CONF_NAME, self.config_entry.title
                    )
                },
            ),
        )


class DeviceSubentryFlow(ConfigSubentryFlow):
    """Pair a device, or change the settings of a paired one."""

    def __init__(self) -> None:
        self._stop_discovery: Any = None
        self._task: asyncio.Task[Any] | None = None
        self._device_id: str | None = None
        self._host: str | None = None
        self._pairing: PendingPairing | None = None
        self._result: tuple[DeviceInfo, bytes] | None = None
        self._error: str | None = None

    def _hub(self) -> KdeConnectHub | None:
        entry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return None
        return entry.runtime_data.hub

    @callback
    def async_remove(self) -> None:
        """Stop answering unknown devices when the flow goes away."""
        if self._stop_discovery:
            self._stop_discovery()
            self._stop_discovery = None
        if self._task and not self._task.done():
            self._task.cancel()

    def _paired_ids(self) -> set[str]:
        return {
            subentry.unique_id
            for subentry in self._get_entry().subentries.values()
            if subentry.unique_id
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Look for devices on the network."""
        if (hub := self._hub()) is None:
            return self.async_abort(reason="not_loaded")
        if self._stop_discovery is None:
            self._stop_discovery = hub.start_discovery()
        if self._task is None:
            self._task = self.hass.async_create_task(self._async_discover(hub))
        if not self._task.done():
            return self.async_show_progress(
                step_id="user", progress_action="discover", progress_task=self._task
            )
        self._task = None
        return self.async_show_progress_done(next_step_id="pick")

    async def _async_discover(self, hub: KdeConnectHub) -> None:
        hosts = {
            str(address)
            for address in await network.async_get_ipv4_broadcast_addresses(self.hass)
        }
        hub.announce(hosts)
        await asyncio.sleep(DISCOVERY_TIME / 2)
        hub.announce(hosts)
        await asyncio.sleep(DISCOVERY_TIME / 2)

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pick one of the devices that answered."""
        hub = self._hub()
        if hub is None:
            return self.async_abort(reason="not_loaded")
        paired = self._paired_ids()
        found = {
            device_id: info
            for device_id, info in hub.discovered.items()
            if device_id not in paired
        }
        if user_input is not None:
            if user_input[CONF_DEVICE] == MANUAL:
                return await self.async_step_manual()
            self._device_id = user_input[CONF_DEVICE]
            if info := found.get(self._device_id):
                self._host = info.host
            return await self.async_step_connect()

        options = [
            SelectOptionDict(
                value=device_id,
                label=f"{info.name} ({info.host})" if info.host else info.name,
            )
            for device_id, info in sorted(
                found.items(), key=lambda item: item[1].name.lower()
            )
        ]
        options.append(SelectOptionDict(value=MANUAL, label=MANUAL))
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                            translation_key="device",
                        )
                    )
                }
            ),
            description_placeholders={"count": str(len(found))},
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reach a device by its address when discovery does not find it."""
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._device_id = None
            return await self.async_step_connect()
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_HOST): TextSelector()}),
        )

    async def async_step_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Wait until the device has connected to Home Assistant."""
        hub = self._hub()
        if hub is None:
            return self.async_abort(reason="not_loaded")
        if self._task is None:
            self._task = self.hass.async_create_task(self._async_connect(hub))
        if not self._task.done():
            return self.async_show_progress(
                step_id="connect", progress_action="connect", progress_task=self._task
            )
        task, self._task = self._task, None
        if task.exception() is not None or self._device_id is None:
            return self.async_show_progress_done(next_step_id="not_found")
        if self._device_id in self._paired_ids():
            return self.async_abort(reason="already_configured")
        return self.async_show_progress_done(next_step_id="pair")

    async def _async_connect(self, hub: KdeConnectHub) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CONNECT_TIMEOUT
        while loop.time() < deadline:
            if self._device_id is None and self._host:
                for device_id, info in hub.discovered.items():
                    if info.host == self._host and hub.is_link_connected(device_id):
                        self._device_id = device_id
                        break
            if self._device_id and hub.is_link_connected(self._device_id):
                return
            if self._host:
                hub.announce([self._host])
            await asyncio.sleep(1)
        raise TimeoutError

    async def async_step_not_found(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The device did not connect."""
        return self.async_abort(reason="cannot_connect")

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Ask the device to pair and wait for the user to accept there."""
        hub = self._hub()
        if hub is None or self._device_id is None:
            return self.async_abort(reason="not_loaded")
        if self._task is None:
            try:
                self._pairing = hub.start_pairing(self._device_id)
            except PairingError:
                return self.async_abort(reason="cannot_connect")
            self._task = self.hass.async_create_task(self._async_pair(self._pairing))
        if not self._task.done():
            info = hub.discovered.get(self._device_id)
            return self.async_show_progress(
                step_id="pair",
                progress_action="pair",
                progress_task=self._task,
                description_placeholders={
                    "name": info.name if info else self._device_id,
                    "key": self._pairing.verification_key if self._pairing else "",
                },
            )
        self._task = None
        if self._result is None:
            return self.async_show_progress_done(next_step_id="pair_failed")
        return self.async_show_progress_done(next_step_id="finish")

    async def _async_pair(self, pairing: PendingPairing) -> None:
        try:
            self._result = await pairing.wait()
        except PairingError as err:
            self._error = str(err)

    async def async_step_pair_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pairing timed out or was declined."""
        reason = {"timeout": "pair_timeout", "rejected": "pair_rejected"}.get(
            self._error or "", "cannot_connect"
        )
        return self.async_abort(reason=reason)

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Store the paired device."""
        assert self._result is not None
        info, certificate = self._result
        mac = None
        if info.host:
            mac = await self.hass.async_add_executor_job(read_mac_address, info.host)
        if self._stop_discovery:
            self._stop_discovery()
            self._stop_discovery = None
        return self.async_create_entry(
            title=info.name,
            unique_id=info.device_id,
            data={
                CONF_DEVICE_ID: info.device_id,
                CONF_NAME: info.name,
                CONF_DEVICE_TYPE: info.device_type,
                CONF_CERTIFICATE: der_to_pem(certificate),
                CONF_CAPABILITIES: sorted(info.incoming_capabilities),
                CONF_MAC: mac,
                CONF_SCRIPTS: [],
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change Wake-on-LAN and the scripts the device may run."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            mac = (user_input.get(CONF_MAC) or "").strip()
            if mac:
                try:
                    mac = format_mac(
                        cv.matches_regex(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")(
                            mac
                        )
                    )
                except vol.Invalid:
                    errors[CONF_MAC] = "invalid_mac"
            if not errors:
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    data_updates={
                        CONF_MAC: mac or None,
                        CONF_SCRIPTS: user_input.get(CONF_SCRIPTS, []),
                    },
                )
        suggested: Mapping[str, Any] = user_input or {
            CONF_MAC: subentry.data.get(CONF_MAC) or "",
            CONF_SCRIPTS: subentry.data.get(CONF_SCRIPTS, []),
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(CONF_MAC): TextSelector(),
                        vol.Optional(CONF_SCRIPTS): EntitySelector(
                            EntitySelectorConfig(domain="script", multiple=True)
                        ),
                    }
                ),
                suggested,
            ),
            errors=errors,
            description_placeholders={"name": subentry.title},
        )
