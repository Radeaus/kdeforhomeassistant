"""KDE Connect over the LAN: discovery, TLS links and pairing.

Discovery happens over UDP. Instead of connecting out, we always answer a
device with our own identity so it opens the TCP connection to us. That keeps
us on the TLS client side, where the standard library lets us accept the
self-signed certificates KDE Connect uses and pin them ourselves.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import socket
import ssl
import tempfile
import time
from collections.abc import Callable, Iterable

from .protocol import (
    MAX_IDENTITY_PACKET_SIZE,
    MAX_TCP_PORT,
    MIN_TCP_PORT,
    PACKET_TYPE_IDENTITY,
    PACKET_TYPE_PAIR,
    UDP_PORT,
    DeviceInfo,
    Identity,
    Packet,
    ProtocolError,
    certificate_common_name,
    verification_key,
)

_LOGGER = logging.getLogger(__name__)

HANDSHAKE_TIMEOUT = 10
PAIR_TIMEOUT = 30
MAX_PACKET_SIZE = 1024 * 1024
MAX_UNTRUSTED_LINKS = 16
ANSWER_INTERVAL = 5

PacketListener = Callable[[Packet], None]
ConnectionListener = Callable[[bool], None]


class PairingError(Exception):
    """Pairing did not succeed; the message is a short reason code."""


class Link(asyncio.Protocol):
    """One TCP connection that a device opened to us."""

    def __init__(self, hub: KdeConnectHub) -> None:
        self._hub = hub
        self._transport: asyncio.Transport | None = None
        self._buffer = bytearray()
        self._state = "identity"
        self._timeout: asyncio.TimerHandle | None = None
        self._host: str | None = None
        self.info: DeviceInfo | None = None
        self.certificate_der: bytes | None = None

    @property
    def ready(self) -> bool:
        """Return whether the link is encrypted and identified."""
        return self._state == "ready"

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Start waiting for the identity packet."""
        assert isinstance(transport, asyncio.Transport)
        self._transport = transport
        peer = transport.get_extra_info("peername")
        self._host = peer[0] if peer else None
        sock = transport.get_extra_info("socket")
        if sock is not None:
            _enable_keepalive(sock)
        self._timeout = asyncio.get_running_loop().call_later(
            HANDSHAKE_TIMEOUT, self._abort, "handshake timed out"
        )

    def data_received(self, data: bytes) -> None:
        """Split incoming data into packets."""
        self._buffer += data
        limit = MAX_PACKET_SIZE if self.ready else MAX_IDENTITY_PACKET_SIZE
        while (end := self._buffer.find(b"\n")) != -1:
            line = bytes(self._buffer[:end])
            del self._buffer[: end + 1]
            self._handle_line(line)
            if self._state in ("tls", "closed"):
                return
        if len(self._buffer) > limit:
            self._abort("packet too large")

    def _handle_line(self, line: bytes) -> None:
        if not line.strip():
            return
        try:
            packet = Packet.parse(line)
            if self._state == "identity":
                self._handle_plain_identity(packet)
            elif self._state == "secure_identity":
                self._handle_secure_identity(packet)
            elif self._state == "ready":
                self._hub._packet_received(self, packet)
        except ProtocolError as err:
            self._abort(str(err))

    def _handle_plain_identity(self, packet: Packet) -> None:
        info = DeviceInfo.from_identity(packet, self._host)
        target = packet.body.get("targetDeviceId")
        if info.device_id == self._hub.identity.device_id or (
            target is not None and target != self._hub.identity.device_id
        ):
            raise ProtocolError("Connection is not meant for us")
        self.info = info
        self._state = "tls"
        asyncio.get_running_loop().create_task(self._start_tls())

    def _handle_secure_identity(self, packet: Packet) -> None:
        assert self.info is not None
        secure = DeviceInfo.from_identity(packet, self._host)
        if secure.device_id != self.info.device_id:
            raise ProtocolError("Device id changed after encryption")
        self.info.merge(secure)
        self._set_ready()

    async def _start_tls(self) -> None:
        assert self._transport is not None and self.info is not None
        loop = asyncio.get_running_loop()
        try:
            transport = await loop.start_tls(
                self._transport,
                self,
                self._hub.ssl_context,
                server_side=False,
                ssl_handshake_timeout=HANDSHAKE_TIMEOUT,
            )
        except (OSError, ssl.SSLError, TimeoutError) as err:
            self._abort(f"TLS handshake failed: {err}")
            return
        if transport is None:
            self._abort("connection closed during TLS handshake")
            return
        self._transport = transport
        ssl_object = transport.get_extra_info("ssl_object")
        der = ssl_object.getpeercert(binary_form=True) if ssl_object else None
        if not der or certificate_common_name(der) != self.info.device_id:
            self._abort("certificate does not belong to this device")
            return
        self.certificate_der = der
        if self.info.protocol_version >= 8:
            self._state = "secure_identity"
            transport.write(self._hub.identity_packet().serialize())
        else:
            self._set_ready()

    def _set_ready(self) -> None:
        if self._timeout:
            self._timeout.cancel()
            self._timeout = None
        self._state = "ready"
        self._hub._link_ready(self)

    def send(self, packet: Packet) -> bool:
        """Send a packet, returning False when the link is gone."""
        if not self.ready or self._transport is None or self._transport.is_closing():
            return False
        self._transport.write(packet.serialize())
        return True

    def close(self) -> None:
        """Close the connection."""
        if self._transport is not None:
            self._transport.close()

    def _abort(self, reason: str) -> None:
        name = self.info.name if self.info else self._host
        _LOGGER.debug("Dropping connection from %s: %s", name, reason)
        if self._transport is not None:
            self._transport.abort()

    def connection_lost(self, exc: Exception | None) -> None:
        """Tell the hub when an established link goes away."""
        if self._timeout:
            self._timeout.cancel()
            self._timeout = None
        was_ready = self.ready
        self._state = "closed"
        if was_ready:
            self._hub._link_lost(self)


class _Discovery(asyncio.DatagramProtocol):
    def __init__(self, hub: KdeConnectHub) -> None:
        self._hub = hub

    def datagram_received(self, data: bytes, addr: tuple[str | int, ...]) -> None:
        if len(data) > MAX_IDENTITY_PACKET_SIZE:
            return
        try:
            packet = Packet.parse(data)
            if packet.type != PACKET_TYPE_IDENTITY:
                return
            info = DeviceInfo.from_identity(packet, str(addr[0]))
        except ProtocolError:
            return
        self._hub._identity_received(info)


class PendingPairing:
    """A pairing request we sent and are waiting on."""

    def __init__(
        self, hub: KdeConnectHub, link: Link, timestamp: int, key: str
    ) -> None:
        self._hub = hub
        self._link = link
        self.timestamp = timestamp
        self.verification_key = key
        self.future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()

    async def wait(self, timeout: float = PAIR_TIMEOUT) -> tuple[DeviceInfo, bytes]:
        """Wait for the device to accept and return its info and certificate."""
        assert self._link.info is not None and self._link.certificate_der is not None
        device_id = self._link.info.device_id
        try:
            accepted = await asyncio.wait_for(self.future, timeout)
        except TimeoutError:
            self._link.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
            raise PairingError("timeout") from None
        finally:
            self._hub._pairings.pop(device_id, None)
        if not accepted:
            raise PairingError("rejected")
        return self._link.info, self._link.certificate_der


class IncomingPairing:
    """A pairing request a device sent us, waiting for the user to answer."""

    def __init__(
        self, info: DeviceInfo, certificate_der: bytes, key: str
    ) -> None:
        self.info = info
        self.certificate_der = certificate_der
        self.verification_key = key
        self.timeout: asyncio.TimerHandle | None = None


class KdeConnectHub:
    """Keeps the sockets and the links to all devices."""

    def __init__(
        self,
        identity: Identity,
        *,
        incoming_capabilities: Iterable[str],
        outgoing_capabilities: Iterable[str],
        udp_port: int = UDP_PORT,
    ) -> None:
        self.identity = identity
        self._incoming = sorted(incoming_capabilities)
        self._outgoing = sorted(outgoing_capabilities)
        self._udp_port = udp_port
        self.tcp_port: int | None = None
        self.ssl_context: ssl.SSLContext | None = None
        self._server: asyncio.Server | None = None
        self._udp: asyncio.DatagramTransport | None = None
        self._trusted: dict[str, bytes] = {}
        self._links: dict[str, Link] = {}
        self._pairings: dict[str, PendingPairing] = {}
        self.incoming: dict[str, IncomingPairing] = {}
        self._answered: dict[str, float] = {}
        self._packet_listeners: dict[str, list[PacketListener]] = {}
        self._connection_listeners: dict[str, list[ConnectionListener]] = {}
        self._discovery_listeners: list[Callable[[], None]] = []
        self._discovering = 0
        self.discovered: dict[str, DeviceInfo] = {}
        self.on_pair_request: Callable[[], None] | None = None
        self.on_unpaired: Callable[[str], None] | None = None

    async def start(self) -> None:
        """Open the TCP server and the UDP discovery socket."""
        loop = asyncio.get_running_loop()
        self.ssl_context = await loop.run_in_executor(None, self._build_ssl_context)
        last_error: OSError | None = None
        for port in range(MIN_TCP_PORT, MAX_TCP_PORT + 1):
            try:
                self._server = await loop.create_server(
                    lambda: Link(self), host="0.0.0.0", port=port
                )
            except OSError as err:
                last_error = err
                continue
            self.tcp_port = port
            break
        else:
            raise OSError(
                f"No free TCP port between {MIN_TCP_PORT} and {MAX_TCP_PORT}"
            ) from last_error
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("0.0.0.0", self._udp_port))
        except OSError:
            sock.close()
            await self.stop()
            raise
        self._udp, _ = await loop.create_datagram_endpoint(
            lambda: _Discovery(self), sock=sock
        )
        _LOGGER.debug(
            "Listening as %s on TCP %s and UDP %s",
            self.identity.device_id,
            self.tcp_port,
            self._udp_port,
        )

    async def stop(self) -> None:
        """Close every connection and socket."""
        for link in list(self._links.values()):
            link.close()
        self._links.clear()
        if self._udp is not None:
            self._udp.close()
            self._udp = None
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._server.wait_closed(), 2)
            self._server = None

    def _build_ssl_context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        fd, path = tempfile.mkstemp(suffix=".pem")
        try:
            with os.fdopen(fd, "w") as file:
                file.write(self.identity.private_key_pem)
                file.write(self.identity.certificate_pem)
            context.load_cert_chain(path)
        finally:
            os.unlink(path)
        return context

    def identity_packet(self) -> Packet:
        """Return our identity, including the TCP port to connect to."""
        return self.identity.identity_packet(
            self._incoming, self._outgoing, self.tcp_port
        )

    # Discovery

    def announce(self, hosts: Iterable[str]) -> None:
        """Send our identity so the devices at these addresses connect to us."""
        if self._udp is None:
            return
        data = self.identity_packet().serialize()
        for host in hosts:
            try:
                self._udp.sendto(data, (host, UDP_PORT))
            except OSError as err:
                _LOGGER.debug("Could not announce to %s: %s", host, err)

    def start_discovery(self) -> Callable[[], None]:
        """Also answer untrusted devices until the returned callable is called."""
        self._discovering += 1
        ended = False

        def stop() -> None:
            nonlocal ended
            if not ended:
                ended = True
                self._discovering -= 1

        return stop

    def add_discovery_listener(
        self, listener: Callable[[], None]
    ) -> Callable[[], None]:
        """Call the listener whenever the list of discovered devices changes."""
        self._discovery_listeners.append(listener)
        return lambda: self._discovery_listeners.remove(listener)

    def _identity_received(self, info: DeviceInfo) -> None:
        if info.device_id == self.identity.device_id:
            return
        known = self.discovered.get(info.device_id)
        if known is None:
            self.discovered[info.device_id] = info
        else:
            known.merge(info)
        self._notify_discovery()
        if info.device_id in self._links or info.host is None:
            return
        if info.device_id not in self._trusted and not self._discovering:
            return
        now = time.monotonic()
        if now - self._answered.get(info.device_id, 0) < ANSWER_INTERVAL:
            return
        self._answered[info.device_id] = now
        self.announce([info.host])

    def _notify_discovery(self) -> None:
        for listener in list(self._discovery_listeners):
            listener()

    # Links

    def _link_ready(self, link: Link) -> None:
        assert link.info is not None and link.certificate_der is not None
        device_id = link.info.device_id
        pinned = self._trusted.get(device_id)
        if pinned is not None and pinned != link.certificate_der:
            _LOGGER.warning(
                "%s connected with a different certificate than the one it was paired with; ignoring it",
                link.info.name,
            )
            link.close()
            return
        if pinned is None:
            untrusted = [d for d in self._links if d not in self._trusted]
            if len(untrusted) >= MAX_UNTRUSTED_LINKS:
                link.close()
                return
        old = self._links.get(device_id)
        self._links[device_id] = link
        if old is not None and old is not link:
            old.close()
        known = self.discovered.get(device_id)
        if known is None:
            self.discovered[device_id] = link.info
        else:
            known.merge(link.info)
        _LOGGER.debug("%s connected", link.info.name)
        if pinned is not None and old is None:
            self._notify_connection(device_id, True)
        self._notify_discovery()

    def _link_lost(self, link: Link) -> None:
        assert link.info is not None
        device_id = link.info.device_id
        if self._links.get(device_id) is not link:
            return
        del self._links[device_id]
        _LOGGER.debug("%s disconnected", link.info.name)
        if (pairing := self._pairings.get(device_id)) and not pairing.future.done():
            pairing.future.set_exception(PairingError("not_connected"))
        self._drop_incoming(device_id)
        if device_id in self._trusted:
            self._notify_connection(device_id, False)
        self._notify_discovery()

    def _packet_received(self, link: Link, packet: Packet) -> None:
        assert link.info is not None
        device_id = link.info.device_id
        _LOGGER.debug("Received %s from %s", packet.type, link.info.name)
        if packet.type == PACKET_TYPE_PAIR:
            self._handle_pair(link, packet)
            return
        if device_id not in self._trusted:
            if device_id not in self._pairings and device_id not in self.incoming:
                link.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
            return
        for listener in list(self._packet_listeners.get(device_id, ())):
            try:
                listener(packet)
            except Exception:
                _LOGGER.exception(
                    "Error handling %s from %s", packet.type, link.info.name
                )

    def _handle_pair(self, link: Link, packet: Packet) -> None:
        assert link.info is not None
        device_id = link.info.device_id
        pairing = self._pairings.get(device_id)
        if packet.body.get("pair") is True:
            if pairing is not None:
                if not pairing.future.done():
                    # Trust right away; the device starts sending packets
                    # in the same breath as its answer.
                    assert link.certificate_der is not None
                    self._trusted[device_id] = link.certificate_der
                    pairing.future.set_result(True)
                    self._notify_connection(device_id, True)
            elif device_id in self._trusted:
                # The device forgot us but we still trust its certificate.
                link.send(Packet(PACKET_TYPE_PAIR, {"pair": True}))
            else:
                self._add_incoming(link, packet)
            return
        if pairing is not None:
            if not pairing.future.done():
                pairing.future.set_result(False)
        elif device_id in self.incoming:
            self._drop_incoming(device_id)
        elif device_id in self._trusted and self.on_unpaired:
            self.on_unpaired(device_id)

    # Pairing requests from devices

    def _add_incoming(self, link: Link, packet: Packet) -> None:
        """Keep a pairing request open until the user answers or it expires."""
        assert link.info is not None and link.certificate_der is not None
        device_id = link.info.device_id
        timestamp = packet.body.get("timestamp")
        if link.info.protocol_version >= 8 and not isinstance(timestamp, int):
            link.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
            return
        self._drop_incoming(device_id, notify=False)
        key = verification_key(
            self.identity.certificate_der,
            link.certificate_der,
            timestamp if link.info.protocol_version >= 8 else None,
        )
        request = IncomingPairing(link.info, link.certificate_der, key)
        request.timeout = asyncio.get_running_loop().call_later(
            PAIR_TIMEOUT, self._expire_incoming, device_id, request
        )
        self.incoming[device_id] = request
        _LOGGER.debug("%s asked to pair", link.info.name)
        self._notify_pair_request()

    def _expire_incoming(self, device_id: str, request: IncomingPairing) -> None:
        if self.incoming.get(device_id) is request:
            self.decline_incoming(device_id)

    def _drop_incoming(self, device_id: str, *, notify: bool = True) -> None:
        request = self.incoming.pop(device_id, None)
        if request is None:
            return
        if request.timeout:
            request.timeout.cancel()
        if notify:
            self._notify_pair_request()

    def _notify_pair_request(self) -> None:
        if self.on_pair_request:
            self.on_pair_request()

    def accept_incoming(self, device_id: str) -> tuple[DeviceInfo, bytes]:
        """Accept a pairing request and trust the device from now on."""
        request = self.incoming.get(device_id)
        link = self._links.get(device_id)
        if request is None or link is None:
            raise PairingError("not_connected")
        self._drop_incoming(device_id)
        if not link.send(Packet(PACKET_TYPE_PAIR, {"pair": True})):
            raise PairingError("not_connected")
        self._trusted[device_id] = request.certificate_der
        self._notify_connection(device_id, True)
        return request.info, request.certificate_der

    def decline_incoming(self, device_id: str) -> None:
        """Turn down a pairing request."""
        if device_id not in self.incoming:
            return
        self._drop_incoming(device_id)
        if link := self._links.get(device_id):
            link.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))

    # Pairing and trust

    def start_pairing(self, device_id: str) -> PendingPairing:
        """Send a pairing request to a connected device."""
        link = self._links.get(device_id)
        if link is None or link.certificate_der is None:
            raise PairingError("not_connected")
        if device_id in self._pairings:
            raise PairingError("in_progress")
        timestamp = int(time.time())
        assert link.info is not None
        key = verification_key(
            self.identity.certificate_der,
            link.certificate_der,
            timestamp if link.info.protocol_version >= 8 else None,
        )
        pairing = PendingPairing(self, link, timestamp, key)
        self._pairings[device_id] = pairing
        link.send(Packet(PACKET_TYPE_PAIR, {"pair": True, "timestamp": timestamp}))
        return pairing

    def set_trusted(self, devices: dict[str, bytes]) -> None:
        """Replace the set of trusted devices and their pinned certificates."""
        removed = set(self._trusted) - set(devices)
        self._trusted = dict(devices)
        for device_id in removed:
            if link := self._links.get(device_id):
                link.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))
                link.close()

    def unpair(self, device_id: str) -> None:
        """Tell a device we no longer trust it."""
        if link := self._links.get(device_id):
            link.send(Packet(PACKET_TYPE_PAIR, {"pair": False}))

    # Talking to trusted devices

    def is_connected(self, device_id: str) -> bool:
        """Return whether a trusted device is connected."""
        return device_id in self._trusted and device_id in self._links

    def connected_info(self, device_id: str) -> DeviceInfo | None:
        """Return what a connected device told us about itself."""
        link = self._links.get(device_id)
        return link.info if link else None

    def is_link_connected(self, device_id: str) -> bool:
        """Return whether any device, trusted or not, has a link to us."""
        return device_id in self._links

    def send(self, device_id: str, packet: Packet) -> bool:
        """Send a packet to a trusted device."""
        if (
            device_id not in self._trusted
            or (link := self._links.get(device_id)) is None
        ):
            return False
        return link.send(packet)

    def add_packet_listener(
        self, device_id: str, listener: PacketListener
    ) -> Callable[[], None]:
        """Receive packets from a trusted device."""
        listeners = self._packet_listeners.setdefault(device_id, [])
        listeners.append(listener)
        return lambda: listeners.remove(listener)

    def add_connection_listener(
        self, device_id: str, listener: ConnectionListener
    ) -> Callable[[], None]:
        """Hear when a trusted device connects or disconnects."""
        listeners = self._connection_listeners.setdefault(device_id, [])
        listeners.append(listener)
        return lambda: listeners.remove(listener)

    def _notify_connection(self, device_id: str, connected: bool) -> None:
        for listener in list(self._connection_listeners.get(device_id, ())):
            listener(connected)


def _enable_keepalive(sock: socket.socket) -> None:
    with contextlib.suppress(OSError, AttributeError):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
