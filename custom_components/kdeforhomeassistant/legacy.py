"""The older KDE Connect integration (bartv2/kde_connect).

It uses the same network ports. After its pairings are taken over it also
uses the same identity, so the two must never run side by side.
"""

from __future__ import annotations

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryDisabler,
    ConfigEntryState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, LEGACY_DOMAIN

LEGACY_ISSUE_ID = "legacy_installed"


@callback
def active_legacy_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Return the entries of the older integration that are not disabled."""
    return [
        entry
        for entry in hass.config_entries.async_entries(LEGACY_DOMAIN)
        if entry.disabled_by is None
    ]


@callback
def legacy_name(hass: HomeAssistant) -> str:
    """Return the name the older integration is set up under."""
    entries = active_legacy_entries(hass)
    return entries[0].title if entries else "KDE Connect"


async def async_disable_legacy(hass: HomeAssistant) -> None:
    """Disable the older integration; it can be turned on again later."""
    for entry in active_legacy_entries(hass):
        await hass.config_entries.async_set_disabled_by(
            entry.entry_id, ConfigEntryDisabler.USER
        )
    _retry_own_entry(hass)


async def async_remove_legacy(hass: HomeAssistant) -> None:
    """Remove the older integration."""
    for entry in active_legacy_entries(hass):
        await hass.config_entries.async_remove(entry.entry_id)
    _retry_own_entry(hass)


@callback
def async_check_legacy_issue(hass: HomeAssistant) -> None:
    """Show a repair while the older integration can still start."""
    if active_legacy_entries(hass):
        ir.async_create_issue(
            hass,
            DOMAIN,
            LEGACY_ISSUE_ID,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=LEGACY_ISSUE_ID,
            translation_placeholders={"name": legacy_name(hass)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, LEGACY_ISSUE_ID)


@callback
def _retry_own_entry(hass: HomeAssistant) -> None:
    """Start right away when we were waiting for the ports to become free."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.SETUP_RETRY:
            hass.config_entries.async_schedule_reload(entry.entry_id)
    ir.async_delete_issue(hass, DOMAIN, LEGACY_ISSUE_ID)
