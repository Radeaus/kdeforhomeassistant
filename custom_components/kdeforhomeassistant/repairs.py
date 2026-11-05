"""Repairs that the user can fix from Settings > Repairs."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .legacy import (
    LEGACY_ISSUE_ID,
    async_disable_legacy,
    async_remove_legacy,
    legacy_name,
)


class LegacyRepairFlow(RepairsFlow):
    """Disable or remove the older KDE Connect integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user choose."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["legacy_disable", "legacy_remove"],
            description_placeholders={"name": legacy_name(self.hass)},
        )

    async def async_step_legacy_disable(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Disable the older integration."""
        await async_disable_legacy(self.hass)
        return self.async_create_entry(data={})

    async def async_step_legacy_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove the older integration."""
        await async_remove_legacy(self.hass)
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Return the flow that fixes the issue."""
    if issue_id != LEGACY_ISSUE_ID:
        raise ValueError(f"Unknown issue {issue_id}")
    return LegacyRepairFlow()
