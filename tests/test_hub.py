"""Tests for the KDE Connect hub without Home Assistant around it."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import ssl
import tempfile
import time
from collections.abc import AsyncGenerator, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.kdeforhomeassistant.kdeconnect import hub as hub_module
from custom_components.kdeforhomeassistant.kdeconnect.hub import (
    MAX_IDENTITY_PACKET_SIZE,
    KdeConnectHub,
    Link,
    PairingError,
    _Discovery,
)
from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_IDENTITY,
    PACKET_TYPE_PAIR,
    PACKET_TYPE_PING,
    DeviceInfo,
    Identity,
    Packet,
    generate_identity,
)

from .fake_device import CAPABILITIES, FakeDevice

LOGGER = "custom_components.kdeforhomeassistant.kdeconnect.hub"

_IDENTITIES: list[Identity] = []


def _identity(index: int) -> Identity:
    """Return a cached identity; generating RSA keys is slow."""
    while len(_IDENTITIES) <= index:
        _IDENTITIES.append(generate_identity(f"Identity {len(_IDENTITIES)}"))
    return _IDENTITIES[index]


def _server_context(identity: Identity) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "w") as file:
        file.write(identity.private_key_pem + identity.certificate_pem)
    context.load_cert_chain(path)
    os.unlink(path)
    return context


async def _until(condition: Callable[[], bool], timeout: float = 5) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def _new_hub(udp_port: int = 0) -> KdeConnectHub:
    return KdeConnectHub(
        _identity(0),
        incoming_capabilities=CAPABILITIES,
        outgoing_capabilities=CAPABILITIES,
        udp_port=udp_port,
    )


class Peers:
    """Keeps track of what a test opened, so it can all be closed."""

    def __init__(self) -> None:
        self.devices: list[FakeDevice] = []
        self.writers: list[asyncio.StreamWriter] = []

    def device(self, protocol_version: int = 7, cls=FakeDevice) -> FakeDevice:
        device = cls("Fake PC", protocol_version=protocol_version)
        self.devices.append(device)
        return device

    async def raw(self, port: int):
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        self.writers.append(writer)
        return reader, writer


@pytest.fixture
async def hub(caplog) -> AsyncGenerator[KdeConnectHub]:
    """A started hub on a free port."""
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    hub = _new_hub()
    await hub.start()
    yield hub
    await hub.stop()
    await asyncio.sleep(0.05)


@pytest.fixture
async def peers() -> AsyncGenerator[Peers]:
    """Fake devices and raw connections, closed at the end."""
    peers = Peers()
    yield peers
    for device in peers.devices:
        device.close()
    for writer in peers.writers:
        writer.close()
    await asyncio.sleep(0.1)


async def _connect(hub: KdeConnectHub, device: FakeDevice) -> None:
    await device.connect(hub.tcp_port)
    await _until(lambda: hub.is_link_connected(device.identity.device_id))


async def _connect_trusted(hub: KdeConnectHub, device: FakeDevice) -> None:
    hub.set_trusted({device.identity.device_id: device.identity.certificate_der})
    await _connect(hub, device)
    assert hub.is_connected(device.identity.device_id)


def _identity_line(device_id: str, **extra) -> bytes:
    return Packet(
        PACKET_TYPE_IDENTITY,
        {"deviceId": device_id, "deviceName": "Raw", "protocolVersion": 7, **extra},
    ).serialize()


# Plain text handshake


async def test_malformed_handshake(hub: KdeConnectHub, peers: Peers, caplog) -> None:
    """Blank lines are skipped; bad JSON, other targets and huge lines drop the link."""
    reader, writer = await peers.raw(hub.tcp_port)
    writer.write(b"\n{nope\n")
    assert await reader.read() == b""
    assert "Packet is not valid JSON" in caplog.text

    reader, writer = await peers.raw(hub.tcp_port)
    writer.write(_identity_line(hub.identity.device_id))
    assert await reader.read() == b""

    reader, writer = await peers.raw(hub.tcp_port)
    writer.write(_identity_line("b" * 32, targetDeviceId="c" * 32))
    assert await reader.read() == b""
    assert caplog.text.count("Connection is not meant for us") == 2

    reader, writer = await peers.raw(hub.tcp_port)
    writer.write(b"x" * (MAX_IDENTITY_PACKET_SIZE + 1))
    assert await reader.read() == b""
    assert "packet too large" in caplog.text


async def test_handshake_timeout(hub: KdeConnectHub, peers: Peers, caplog) -> None:
    """A device that never identifies itself is dropped."""
    with patch.object(hub_module, "HANDSHAKE_TIMEOUT", 0.05):
        reader, _ = await peers.raw(hub.tcp_port)
        assert await reader.read() == b""
    assert "handshake timed out" in caplog.text


async def test_closed_before_identity(hub: KdeConnectHub, peers: Peers) -> None:
    """Closing before the handshake cancels its timer (checked by cleanup)."""
    _, writer = await peers.raw(hub.tcp_port)
    writer.close()
    await asyncio.sleep(0.1)
    assert not hub._links


async def test_tls_handshake_fails(hub: KdeConnectHub, peers: Peers, caplog) -> None:
    """A device that answers our TLS hello with nonsense is dropped."""
    reader, writer = await peers.raw(hub.tcp_port)
    writer.write(_identity_line("b" * 32))
    await reader.read(1)  # The start of our TLS client hello.
    writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n" * 4)
    await _until(lambda: "TLS handshake failed" in caplog.text)


async def test_tls_returns_no_transport(
    hub: KdeConnectHub, peers: Peers, caplog
) -> None:
    """If start_tls gives no transport, the link is dropped."""
    loop = asyncio.get_running_loop()
    reader, writer = await peers.raw(hub.tcp_port)
    with patch.object(loop, "start_tls", AsyncMock(return_value=None)):
        writer.write(_identity_line("b" * 32))
        assert await reader.read() == b""
    assert "connection closed during TLS handshake" in caplog.text


class _WrongCertificate(FakeDevice):
    """Claims one device id but shows the certificate of another."""

    def _server_context(self) -> ssl.SSLContext:
        return _server_context(_identity(1))


async def test_certificate_of_other_device(
    hub: KdeConnectHub, peers: Peers, caplog
) -> None:
    """The certificate common name must match the announced device id."""
    device = peers.device(cls=_WrongCertificate)
    await device.connect(hub.tcp_port)
    await _until(lambda: "certificate does not belong" in caplog.text)
    assert not hub.is_link_connected(device.identity.device_id)


class _ChangingId(FakeDevice):
    """Sends another device id after encryption (protocol 8)."""

    def _identity_packet(self) -> Packet:
        packet = super()._identity_packet()
        if getattr(self, "_sent_plain", False):
            packet.body["deviceId"] = "d" * 32
        self._sent_plain = True
        return packet


async def test_protocol_8_id_changes(hub: KdeConnectHub, peers: Peers, caplog) -> None:
    """The encrypted identity must have the same device id."""
    device = peers.device(protocol_version=8, cls=_ChangingId)
    await device.connect(hub.tcp_port)
    await _until(lambda: "Device id changed after encryption" in caplog.text)
    assert not hub._links


async def test_protocol_8_and_7(hub: KdeConnectHub, peers: Peers) -> None:
    """Protocol 8 exchanges identities again over TLS; protocol 7 does not."""
    new = peers.device(protocol_version=8)
    await _connect(hub, new)
    identity = await new.wait_for(PACKET_TYPE_IDENTITY)
    assert identity.body["deviceId"] == hub.identity.device_id
    assert identity.body["tcpPort"] == hub.tcp_port
    assert hub.connected_info(new.identity.device_id).protocol_version == 8

    old = peers.device(protocol_version=7)
    await _connect(hub, old)
    assert hub.connected_info(old.identity.device_id).protocol_version == 7
    assert not [p for p in old.packets if p.type == PACKET_TYPE_IDENTITY]
    assert hub.connected_info("e" * 32) is None


def test_send_on_link_not_ready() -> None:
    """A link that is not ready refuses to send, and closes without a transport."""
    link = Link(MagicMock())
    assert link.host is None
    assert not link.send(Packet(PACKET_TYPE_PING))
    link.close()


# Starting and stopping


async def test_no_free_tcp_port() -> None:
    """Starting fails when every TCP port in the range is taken."""
    taken = socket.socket()
    taken.bind(("0.0.0.0", 0))
    taken.listen()
    port = taken.getsockname()[1]
    hub = _new_hub()
    try:
        with (
            patch.object(hub_module, "MIN_TCP_PORT", port),
            patch.object(hub_module, "MAX_TCP_PORT", port),
            pytest.raises(OSError, match="No free TCP port"),
        ):
            await hub.start()
    finally:
        taken.close()
        await hub.stop()


async def test_udp_port_in_use() -> None:
    """Starting fails, and cleans up, when the UDP port is taken."""
    taken = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    taken.bind(("0.0.0.0", 0))
    hub = _new_hub(udp_port=taken.getsockname()[1])
    try:
        with pytest.raises(OSError):
            await hub.start()
        assert hub._server is None
        assert hub._udp is None
    finally:
        taken.close()


async def test_announce(hub: KdeConnectHub) -> None:
    """Announcing does nothing before start, and survives send errors."""
    _new_hub().announce(["127.0.0.1"])
    hub.announce(["127.0.0.1"])
    with patch.object(hub._udp, "sendto", side_effect=OSError("unreachable")):
        hub.announce(["127.0.0.1"])


# Discovery


async def test_datagrams(hub: KdeConnectHub) -> None:
    """Only valid identity datagrams that fit are taken in."""
    discovery = _Discovery(hub)
    addr = ("10.0.0.5", 1716)
    good = _identity_line("b" * 32)
    discovery.datagram_received(b" " * (MAX_IDENTITY_PACKET_SIZE + 1), addr)
    discovery.datagram_received(b"{nope", addr)
    discovery.datagram_received(Packet(PACKET_TYPE_PING).serialize(), addr)
    discovery.datagram_received(_identity_line("short"), addr)
    assert hub.discovered == {}
    discovery.datagram_received(good, addr)
    assert hub.discovered["b" * 32].host == "10.0.0.5"


async def test_real_datagram(hub: KdeConnectHub) -> None:
    """An identity sent to the UDP socket shows up as discovered."""
    port = hub._udp.get_extra_info("sockname")[1]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(_identity_line("b" * 32), ("127.0.0.1", port))
    await _until(lambda: "b" * 32 in hub.discovered)


async def test_identity_received(hub: KdeConnectHub) -> None:
    """We only answer trusted devices, or anyone while discovering, now and then."""
    calls = []
    remove = hub.add_discovery_listener(lambda: calls.append(1))

    def info(device_id: str, host: str | None = "10.0.0.5", name="PC") -> DeviceInfo:
        return DeviceInfo(device_id, name, host=host)

    with patch.object(hub, "announce") as announce:
        hub._identity_received(info(hub.identity.device_id))
        assert hub.discovered == {}
        assert not calls

        hub._identity_received(info("b" * 32))
        announce.assert_not_called()
        assert len(calls) == 1

        stop = hub.start_discovery()
        hub._identity_received(info("b" * 32, name="Renamed"))
        assert hub.discovered["b" * 32].name == "Renamed"
        announce.assert_called_once_with(["10.0.0.5"])
        hub._identity_received(info("b" * 32))
        assert announce.call_count == 1
        hub._identity_received(info("c" * 32, host=None))
        assert announce.call_count == 1
        stop()
        stop()
        assert hub._discovering == 0

        hub.set_trusted({"f" * 32: b"cert"})
        hub._identity_received(info("f" * 32))
        assert announce.call_count == 2
        hub._links["f" * 32] = MagicMock()
        hub._answered.clear()
        hub._identity_received(info("f" * 32))
        assert announce.call_count == 2
        del hub._links["f" * 32]

    remove()
    hub._identity_received(info("b" * 32))
    assert len(calls) == 6


# Links and trust


async def test_pinned_certificate_mismatch(
    hub: KdeConnectHub, peers: Peers, caplog
) -> None:
    """A trusted device id with another certificate is turned away."""
    device = peers.device()
    hub.set_trusted({device.identity.device_id: _identity(1).certificate_der})
    await device.connect(hub.tcp_port)
    await _until(lambda: "different certificate" in caplog.text)
    assert not hub.is_link_connected(device.identity.device_id)


async def test_too_many_untrusted(hub: KdeConnectHub, peers: Peers) -> None:
    """Untrusted links beyond the limit are closed."""
    device = peers.device()
    with patch.object(hub_module, "MAX_UNTRUSTED_LINKS", 0):
        await device.connect(hub.tcp_port)
        await _until(lambda: not device.connected)
    assert not hub.is_link_connected(device.identity.device_id)


async def test_reconnect_replaces_link(hub: KdeConnectHub, peers: Peers) -> None:
    """A second connection from the same device replaces the first."""
    first = peers.device()
    events: list[bool] = []
    hub.add_connection_listener(first.identity.device_id, events.append)
    await _connect_trusted(hub, first)
    old = hub._links[first.identity.device_id]
    second = peers.device()
    second.identity = first.identity
    await second.connect(hub.tcp_port)
    await _until(lambda: hub._links[first.identity.device_id] is not old)
    await _until(lambda: not first.connected)
    assert hub.is_connected(first.identity.device_id)
    assert events == [True]

    second.close()
    await _until(lambda: not hub.is_link_connected(first.identity.device_id))
    assert events == [True, False]
    assert not old.send(Packet(PACKET_TYPE_PING))


async def test_packets_from_devices(hub: KdeConnectHub, peers: Peers, caplog) -> None:
    """Untrusted devices are told we are not paired; listener errors are logged."""
    device = peers.device()
    await _connect(hub, device)
    device.send(Packet(PACKET_TYPE_PING))
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    assert not hub.send(device.identity.device_id, Packet(PACKET_TYPE_PING))

    hub.set_trusted({device.identity.device_id: device.identity.certificate_der})
    received: list[Packet] = []

    def broken(packet: Packet) -> None:
        raise RuntimeError("boom")

    hub.add_packet_listener(device.identity.device_id, broken)
    remove = hub.add_packet_listener(device.identity.device_id, received.append)
    device.send(Packet(PACKET_TYPE_PING, {"message": "hi"}))
    await _until(lambda: bool(received))
    assert "Error handling kdeconnect.ping" in caplog.text
    remove()

    assert hub.send(device.identity.device_id, Packet(PACKET_TYPE_PING))
    await device.wait_for(PACKET_TYPE_PING)


# Pairing that we start


async def test_pairing_accepted(hub: KdeConnectHub, peers: Peers) -> None:
    """The device accepts, and its certificate is trusted."""
    device = peers.device(protocol_version=8)
    await _connect(hub, device)
    pairing = hub.start_pairing(device.identity.device_id)
    with pytest.raises(PairingError, match="in_progress"):
        hub.start_pairing(device.identity.device_id)
    info, der = await pairing.wait()
    assert info.device_id == device.identity.device_id
    assert der == device.identity.certificate_der
    assert hub.is_connected(device.identity.device_id)
    assert len(pairing.verification_key) == 8


async def test_pairing_not_connected(hub: KdeConnectHub) -> None:
    """Pairing needs a connected device."""
    with pytest.raises(PairingError, match="not_connected"):
        hub.start_pairing("b" * 32)


async def test_pairing_rejected(hub: KdeConnectHub, peers: Peers) -> None:
    """The device says no."""
    device = peers.device()
    device.auto_accept = False
    await _connect(hub, device)
    pairing = hub.start_pairing(device.identity.device_id)
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    with pytest.raises(PairingError, match="rejected"):
        await pairing.wait()
    assert not hub.is_connected(device.identity.device_id)


async def test_pairing_timeout(hub: KdeConnectHub, peers: Peers) -> None:
    """Nobody answers: we cancel the request on the device."""
    device = peers.device()
    device.auto_accept = False
    await _connect(hub, device)
    pairing = hub.start_pairing(device.identity.device_id)
    with pytest.raises(PairingError, match="timeout"):
        await pairing.wait(timeout=0.05)
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    assert not hub._pairings


async def test_pairing_connection_lost(hub: KdeConnectHub, peers: Peers) -> None:
    """The device goes away while we wait for its answer."""
    device = peers.device()
    device.auto_accept = False
    await _connect(hub, device)
    pairing = hub.start_pairing(device.identity.device_id)
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    device.close()
    with pytest.raises(PairingError, match="not_connected"):
        await pairing.wait()


# Pairing requests from devices


async def _incoming(hub: KdeConnectHub, device: FakeDevice) -> None:
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": True, "timestamp": int(time.time())}))
    await _until(lambda: device.identity.device_id in hub.incoming)


async def test_incoming_accepted(hub: KdeConnectHub, peers: Peers) -> None:
    """The user accepts a request from a protocol 8 device."""
    requests = []
    hub.on_pair_request = lambda: requests.append(1)
    device = peers.device(protocol_version=8)
    await _connect(hub, device)
    await _incoming(hub, device)
    assert requests == [1]
    # A packet while the request is open gets no "not paired" answer.
    device.send(Packet(PACKET_TYPE_PING))
    info, der = hub.accept_incoming(device.identity.device_id)
    assert info.device_id == device.identity.device_id
    assert der == device.identity.certificate_der
    await device.wait_for(PACKET_TYPE_PAIR, pair=True)
    assert not [p for p in device.packets if p.body.get("pair") is False]
    assert hub.is_connected(device.identity.device_id)
    with pytest.raises(PairingError, match="not_connected"):
        hub.accept_incoming(device.identity.device_id)


async def test_incoming_needs_timestamp(hub: KdeConnectHub, peers: Peers) -> None:
    """Protocol 8 requests without a timestamp are turned down."""
    device = peers.device(protocol_version=8)
    await _connect(hub, device)
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": True}))
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    assert not hub.incoming


async def test_incoming_declined_and_cancelled(
    hub: KdeConnectHub, peers: Peers
) -> None:
    """The user declines, or the device withdraws its request."""
    device = peers.device()
    await _connect(hub, device)
    await _incoming(hub, device)
    hub.decline_incoming(device.identity.device_id)
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    assert not hub.incoming
    hub.decline_incoming(device.identity.device_id)

    await _incoming(hub, device)
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    await _until(lambda: not hub.incoming)


async def test_incoming_expires(hub: KdeConnectHub, peers: Peers) -> None:
    """A request nobody answers runs out."""
    device = peers.device()
    await _connect(hub, device)
    with patch.object(hub_module, "PAIR_TIMEOUT", 0.05):
        await _incoming(hub, device)
        await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    assert not hub.incoming


async def test_incoming_link_closing(hub: KdeConnectHub, peers: Peers) -> None:
    """Accepting fails when the link is just going away."""
    device = peers.device()
    await _connect(hub, device)
    await _incoming(hub, device)
    hub._links[device.identity.device_id].close()
    with pytest.raises(PairingError, match="not_connected"):
        hub.accept_incoming(device.identity.device_id)
    await _until(lambda: not hub.is_link_connected(device.identity.device_id))


async def test_incoming_dropped_on_disconnect(
    hub: KdeConnectHub, peers: Peers
) -> None:
    """An open request goes away with the connection."""
    requests = []
    hub.on_pair_request = lambda: requests.append(1)
    device = peers.device()
    await _connect(hub, device)
    await _incoming(hub, device)
    device.close()
    await _until(lambda: not hub.incoming)
    assert requests == [1, 1]


# Unpairing


async def test_unpair_both_ways(hub: KdeConnectHub, peers: Peers) -> None:
    """The device unpairs us, we unpair it, and trust is withdrawn."""
    unpaired: list[str] = []
    device = peers.device()
    await _connect_trusted(hub, device)
    device_id = device.identity.device_id

    # Without a callback, an unpair from the device is only ignored.
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    await asyncio.sleep(0.05)
    hub.on_unpaired = unpaired.append
    device.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
    await _until(lambda: unpaired == [device_id])

    hub.unpair(device_id)
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    hub.unpair("e" * 32)

    device.packets.clear()
    hub.set_trusted({})
    await device.wait_for(PACKET_TYPE_PAIR, pair=False)
    await _until(lambda: not device.connected)
    assert not hub.is_link_connected(device_id)


# Files offered by a device


async def _serve(identity: Identity, data: bytes) -> asyncio.Server:
    async def handle(reader, writer) -> None:
        writer.write(data)
        await writer.drain()
        writer.close()

    return await asyncio.start_server(
        handle, "127.0.0.1", 0, ssl=_server_context(identity)
    )


async def test_download_payload(hub: KdeConnectHub, peers: Peers) -> None:
    """Download a file, and refuse other certificates and short transfers."""
    device = peers.device()
    with pytest.raises(OSError, match="is not connected"):
        await hub.async_download_payload(device.identity.device_id, 1, 1)
    await _connect_trusted(hub, device)
    device_id = device.identity.device_id

    servers = [
        await _serve(device.identity, b"hello"),
        await _serve(_identity(1), b"hello"),
    ]
    try:
        port = servers[0].sockets[0].getsockname()[1]
        assert await hub.async_download_payload(device_id, port, 5) == b"hello"
        with pytest.raises(OSError, match="stopped early"):
            await hub.async_download_payload(device_id, port, 10)
        port = servers[1].sockets[0].getsockname()[1]
        with pytest.raises(OSError, match="another certificate"):
            await hub.async_download_payload(device_id, port, 5)
    finally:
        for server in servers:
            server.close()
            await server.wait_closed()
