"""Tests for packets, identities and certificates."""

from __future__ import annotations

import pytest

from custom_components.kdeforhomeassistant.kdeconnect.protocol import (
    PACKET_TYPE_IDENTITY,
    PACKET_TYPE_PING,
    DeviceInfo,
    Packet,
    ProtocolError,
    certificate_fingerprint,
    filter_device_name,
    generate_identity,
)

DEVICE_ID = "a" * 32


@pytest.mark.parametrize("line", [b"{not json", b"\xff\xfe", b"[1, 2]", b'{"type": 5}'])
def test_parse_rejects_bad_packets(line: bytes) -> None:
    """Lines that are not JSON objects with a type are refused."""
    with pytest.raises(ProtocolError):
        Packet.parse(line)


def test_parse_payload() -> None:
    """A payload size and port come through; nonsense values are dropped."""
    packet = Packet.parse(
        b'{"type":"x","body":[],"payloadSize":10,"payloadTransferInfo":{"port":1739}}'
    )
    assert packet.body == {}
    assert packet.payload_size == 10
    assert packet.payload_port == 1739
    packet = Packet.parse(
        b'{"type":"x","payloadSize":-1,"payloadTransferInfo":{"port":70000}}'
    )
    assert packet.payload_size is None
    assert packet.payload_port is None
    again = Packet.parse(
        Packet("x", {"a": 1}, payload_size=3, payload_port=1740).serialize()
    )
    assert (again.payload_size, again.payload_port) == (3, 1740)


def test_filter_device_name() -> None:
    """Forbidden characters are removed and non-strings give an empty name."""
    assert filter_device_name(None) == ""
    assert filter_device_name(" Jan's (PC)! ") == "Jans PC"
    assert filter_device_name("x" * 40) == "x" * 32


def test_from_identity_rejects() -> None:
    """Only identity packets with a valid device id become device info."""
    with pytest.raises(ProtocolError, match="Expected an identity packet"):
        DeviceInfo.from_identity(Packet(PACKET_TYPE_PING, {"deviceId": DEVICE_ID}))
    with pytest.raises(ProtocolError, match="invalid device id"):
        DeviceInfo.from_identity(Packet(PACKET_TYPE_IDENTITY, {"deviceId": "short"}))


def test_from_identity_and_merge() -> None:
    """Missing or malformed fields get defaults, and merge fills them in later."""
    info = DeviceInfo.from_identity(
        Packet(
            PACKET_TYPE_IDENTITY,
            {
                "deviceId": DEVICE_ID,
                "protocolVersion": "8",
                "incomingCapabilities": "kdeconnect.ping",
                "outgoingCapabilities": ["kdeconnect.ping", 3],
                "tcpPort": "1716",
            },
        )
    )
    assert info.name == DEVICE_ID
    assert info.device_type == "unknown"
    assert info.protocol_version == 0
    assert info.incoming_capabilities == frozenset()
    assert info.outgoing_capabilities == frozenset({"kdeconnect.ping"})
    assert info.host is None
    assert info.tcp_port is None

    later = DeviceInfo.from_identity(
        Packet(
            PACKET_TYPE_IDENTITY,
            {
                "deviceId": DEVICE_ID,
                "deviceName": "Laptop",
                "deviceType": "laptop",
                "protocolVersion": 8,
                "incomingCapabilities": ["kdeconnect.lock"],
                "tcpPort": 1720,
            },
        ),
        host="10.0.0.2",
    )
    info.merge(later)
    assert info.name == "Laptop"
    assert info.device_type == "laptop"
    assert info.protocol_version == 8
    assert info.incoming_capabilities == frozenset({"kdeconnect.lock"})
    assert info.outgoing_capabilities == frozenset()
    assert info.host == "10.0.0.2"
    assert info.tcp_port == 1720


def test_certificate_fingerprint() -> None:
    """The fingerprint is the SHA-256 digest in colon separated pairs."""
    identity = generate_identity("Test")
    fingerprint = certificate_fingerprint(identity.certificate_der)
    parts = fingerprint.split(":")
    assert len(parts) == 32
    assert all(len(part) == 2 for part in parts)
    assert fingerprint == fingerprint.lower()
