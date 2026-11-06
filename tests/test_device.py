"""Unit tests for the device: packets in, packets out, against a stand-in hub."""

from __future__ import annotations

import logging
import socket
from ipaddress import IPv4Address
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.kdeforhomeassistant import device as device_module
from custom_components.kdeforhomeassistant.const import (
    CONF_CAPABILITIES,
    CONF_DEVICE_ID,
    CONF_SCRIPTS,
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.kdeforhomeassistant.device import (
    NORMAL_SINK_VOLUME,
    KdeConnectDevice,
    _normal_volume,
    _send_magic_packet,
    read_mac_address,
)
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_FINDMYPHONE_REQUEST,
    PACKET_TYPE_LOCK,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_MPRIS,
    PACKET_TYPE_MPRIS_REQUEST,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    PACKET_TYPE_SHARE_REQUEST,
    PACKET_TYPE_SYSTEMVOLUME,
    PACKET_TYPE_SYSTEMVOLUME_REQUEST,
    Packet,
    generate_identity,
)

DEVICE_ID = "abc123"


class FakeHub:
    """Just what KdeConnectDevice asks of the hub."""

    def __init__(self) -> None:
        self.connected = False
        self.info = None
        self.sent: list[Packet] = []
        self.accept = True
        self.discovered: dict = {}
        self.packet_listeners: list = []
        self.connection_listeners: list = []
        self.download = None

    def is_connected(self, device_id: str) -> bool:
        return self.connected

    def connected_info(self, device_id: str):
        return self.info

    def send(self, device_id: str, packet: Packet) -> bool:
        if not self.accept:
            return False
        self.sent.append(packet)
        return True

    def add_packet_listener(self, device_id, listener):
        self.packet_listeners.append(listener)
        return lambda: self.packet_listeners.remove(listener)

    def add_connection_listener(self, device_id, listener):
        self.connection_listeners.append(listener)
        return lambda: self.connection_listeners.remove(listener)

    async def async_download_payload(self, device_id, port, size):
        return await self.download(device_id, port, size)

    def packet(self, packet_type: str, body: dict) -> None:
        for listener in list(self.packet_listeners):
            listener(Packet(packet_type, body))

    def types(self) -> list[str]:
        return [packet.type for packet in self.sent]


@pytest.fixture
def hub() -> FakeHub:
    return FakeHub()


def _make(hass: HomeAssistant, hub: FakeHub, **data) -> KdeConnectDevice:
    identity = generate_identity("Desk")
    subentry = ConfigSubentry(
        data={
            CONF_DEVICE_ID: DEVICE_ID,
            "name": "Desk",
            "certificate": identity.certificate_pem,
            CONF_CAPABILITIES: [PACKET_TYPE_MPRIS_REQUEST],
            **data,
        },
        subentry_type=SUBENTRY_TYPE_DEVICE,
        title="Desk",
        unique_id=DEVICE_ID,
    )
    entry = MockConfigEntry(domain=DOMAIN, data={}, subentries_data=[])
    entry.add_to_hass(hass)
    return KdeConnectDevice(hass, entry, subentry, hub)


async def test_start_while_connected(hass: HomeAssistant, hub: FakeHub) -> None:
    """A device that is already connected asks for its state right away."""
    hub.connected = True
    device = _make(hass, hub)
    calls = []
    device.async_add_listener(lambda: calls.append(1))
    stop = device.async_start()
    assert PACKET_TYPE_LOCK_REQUEST in hub.types()
    # Only the stored capabilities count: mpris yes, systemvolume no.
    assert PACKET_TYPE_MPRIS_REQUEST in hub.types()
    assert PACKET_TYPE_SYSTEMVOLUME_REQUEST not in hub.types()
    assert calls
    stop()
    assert not hub.packet_listeners
    assert not hub.connection_listeners


async def test_command_packets(
    hass: HomeAssistant, hub: FakeHub, caplog: pytest.LogCaptureFixture
) -> None:
    """Command lists, requests and script runs."""
    hub.connected = True
    device = _make(hass, hub, **{CONF_SCRIPTS: ["script.hello"]})
    device.async_start()
    changed = []
    device.async_add_command_listener(lambda: changed.append(1))

    # The device asks for our commands.
    hub.sent.clear()
    hub.packet(PACKET_TYPE_RUNCOMMAND_REQUEST, {"requestCommandList": True})
    assert hub.types() == [PACKET_TYPE_RUNCOMMAND]

    # Broken lists are ignored.
    hub.packet(PACKET_TYPE_RUNCOMMAND, {"commandList": "{not json"})
    hub.packet(PACKET_TYPE_RUNCOMMAND, {"commandList": "[1, 2]"})
    assert not changed
    # A dict is accepted as is; bad items are skipped.
    hub.packet(
        PACKET_TYPE_RUNCOMMAND,
        {"commandList": {"a": {"command": "ls"}, "b": "nope"}},
    )
    assert changed
    assert device.remote_commands == {"a": {"name": "a", "command": "ls"}}

    # A script that is not shared is refused.
    calls = async_mock_service(hass, "script", "turn_on")
    hub.packet(PACKET_TYPE_RUNCOMMAND_REQUEST, {"key": "script.secret"})
    await hass.async_block_till_done()
    assert not calls
    assert "asked to run script.secret" in caplog.text


async def test_lock_packets(hass: HomeAssistant, hub: FakeHub) -> None:
    """A lock result asks again; own commands that fail to send report so."""
    hub.connected = True
    device = _make(hass, hub)
    device.async_start()
    hub.sent.clear()
    hub.packet(PACKET_TYPE_LOCK, {"lockResult": True})
    assert hub.sent[-1].type == PACKET_TYPE_LOCK_REQUEST
    assert hub.sent[-1].body == {"requestLocked": True}

    device.remote_commands = {"l": {"name": "Lock screen", "command": "x"}}
    hub.accept = False
    assert device.set_locked(True) is False
    assert device.locked is None


async def test_ring(hass: HomeAssistant, hub: FakeHub) -> None:
    """Without a Ring command the find-my-device sound is used."""
    hub.connected = True
    device = _make(hass, hub)
    assert device.ring() is True
    assert hub.sent[-1].type == PACKET_TYPE_FINDMYPHONE_REQUEST


async def test_share_ignored(hass: HomeAssistant, hub: FakeHub) -> None:
    """Shares without a file name, size or port are ignored."""
    device = _make(hass, hub)
    device.async_start()
    hub.packet(PACKET_TYPE_SHARE_REQUEST, {"filename": "a.png"})
    await hass.async_block_till_done()
    assert device.screen is None


async def test_share_download_fails(
    hass: HomeAssistant, hub: FakeHub, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed download keeps the old screen and logs why."""
    device = _make(hass, hub)
    device.async_start()

    async def fail(*args):
        raise OSError("boom")

    hub.download = fail
    packet = Packet(PACKET_TYPE_SHARE_REQUEST, {"filename": "a.png"})
    packet.payload_size = 10
    packet.payload_port = 1234
    for listener in hub.packet_listeners:
        listener(packet)
    await hass.async_block_till_done()
    assert device.screen is None
    assert "Could not receive the screen of Desk: boom" in caplog.text


async def test_mpris_and_volume(hass: HomeAssistant, hub: FakeHub) -> None:
    """Players and audio outputs, and what volume and controls act on."""
    hub.connected = True
    device = _make(hass, hub)
    device.async_start()
    calls = []
    device.async_add_listener(lambda: calls.append(1))

    # Nothing to act on yet.
    assert device.media_action("Play") is False
    assert device.media_seek(1000) is False
    assert device.set_volume(0.5) is False
    assert device.set_muted(True) is False
    assert device.volume_level is None
    assert device.muted is None

    # Packets about unknown players change nothing.
    hub.packet(PACKET_TYPE_MPRIS, {"player": "Ghost", "title": "x"})
    hub.packet(PACKET_TYPE_MPRIS, {})
    assert not calls

    hub.packet(PACKET_TYPE_MPRIS, {"playerList": ["VLC", 3]})
    hub.packet(PACKET_TYPE_MPRIS, {"player": "VLC", "volume": 40})
    assert list(device.players) == ["VLC"]
    # Without an audio output, the player volume is used.
    assert device.volume_level == 0.4
    hub.sent.clear()
    assert device.set_volume(0.7) is True
    assert hub.sent[-1].body == {"player": "VLC", "setVolume": 70}
    hub.packet(PACKET_TYPE_MPRIS, {"player": "VLC", "volume": "loud"})
    assert device.volume_level is None

    # Audio outputs.
    hub.packet(PACKET_TYPE_SYSTEMVOLUME, {"name": "ghost", "volume": 1})
    hub.packet(
        PACKET_TYPE_SYSTEMVOLUME,
        {
            "sinkList": [
                {"name": "a", "volume": 100, "enabled": True, "maxVolume": 200},
                {"name": "b", "enabled": False},
                "junk",
            ]
        },
    )
    assert set(device.sinks) == {"a", "b"}
    assert device.default_sink["name"] == "a"
    assert device.volume_level == 0.5
    # Another output becomes the default.
    hub.packet(PACKET_TYPE_SYSTEMVOLUME, {"name": "b", "enabled": True})
    assert device.sinks["a"]["enabled"] is False
    assert device.default_sink["name"] == "b"
    # It has no volume yet.
    assert device.volume_level is None
    assert device.muted is None
    hub.sent.clear()
    assert device.set_volume(1.0) is True
    assert hub.sent[-1].body == {"name": "b", "volume": NORMAL_SINK_VOLUME}


def test_normal_volume() -> None:
    """The volume that means 100%."""
    assert _normal_volume({}) == NORMAL_SINK_VOLUME
    assert _normal_volume({"maxVolume": 0}) == NORMAL_SINK_VOLUME
    assert _normal_volume({"maxVolume": 1.5}) == NORMAL_SINK_VOLUME
    assert _normal_volume({"maxVolume": 100}) == 100
    assert _normal_volume({"maxVolume": 100000}) == NORMAL_SINK_VOLUME


async def test_wake(hass: HomeAssistant, hub: FakeHub) -> None:
    """The magic packet goes to the broadcast addresses and the last host."""
    device = _make(hass, hub)
    with patch.object(device_module, "_send_magic_packet") as send:
        await device.async_wake()
    send.assert_not_called()

    device = _make(hass, hub, mac="AA-BB-CC-DD-EE-FF")
    hub.discovered[DEVICE_ID] = SimpleNamespace(host="192.168.1.20")
    with (
        patch.object(device_module, "_send_magic_packet") as send,
        patch(
            "homeassistant.components.network.async_get_ipv4_broadcast_addresses",
            return_value={IPv4Address("192.168.1.255")},
        ),
    ):
        await device.async_wake()
    packet, addresses = send.call_args.args
    assert packet == b"\xff" * 6 + bytes.fromhex("AABBCCDDEEFF") * 16
    assert addresses == {"192.168.1.255", "192.168.1.20"}


def test_send_magic_packet(caplog: pytest.LogCaptureFixture) -> None:
    """Every address gets the packet; a failing one is logged and skipped."""
    sock = MagicMock()
    sock.__enter__.return_value = sock
    sock.sendto.side_effect = [OSError("unreachable"), None]
    caplog.set_level(logging.DEBUG)
    with patch.object(device_module.socket, "socket", return_value=sock):
        _send_magic_packet(b"x", {"10.0.0.255", "10.0.1.255"})
    assert sock.sendto.call_count == 2
    sock.setsockopt.assert_called_once_with(
        socket.SOL_SOCKET, socket.SO_BROADCAST, 1
    )
    assert "Could not send Wake-on-LAN packet" in caplog.text

    # Without addresses, the global broadcast address is used.
    sock.sendto.reset_mock(side_effect=True)
    with patch.object(device_module.socket, "socket", return_value=sock):
        _send_magic_packet(b"x", set())
    sock.sendto.assert_called_once_with(b"x", ("255.255.255.255", 9))


def test_read_mac_address() -> None:
    """The ARP table gives the MAC address of a host."""
    table = (
        "IP address  HW type  Flags  HW address  Mask  Device\n"
        "10.0.0.2  0x1  0x2  00:00:00:00:00:00  *  eth0\n"
        "short line\n"
        "10.0.0.3  0x1  0x2  AA:BB:CC:DD:EE:FF  *  eth0\n"
    )
    with patch("builtins.open", mock_open(read_data=table)):
        assert read_mac_address("10.0.0.3") == "aa:bb:cc:dd:ee:ff"
        assert read_mac_address("10.0.0.2") is None
    with patch("builtins.open", mock_open(read_data="")):
        assert read_mac_address("10.0.0.3") is None
    with patch("builtins.open", side_effect=OSError):
        assert read_mac_address("10.0.0.3") is None
