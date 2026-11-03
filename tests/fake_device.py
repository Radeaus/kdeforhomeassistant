"""A minimal KDE Connect peer that connects to the hub, like a real PC would."""

from __future__ import annotations

import asyncio
import json
import os
import ssl
import tempfile

from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_IDENTITY,
    PACKET_TYPE_LOCK,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_PAIR,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    Identity,
    Packet,
    generate_identity,
)

CAPABILITIES = [
    PACKET_TYPE_LOCK,
    PACKET_TYPE_LOCK_REQUEST,
    PACKET_TYPE_RUNCOMMAND,
    PACKET_TYPE_RUNCOMMAND_REQUEST,
    "kdeconnect.notification",
    "kdeconnect.findmyphone.request",
    "kdeconnect.ping",
]


class _PeerProtocol(asyncio.Protocol):
    def __init__(self, device: FakeDevice) -> None:
        self.device = device
        self.buffer = b""

    def data_received(self, data: bytes) -> None:
        self.buffer += data
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            if line.strip():
                self.device.received(Packet.parse(line))

    def connection_lost(self, exc: Exception | None) -> None:
        self.device.connected = False


class FakeDevice:
    """Acts as KDE Connect 23.08 (protocol 7) or newer (protocol 8)."""

    def __init__(self, name: str = "Fake PC", protocol_version: int = 7) -> None:
        self.identity: Identity = generate_identity(name)
        self.identity.device_type = "desktop"
        self.protocol_version = protocol_version
        self.transport: asyncio.Transport | None = None
        self.packets: list[Packet] = []
        self.connected = False
        self.auto_accept = True
        self.commands: dict[str, dict[str, str]] = {}
        self.locked = False
        self._event = asyncio.Event()

    def _identity_packet(self) -> Packet:
        packet = self.identity.identity_packet(CAPABILITIES, CAPABILITIES)
        packet.body["protocolVersion"] = self.protocol_version
        return packet

    def _server_context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        fd, path = tempfile.mkstemp(suffix=".pem")
        with os.fdopen(fd, "w") as file:
            file.write(self.identity.private_key_pem + self.identity.certificate_pem)
        context.load_cert_chain(path)
        os.unlink(path)
        return context

    async def connect(self, port: int) -> None:
        """Connect to the hub the way KDE Connect does after a UDP announce."""
        loop = asyncio.get_running_loop()
        protocol = _PeerProtocol(self)
        self.transport = None
        self._pending: list[Packet] = []
        context = await loop.run_in_executor(None, self._server_context)
        transport, _ = await loop.create_connection(lambda: protocol, "127.0.0.1", port)
        transport.write(self._identity_packet().serialize())
        self.transport = await loop.start_tls(
            transport, protocol, context, server_side=True
        )
        for packet in self._pending:
            self.transport.write(packet.serialize())
        if self.protocol_version >= 8:
            self.send(self._identity_packet())
        self.connected = True

    def send(self, packet: Packet) -> None:
        """Send a packet to Home Assistant."""
        if self.transport is None:
            # Replies to packets that arrive while start_tls is finishing.
            self._pending.append(packet)
            return
        self.transport.write(packet.serialize())

    def received(self, packet: Packet) -> None:
        """Answer like the real KDE Connect plugins."""
        self.packets.append(packet)
        body = packet.body
        if packet.type == PACKET_TYPE_PAIR and body.get("pair") and self.auto_accept:
            self.send(Packet(PACKET_TYPE_PAIR, {"pair": True}))
        elif packet.type == PACKET_TYPE_RUNCOMMAND_REQUEST and body.get(
            "requestCommandList"
        ):
            self.send_commands()
        elif packet.type == PACKET_TYPE_LOCK_REQUEST:
            if "setLocked" in body:
                self.locked = bool(body["setLocked"])
            self.send(Packet(PACKET_TYPE_LOCK, {"isLocked": self.locked}))
        elif packet.type == PACKET_TYPE_IDENTITY:
            pass
        self._event.set()

    def send_commands(self) -> None:
        """Send the configured run commands."""
        self.send(
            Packet(
                PACKET_TYPE_RUNCOMMAND,
                {"commandList": json.dumps(self.commands), "canAddCommand": True},
            )
        )

    def close(self) -> None:
        """Disconnect."""
        if self.transport:
            self.transport.close()

    async def wait_for(self, packet_type: str, timeout: float = 5, **body) -> Packet:
        """Wait for a packet of this type, optionally with matching body fields."""
        async with asyncio.timeout(timeout):
            while True:
                for packet in self.packets:
                    if packet.type == packet_type and all(
                        packet.body.get(key) == value for key, value in body.items()
                    ):
                        return packet
                self._event.clear()
                await self._event.wait()
