"""Desktop messages join by device, app and displayed sender/chat title."""

import asyncio

from homeassistant.core import HomeAssistant

from custom_components.kdeforhomeassistant.const import DOMAIN
from custom_components.kdeforhomeassistant.notifications import (
    EVENT_NOTIFICATION,
    MAX_CHAT_MESSAGES,
    MAX_CHAT_TEXT,
    MAX_SHARED,
    DesktopNotificationChats,
)

from .fake_device import FakeDevice
from .test_init import _pair, _setup


def test_append_and_isolate_senders_apps_and_devices():
    chats = DesktopNotificationChats()
    identifier, text = chats.add("one", "Telegram Desktop", "Alice", "First")
    updated_id, text = chats.add("two", "Telegram Desktop", "Alice", "Second")
    assert updated_id == identifier
    assert text == "First\nSecond"
    assert chats.add("two", "Telegram Desktop", "Alice", "Second") == (identifier, text)
    # A new notification can legitimately repeat the same words.
    assert (
        chats.add("three", "Telegram Desktop", "Alice", "Second")[1]
        == "First\nSecond\nSecond"
    )
    assert (
        chats.add("bob", "Telegram Desktop", "Bob", "Different sender")[0] != identifier
    )
    assert chats.add("signal", "Signal", "Alice", "Different app")[0] != identifier
    other_device = DesktopNotificationChats()
    assert (
        other_device.add("one", "Telegram Desktop", "Alice", "Different device")[1]
        == "Different device"
    )
    # Native updates with the same ID add changed message text as well.
    assert chats.add("three", "Telegram Desktop", "Alice", "Third")[1].endswith(
        "\nThird"
    )


def test_partial_and_complete_dismissal():
    chats = DesktopNotificationChats()
    identifier, _ = chats.add("one", "Telegram", "Alice", "First")
    chats.add("two", "Telegram", "Alice", "Second")
    assert chats.remove("one") == (identifier, True)
    assert chats.remove("two") == (identifier, False)
    assert chats.add("three", "Telegram", "Alice", "New session")[1] == "New session"


def test_full_history_snapshot_does_not_duplicate_messages():
    chats = DesktopNotificationChats()
    identifier, _ = chats.add("one", "Telegram", "Alice", "First")
    assert chats.add("two", "Telegram", "Alice", "First\nSecond") == (
        identifier,
        "First\nSecond",
    )
    assert chats.add(
        "three", "Telegram", "Alice", "First\nSecond\nThird", complete=True
    ) == (identifier, "First\nSecond\nThird")


def test_bounded_history_and_idle_expiry():
    clock = [0.0]
    chats = DesktopNotificationChats(clock=lambda: clock[0])
    identifier, _ = chats.add("first", "Telegram", "Alice", "First")
    for index in range(40):
        _, text = chats.add(
            str(index), "Telegram", "Alice", ("message " + str(index)) * 20
        )
    assert len(text) <= MAX_CHAT_TEXT
    assert len(next(iter(chats._chats.values())).messages) <= MAX_CHAT_MESSAGES
    assert len(chats._sources) <= MAX_CHAT_MESSAGES
    clock[0] = 301.0
    new_id, text = chats.add("new", "Telegram", "Alice", "After inactivity")
    assert new_id != identifier
    assert text == "After inactivity"
    for index in range(MAX_SHARED + 1):
        chats.add("id" + str(index), "Telegram", "Sender " + str(index), "Message")
    assert len(chats._chats) == MAX_SHARED
    assert len(chats._sources) <= MAX_SHARED * MAX_CHAT_MESSAGES
    assert chats.add("generic", "Telegram Desktop", "Telegram", "Summary") == (
        "generic",
        "Summary",
    )


async def _settle(hass):
    await asyncio.sleep(0.2)
    await hass.async_block_till_done()


async def test_desktop_chat_packets_update_one_notification(hass: HomeAssistant):
    entry = await _setup(hass)
    peer = FakeDevice("Desk", protocol_version=8)
    await _pair(hass, entry, peer)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await peer.connect(entry.runtime_data.hub.tcp_port)
    await _settle(hass)
    entry.runtime_data.notifications.async_update(peer.identity.device_id, enabled=True)
    events = []
    hass.bus.async_listen(EVENT_NOTIFICATION, events.append)
    peer.notify(id="first", appName="Telegram Desktop", title="Alice", text="First")
    await _settle(hass)
    peer.notify(id="second", appName="Telegram Desktop", title="Alice", text="Second")
    await _settle(hass)
    assert [event.data["action"] for event in events] == ["added", "updated"]
    assert events[0].data["id"] == events[1].data["id"]
    assert events[1].data["source_id"] == "second"
    assert events[1].data["text"] == "First\nSecond"
    peer.notify(id="first", isCancel=True)
    await _settle(hass)
    assert len(events) == 2
    peer.notify(id="second", isCancel=True)
    await _settle(hass)
    assert events[-1].data["action"] == "removed"
    assert events[-1].data["id"] == events[0].data["id"]
    peer.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_phone_packets_are_not_accumulated(hass: HomeAssistant):
    entry = await _setup(hass)
    peer = FakeDevice("Phone", protocol_version=8)
    peer.identity.device_type = "phone"
    await _pair(hass, entry, peer)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await peer.connect(entry.runtime_data.hub.tcp_port)
    await _settle(hass)
    entry.runtime_data.notifications.async_update(peer.identity.device_id, enabled=True)
    events = []
    hass.bus.async_listen(EVENT_NOTIFICATION, events.append)
    peer.notify(id="first", appName="Telegram", title="Alice", text="First")
    peer.notify(id="second", appName="Telegram", title="Alice", text="Second")
    await _settle(hass)
    assert [(event.data["id"], event.data["text"]) for event in events] == [
        ("first", "First"),
        ("second", "Second"),
    ]
    peer.close()
    assert await hass.config_entries.async_unload(entry.entry_id)
