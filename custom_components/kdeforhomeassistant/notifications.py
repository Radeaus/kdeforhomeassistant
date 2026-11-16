"""Notifications that paired devices share with Home Assistant.

A phone or computer with notification sync on sends us its notifications.
Per device the user chooses whether to share them at all and which apps,
so for example Telegram can come from the computer but not from the phone.
These choices live in their own store: changing them must not reload the
entry, which would drop every connection.
"""

from __future__ import annotations

import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Final

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

EVENT_NOTIFICATION: Final = f"{DOMAIN}_notification"
ACTION_ADDED: Final = "added"
ACTION_UPDATED: Final = "updated"
ACTION_REMOVED: Final = "removed"

STORAGE_KEY: Final = f"{DOMAIN}.notifications"
STORAGE_VERSION: Final = 1
SAVE_DELAY: Final = 10

ICON_URL: Final = f"/api/{DOMAIN}/notification_icon"
MAX_ICONS: Final = 64
MAX_ICON_SIZE: Final = 1024 * 1024
# Notifications we remember, per device, to report when they go away.
MAX_SHARED: Final = 200
MAX_APPS: Final = 500
MAX_APP_NAME: Final = 100


@dataclass
class NotificationSettings:
    """What one device shares."""

    enabled: bool = False
    # Whether apps we have not seen before are shared.
    share_new: bool = True
    # Silent notifications include the ones a phone resends when it connects.
    include_silent: bool = False
    apps: dict[str, bool] = field(default_factory=dict)

    def shares(self, app: str, silent: bool) -> bool:
        """Return whether a notification of this app is passed on."""
        if not self.enabled or (silent and not self.include_silent):
            return False
        return self.apps.get(app, self.share_new)

    def as_dict(self) -> dict[str, Any]:
        """Return the settings as stored and as the panel sees them."""
        return {
            "enabled": self.enabled,
            "share_new": self.share_new,
            "include_silent": self.include_silent,
            "apps": dict(self.apps),
        }

    @classmethod
    def from_dict(cls, data: Any) -> NotificationSettings:
        """Read stored settings, ignoring anything malformed."""
        if not isinstance(data, dict):
            return cls()
        apps = data.get("apps")
        return cls(
            enabled=data.get("enabled") is True,
            share_new=data.get("share_new") is not False,
            include_silent=data.get("include_silent") is True,
            apps={
                name: value
                for name, value in (apps.items() if isinstance(apps, dict) else ())
                if isinstance(name, str) and isinstance(value, bool)
            },
        )


class NotificationStore:
    """The notification settings of every device, by KDE Connect device id."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._devices: dict[str, NotificationSettings] = {}

    async def async_load(self) -> None:
        """Read the stored settings."""
        data = await self._store.async_load() or {}
        devices = data.get("devices")
        if isinstance(devices, dict):
            self._devices = {
                device_id: NotificationSettings.from_dict(value)
                for device_id, value in devices.items()
            }

    def get(self, device_id: str) -> NotificationSettings:
        """Return the settings of a device."""
        return self._devices.setdefault(device_id, NotificationSettings())

    @callback
    def async_seen(self, device_id: str, app: str) -> bool:
        """Remember an app the device sent a notification for.

        Returns whether the app is new, so the panel can show it.
        """
        settings = self.get(device_id)
        if app in settings.apps or len(settings.apps) >= MAX_APPS:
            return False
        settings.apps[app] = settings.share_new
        self._schedule_save()
        return True

    @callback
    def async_update(
        self,
        device_id: str,
        *,
        enabled: bool | None = None,
        share_new: bool | None = None,
        include_silent: bool | None = None,
        apps: dict[str, bool] | None = None,
        forget: list[str] | None = None,
    ) -> NotificationSettings:
        """Change what a device shares."""
        settings = self.get(device_id)
        if enabled is not None:
            settings.enabled = enabled
        if share_new is not None:
            settings.share_new = share_new
        if include_silent is not None:
            settings.include_silent = include_silent
        for app, shared in (apps or {}).items():
            if app in settings.apps or len(settings.apps) < MAX_APPS:
                settings.apps[app] = shared
        for app in forget or ():
            settings.apps.pop(app, None)
        self._schedule_save()
        return settings

    @callback
    def async_remove(self, device_id: str) -> None:
        """Forget a device that is no longer paired."""
        if self._devices.pop(device_id, None) is not None:
            self._schedule_save()

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._data, SAVE_DELAY)

    def _data(self) -> dict[str, Any]:
        return {
            "devices": {
                device_id: settings.as_dict()
                for device_id, settings in self._devices.items()
            }
        }


class NotificationIcons:
    """The icons of recent notifications, served without login.

    Small screens such as an ESPHome display fetch them by URL; the random
    token in the URL is what keeps others out.
    """

    def __init__(self) -> None:
        self._icons: OrderedDict[str, bytes] = OrderedDict()

    def add(self, data: bytes) -> str:
        """Keep an icon and return its token."""
        token = secrets.token_urlsafe(24)
        self._icons[token] = data
        while len(self._icons) > MAX_ICONS:
            self._icons.popitem(last=False)
        return token

    def get(self, token: str) -> bytes | None:
        """Return an icon by its token."""
        return self._icons.get(token)


class NotificationIconView(HomeAssistantView):
    """Serve notification icons."""

    url = ICON_URL + "/{token}.png"
    name = f"api:{DOMAIN}:notification_icon"
    requires_auth = False

    def __init__(self, icons: NotificationIcons) -> None:
        self._icons = icons

    async def get(self, request: web.Request, token: str) -> web.Response:
        """Return the icon, or 404."""
        if (data := self._icons.get(token)) is None:
            return web.Response(status=404)
        return web.Response(
            body=data,
            content_type="image/png",
            headers={"Cache-Control": "private, max-age=3600"},
        )


@callback
def async_get_icons(hass: HomeAssistant) -> NotificationIcons:
    """Return the icon cache, serving it the first time."""
    key = f"{DOMAIN}_notification_icons"
    if (icons := hass.data.get(key)) is None:
        icons = hass.data[key] = NotificationIcons()
        hass.http.register_view(NotificationIconView(icons))
    return icons


def clean_app_name(value: Any) -> str:
    """Return the app name of a notification, never empty."""
    if not isinstance(value, str) or not (name := value.strip()):
        return "Unknown"
    return name[:MAX_APP_NAME]


def notification_content(body: dict[str, Any]) -> tuple[str, str]:
    """Render KDE Connect conversation history like the desktop receiver."""
    title = body.get("title") if isinstance(body.get("title"), str) else ""
    text = body.get("text") if isinstance(body.get("text"), str) else ""
    conversation = body.get("conversation")
    if not isinstance(conversation, list):
        return title, text
    messages = [
        message
        for message in conversation[-100:]
        if isinstance(message, dict)
        and isinstance(message.get("content"), str)
        and message["content"]
    ]
    if not messages:
        return title, text
    group = body.get("groupName")
    sender = messages[0].get("sender")
    title = (
        group
        if isinstance(group, str) and group
        else sender
        if isinstance(sender, str) and sender
        else title
    )
    previous_sender = title
    lines: list[str] = []
    for message in messages:
        sender = message.get("sender")
        if isinstance(sender, str) and sender and sender != previous_sender:
            lines.append(f"{sender}:")
            previous_sender = sender
        lines.append(message["content"])
    return title, "\n".join(lines)
