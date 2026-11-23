"""Tests for notifications that devices share with Home Assistant."""

from __future__ import annotations

import asyncio

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.kdeforhomeassistant.const import DOMAIN
from custom_components.kdeforhomeassistant.notifications import (
    EVENT_NOTIFICATION,
    MAX_APPS,
    MAX_ICONS,
    NotificationIcons,
    NotificationSettings,
    NotificationStore,
    clean_app_name,
    notification_content,
)

from .fake_device import FakeDevice
from .test_init import _pair, _setup

PNG = b"\x89PNG\r\n\x1a\n" + b"icon" * 100


async def _connected(hass: HomeAssistant, entry, name: str) -> FakeDevice:
    device = FakeDevice(name, protocol_version=8)
    await _pair(hass, entry, device)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await device.connect(entry.runtime_data.hub.tcp_port)
    await device.wait_for("kdeconnect.runcommand.request", requestCommandList=True)
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()
    return device


def _subentry_id(entry, name: str) -> str:
    return next(
        subentry_id
        for subentry_id, subentry in entry.subentries.items()
        if subentry.title == name
    )


async def _settle(hass: HomeAssistant) -> None:
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()


async def test_choose_apps_per_device(hass: HomeAssistant, hass_ws_client) -> None:
    """The same app is shared from one device and not from the other."""
    entry = await _setup(hass)
    desk = await _connected(hass, entry, "Desk")
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    phone = await _connected(hass, entry, "Phone")
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    # Adding the phone reloaded the entry, which dropped the desk.
    desk.close()
    await desk.connect(entry.runtime_data.hub.tcp_port)
    await _settle(hass)
    events = async_capture_events(hass, EVENT_NOTIFICATION)
    ws = await hass_ws_client(hass)

    # Off until the user turns it on, but the app is listed to choose.
    phone.notify(id="1", appName="Telegram", title="Ann", text="Hi")
    await _settle(hass)
    assert events == []
    store = entry.runtime_data.notifications
    phone_id = entry.subentries[_subentry_id(entry, "Phone")].data["device_id"]
    assert store.get(phone_id).apps == {"Telegram": True}

    for name, apps in (("Desk", None), ("Phone", {"Telegram": False})):
        payload = {
            "type": f"{DOMAIN}/update_notifications",
            "subentry_id": _subentry_id(entry, name),
            "enabled": True,
        }
        if apps is not None:
            payload["apps"] = apps
        await ws.send_json_auto_id(payload)
        assert (await ws.receive_json())["success"]

    phone.notify(id="2", appName="Telegram", title="Ann", text="Again")
    phone.notify(id="3", appName="Signal", title="Bob", text="Yo")
    desk.notify(id="9", appName="Telegram", title="Ann", text="Again")
    await _settle(hass)
    assert [(e.data["device_name"], e.data["app"]) for e in events] == [
        ("Phone", "Signal"),
        ("Desk", "Telegram"),
    ]
    event = events[1].data
    desk_notification_id = event["id"]
    assert event["action"] == "added"
    assert event["title"] == "Ann"
    assert event["text"] == "Again"
    assert event["icon_url"] is None
    registry_device = dr.async_get(hass).async_get_device(
        identifiers={
            (DOMAIN, entry.subentries[_subentry_id(entry, "Desk")].data["device_id"])
        }
    )
    assert event["device_id"] == registry_device.id

    state = hass.states.get("event.desk_notification")
    assert state.attributes["event_type"] == "added"
    assert state.attributes["app"] == "Telegram"
    assert state.attributes["text"] == "Again"

    # Updates, silent ones, removals.
    events.clear()
    desk.notify(id="9", appName="Telegram", title="Ann", text="Edited")
    desk.notify(id="10", appName="Telegram", title="Old", text="x", silent=True)
    desk.notify(id="9", isCancel=True)
    desk.notify(id="unknown", isCancel=True)
    desk.notify(appName="No id")
    await _settle(hass)
    assert [(e.data["action"], e.data["id"]) for e in events] == [
        ("updated", desk_notification_id),
        ("removed", desk_notification_id),
    ]
    assert (
        hass.states.get("event.desk_notification").attributes["event_type"] == "removed"
    )

    # Silent ones on request; forgetting an app lists it again on its next one.
    await ws.send_json_auto_id(
        {
            "type": f"{DOMAIN}/update_notifications",
            "subentry_id": _subentry_id(entry, "Desk"),
            "include_silent": True,
            "share_new": False,
            "forget": ["Telegram"],
        }
    )
    assert (await ws.receive_json())["success"]
    events.clear()
    desk.notify(id="11", appName="Telegram", title="Old", silent=True)
    desk.notify(id="12", appName="", title="Who")
    await _settle(hass)
    assert events == []
    desk_settings = store.get(
        entry.subentries[_subentry_id(entry, "Desk")].data["device_id"]
    )
    assert desk_settings.apps == {"Telegram": False, "Unknown": False}

    # The panel sees the settings.
    await ws.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    await ws.receive_json()
    state = (await ws.receive_json())["event"]
    by_name = {d["name"]: d for d in state["devices"]}
    assert by_name["Phone"]["notifications"]["apps"] == {
        "Telegram": False,
        "Signal": True,
    }
    assert by_name["Desk"]["entities"]["notification"] == "event.desk_notification"

    # Removing a device forgets its settings.
    await ws.send_json_auto_id(
        {"type": f"{DOMAIN}/remove_device", "subentry_id": _subentry_id(entry, "Phone")}
    )
    while (reply := await ws.receive_json())["type"] != "result":
        pass
    assert reply["success"]
    await hass.async_block_till_done()
    assert store.get(phone_id).apps == {}

    desk.close()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_notification_icon(hass: HomeAssistant, hass_client_no_auth) -> None:
    """The icon is fetched from the device and served without login."""
    entry = await _setup(hass)
    device = await _connected(hass, entry, "Phone")
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry = entry.subentries[_subentry_id(entry, "Phone")]
    entry.runtime_data.notifications.async_update(
        subentry.data["device_id"], enabled=True
    )
    events = async_capture_events(hass, EVENT_NOTIFICATION)

    await device.notify_with_icon(PNG, id="1", appName="Mail", title="New mail")
    await _settle(hass)
    assert len(events) == 1
    url = events[0].data["icon_url"]
    assert "/api/kdeforhomeassistant/notification_icon/" in url
    client = await hass_client_no_auth()
    path = url[url.index("/api/") :]
    resp = await client.get(path)
    assert resp.status == 200
    assert await resp.read() == PNG
    assert resp.content_type == "image/png"
    resp = await client.get("/api/kdeforhomeassistant/notification_icon/nope.png")
    assert resp.status == 404

    # Updates without another payload retain the existing icon.
    device.notify(id="1", appName="Mail", title="Updated mail")
    await _settle(hass)
    assert events[-1].data["icon_url"] == url
    assert events[-1].data["action"] == "updated"
    # A different app may reuse a desktop notification id, without an image.
    device.notify(id="1", appName="Telegram", title="Different app")
    await _settle(hass)
    assert events[-1].data["icon_url"] is None
    assert events[-1].data["action"] == "added"
    device.notify(id="1", isCancel=True)
    await _settle(hass)
    device.notify(id="1", appName="Mail", title="Reused id")
    await _settle(hass)
    assert events[-1].data["icon_url"] is None

    # A failed download still passes on the notification, without icon.
    hub = entry.runtime_data.hub

    async def broken(*_args, **_kwargs):
        raise OSError("gone")

    hub.async_download_payload = broken
    task = asyncio.create_task(
        device.notify_with_icon(PNG, id="2", appName="Mail", title="Again")
    )
    await _settle(hass)
    task.cancel()
    assert events[-1].data["icon_url"] is None
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_store_persists(hass: HomeAssistant, hass_storage) -> None:
    """Settings survive a restart and malformed data is ignored."""
    hass_storage["kdeforhomeassistant.notifications"] = {
        "version": 1,
        "key": "kdeforhomeassistant.notifications",
        "data": {
            "devices": {
                "a": {"enabled": True, "apps": {"Telegram": False, "bad": 1, 2: True}},
                "b": "junk",
            }
        },
    }
    store = NotificationStore(hass)
    await store.async_load()
    assert store.get("a") == NotificationSettings(
        enabled=True, apps={"Telegram": False}
    )
    assert store.get("b") == NotificationSettings()
    assert store.async_seen("a", "Signal") is True
    assert store.async_seen("a", "Signal") is False
    store.async_remove("b")
    store.async_remove("missing")

    # The number of apps is bounded.
    for index in range(MAX_APPS):
        store.async_seen("c", f"app{index}")
    assert store.async_seen("c", "one more") is False
    store.async_update("c", apps={"one more": True, "app0": False})
    assert "one more" not in store.get("c").apps
    assert store.get("c").apps["app0"] is False

    hass_storage.pop("kdeforhomeassistant.notifications")
    await hass.async_stop(force=True)
    saved = hass_storage["kdeforhomeassistant.notifications"]["data"]["devices"]
    assert saved["a"]["apps"] == {"Telegram": False, "Signal": True}
    assert "b" not in saved


async def test_empty_store(hass: HomeAssistant) -> None:
    """Without stored data every device starts with sharing off."""
    store = NotificationStore(hass)
    await store.async_load()
    settings = store.get("x")
    assert not settings.shares("Telegram", silent=False)
    settings.enabled = True
    assert settings.shares("Telegram", silent=False)
    assert not settings.shares("Telegram", silent=True)


def test_icons_and_names() -> None:
    """Old icons are dropped; app names are cleaned."""
    icons = NotificationIcons()
    first = icons.add(b"first")
    for _ in range(MAX_ICONS):
        icons.add(b"more")
    assert icons.get(first) is None
    assert clean_app_name(None) == "Unknown"
    assert clean_app_name("  ") == "Unknown"
    assert clean_app_name(" Telegram ") == "Telegram"
    assert len(clean_app_name("x" * 500)) == 100
    assert NotificationSettings.from_dict([]) == NotificationSettings()


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"title": "Mail", "text": "Hi"}, ("Mail", "Hi")),
        ({"title": "Fallback", "text": "Hi", "conversation": []}, ("Fallback", "Hi")),
        (
            {"title": "Fallback", "text": "Hi", "conversation": [None, {"content": 5}]},
            ("Fallback", "Hi"),
        ),
        (
            {
                "conversation": [
                    {"sender": "Ann", "content": "First"},
                    {"sender": "Ann", "content": "Second"},
                ]
            },
            ("Ann", "First\nSecond"),
        ),
        (
            {
                "groupName": "Friends",
                "conversation": [
                    {"sender": "Ann", "content": "First"},
                    {"sender": "Ann", "content": "Second"},
                    {"sender": "Bob", "content": "Third"},
                ],
            },
            ("Friends", "Ann:\nFirst\nSecond\nBob:\nThird"),
        ),
    ],
)
def test_notification_conversation_content(body, expected):
    """Conversation messages remain together, with sender changes for groups."""
    assert notification_content(body) == expected


async def test_conversation_packet_updates(hass: HomeAssistant) -> None:
    """Successive packets carry the complete conversation to display consumers."""
    entry = await _setup(hass)
    device = await _connected(hass, entry, "Phone")
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry = entry.subentries[_subentry_id(entry, "Phone")]
    entry.runtime_data.notifications.async_update(
        subentry.data["device_id"], enabled=True
    )
    events = async_capture_events(hass, EVENT_NOTIFICATION)
    messages = [{"sender": "Ann", "content": "First"}]
    device.notify(
        id="chat-1",
        appName="Telegram",
        title="Telegram",
        text="First",
        conversation=messages,
    )
    await _settle(hass)
    messages.append({"sender": "Ann", "content": "Second"})
    device.notify(
        id="chat-1",
        appName="Telegram",
        title="Telegram",
        text="Second",
        conversation=messages,
    )
    await _settle(hass)
    assert events[-1].data["action"] == "updated"
    assert events[-1].data["title"] == "Ann"
    assert events[-1].data["text"] == "First\nSecond"
    device.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("followup", ["updated", "removed", "different_app"])
async def test_late_icon_cannot_restore_an_old_notification(
    hass: HomeAssistant, followup
) -> None:
    """An icon finishing later must not replace newer text or undo dismissal."""
    from custom_components.kdeforhomeassistant.kdeconnect.protocol import Packet

    entry = await _setup(hass)
    peer = await _connected(hass, entry, "Phone")
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    subentry_id = _subentry_id(entry, "Phone")
    device = entry.runtime_data.devices[subentry_id]
    entry.runtime_data.notifications.async_update(device.device_id, enabled=True)
    ready = asyncio.Event()
    release = asyncio.Event()

    async def delayed(*args, **kwargs):
        ready.set()
        await release.wait()
        return PNG

    entry.runtime_data.hub.async_download_payload = delayed
    events = async_capture_events(hass, EVENT_NOTIFICATION)
    device._handle_notification(
        Packet(
            "kdeconnect.notification",
            {"id": "1", "appName": "Mail", "text": "Old"},
            payload_size=len(PNG),
            payload_port=1739,
        )
    )
    await asyncio.wait_for(ready.wait(), 2)
    body = {"id": "1", "appName": "Mail", "text": "New"}
    if followup == "removed":
        body["isCancel"] = True
    elif followup == "different_app":
        body["appName"] = "Telegram"
    device._handle_notification(Packet("kdeconnect.notification", body))
    await hass.async_block_till_done(wait_background_tasks=False)
    release.set()
    await _settle(hass)
    assert len(events) == 1
    if followup == "removed":
        assert events[0].data["action"] == "removed"
    else:
        assert events[0].data["text"] == "New"
        assert events[0].data["icon_url"] is None
    peer.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_timed_out_icon_still_delivers_text(hass: HomeAssistant) -> None:
    """A slow payload must not drop the notification entirely."""
    from custom_components.kdeforhomeassistant.kdeconnect.protocol import Packet

    entry = await _setup(hass)
    peer = await _connected(hass, entry, "Phone")
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    device = entry.runtime_data.devices[_subentry_id(entry, "Phone")]
    entry.runtime_data.notifications.async_update(device.device_id, enabled=True)
    events = async_capture_events(hass, EVENT_NOTIFICATION)

    async def timeout(*args, **kwargs):
        raise TimeoutError

    entry.runtime_data.hub.async_download_payload = timeout
    device._handle_notification(
        Packet(
            "kdeconnect.notification",
            {"id": "1", "appName": "Mail", "text": "Still delivered"},
            payload_size=len(PNG),
            payload_port=1739,
        )
    )
    await _settle(hass)
    assert events[-1].data["text"] == "Still delivered"
    assert events[-1].data["icon_url"] is None
    peer.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_choices_survive_reload_and_go_with_the_entry(
    hass: HomeAssistant, hass_storage
) -> None:
    """A reload right after a change keeps it; removing the entry deletes the file."""
    entry = await _setup(hass)
    device = await _connected(hass, entry, "Phone")
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    device_id = entry.subentries[_subentry_id(entry, "Phone")].data["device_id"]
    entry.runtime_data.notifications.async_update(
        device_id, enabled=True, apps={"Telegram": False}
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    settings = entry.runtime_data.notifications.get(device_id)
    assert settings.enabled is True
    assert settings.apps == {"Telegram": False}
    assert "kdeforhomeassistant.notifications" in hass_storage

    device.close()
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "kdeforhomeassistant.notifications" not in hass_storage
