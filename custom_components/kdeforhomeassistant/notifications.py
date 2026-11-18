"""Notifications that paired devices share with Home Assistant.

A phone or computer with notification sync on sends us its notifications.
Per device the user chooses whether to share them at all and which apps,
so for example Telegram can come from the computer but not from the phone.
These choices live in their own store: changing them must not reload the
entry, which would drop every connection.
"""

from __future__ import annotations

import secrets
import time
from collections import OrderedDict
from collections.abc import Callable
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


# Desktop notifications generally provide a sender title, not conversation history.
CHAT_APPS = frozenset(
    {
        "telegram",
        "telegramdesktop",
        "signal",
        "signaldesktop",
        "discord",
        "whatsapp",
        "whatsappdesktop",
        "element",
        "slack",
        "teams",
        "microsoftteams",
    }
)
MAX_CHAT_MESSAGES = 20
MAX_CHAT_TEXT = 768
CHAT_IDLE_SECONDS = 300


def is_chat_notification(app: str, body: dict[str, Any]) -> bool:
    """Recognize messaging apps or an explicit freedesktop instant-message category."""
    category = body.get("category")
    return app.casefold().replace(" ", "").replace("-", "") in CHAT_APPS or (
        isinstance(category, str) and category.startswith("im.")
    )


@dataclass
class _DesktopChat:
    notification_id: str
    touched: float
    messages: list[str] = field(default_factory=list)
    sources: OrderedDict[str, str] = field(default_factory=OrderedDict)


class DesktopNotificationChats:
    """Bounded, in-memory chat history; one instance belongs to one device."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._chats: OrderedDict[tuple[str, str], _DesktopChat] = OrderedDict()
        self._sources: dict[str, tuple[str, str]] = {}

    def _forget(self, key: tuple[str, str]) -> None:
        chat = self._chats.pop(key)
        for source in chat.sources:
            self._sources.pop(source, None)

    def add(
        self, source: str, app: str, title: str, text: str, *, complete: bool = False
    ) -> tuple[str, str]:
        """Append a new message, or replace a sender-provided conversation snapshot."""
        if (
            not title.strip()
            or len(title) > 256
            or not text
            or len(source) > 1024
            or title.strip().casefold()
            in (app.casefold(), app.casefold().removesuffix(" desktop"))
        ):
            return source, text
        now = self._clock()
        for expired in [
            key
            for key, chat in self._chats.items()
            if now - chat.touched >= CHAT_IDLE_SECONDS
        ]:
            self._forget(expired)
        key = (app, title.strip())
        if (previous := self._sources.get(source)) is not None and previous != key:
            self.remove(source)
        chat = self._chats.get(key)
        if chat is None:
            chat = self._chats[key] = _DesktopChat(
                "chat:" + secrets.token_urlsafe(18), now
            )
        self._chats.move_to_end(key)
        chat.touched = now
        text = text[-MAX_CHAT_TEXT:]
        current = "\n".join(chat.messages)
        if complete or (current and text.startswith(current + "\n")):
            chat.messages = [text]
        elif chat.sources.get(source) != text:
            chat.messages.append(text)
        chat.messages = chat.messages[-MAX_CHAT_MESSAGES:]
        chat.sources[source] = text
        chat.sources.move_to_end(source)
        self._sources[source] = key
        while len(chat.sources) > MAX_CHAT_MESSAGES:
            old, _ = chat.sources.popitem(last=False)
            self._sources.pop(old, None)
        while len(self._chats) > MAX_SHARED:
            self._forget(next(iter(self._chats)))
        return chat.notification_id, "\n".join(chat.messages)[-MAX_CHAT_TEXT:]

    def remove(self, source: str) -> tuple[str, bool]:
        """Dismiss only when every tracked notification in this chat is removed."""
        key = self._sources.pop(source, None)
        if key is None:
            return source, False
        chat = self._chats[key]
        chat.sources.pop(source, None)
        if chat.sources:
            return chat.notification_id, True
        self._forget(key)
        return chat.notification_id, False
