"""KDE Connect packets, identities and certificates."""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

PROTOCOL_VERSION = 8
UDP_PORT = 1716
MIN_TCP_PORT = 1716
MAX_TCP_PORT = 1764
MAX_IDENTITY_PACKET_SIZE = 8192

PACKET_TYPE_IDENTITY = "kdeconnect.identity"
PACKET_TYPE_PAIR = "kdeconnect.pair"
PACKET_TYPE_PING = "kdeconnect.ping"
PACKET_TYPE_RUNCOMMAND = "kdeconnect.runcommand"
PACKET_TYPE_RUNCOMMAND_REQUEST = "kdeconnect.runcommand.request"
PACKET_TYPE_NOTIFICATION = "kdeconnect.notification"
PACKET_TYPE_FINDMYPHONE_REQUEST = "kdeconnect.findmyphone.request"
PACKET_TYPE_LOCK = "kdeconnect.lock"
PACKET_TYPE_LOCK_REQUEST = "kdeconnect.lock.request"
PACKET_TYPE_MOUSEPAD_REQUEST = "kdeconnect.mousepad.request"
PACKET_TYPE_MOUSEPAD_KEYBOARDSTATE = "kdeconnect.mousepad.keyboardstate"
PACKET_TYPE_MPRIS = "kdeconnect.mpris"
PACKET_TYPE_MPRIS_REQUEST = "kdeconnect.mpris.request"
PACKET_TYPE_SYSTEMVOLUME = "kdeconnect.systemvolume"
PACKET_TYPE_SYSTEMVOLUME_REQUEST = "kdeconnect.systemvolume.request"

# "specialKey" codes of the mousepad plugin; the same on every platform.
SPECIAL_KEYS: dict[str, int] = {
    "backspace": 1,
    "tab": 2,
    "left": 4,
    "up": 5,
    "right": 6,
    "down": 7,
    "page_up": 8,
    "page_down": 9,
    "home_key": 10,
    "end": 11,
    "enter": 12,
    "delete": 13,
    "escape": 14,
    "super": 20,
    **{f"f{number}": 20 + number for number in range(1, 13)},
}

DEVICE_TYPES = ("desktop", "laptop", "phone", "tablet", "tv")

_DEVICE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{32,38}$")
_INVALID_NAME_CHARS_RE = re.compile(r"[\"',;:.!?()\[\]<>]")


class ProtocolError(Exception):
    """Raised when a peer sends something we cannot accept."""


@dataclass(slots=True)
class Packet:
    """A single KDE Connect network packet."""

    type: str
    body: dict[str, Any] = field(default_factory=dict)

    def serialize(self) -> bytes:
        """Return the packet as a newline terminated JSON line."""
        data = {"id": int(time.time() * 1000), "type": self.type, "body": self.body}
        return json.dumps(data, separators=(",", ":")).encode() + b"\n"

    @classmethod
    def parse(cls, line: bytes) -> Packet:
        """Parse a JSON line received from a peer."""
        try:
            data = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise ProtocolError("Packet is not valid JSON") from err
        if not isinstance(data, dict) or not isinstance(data.get("type"), str):
            raise ProtocolError("Packet has no type")
        body = data.get("body")
        return cls(data["type"], body if isinstance(body, dict) else {})


def is_valid_device_id(device_id: Any) -> bool:
    """Return whether a device id follows the KDE Connect rules."""
    return isinstance(device_id, str) and _DEVICE_ID_RE.match(device_id) is not None


def filter_device_name(name: Any) -> str:
    """Strip the characters KDE Connect does not allow in device names."""
    if not isinstance(name, str):
        return ""
    return _INVALID_NAME_CHARS_RE.sub("", name).strip()[:32]


@dataclass(slots=True)
class DeviceInfo:
    """What a peer told us about itself."""

    device_id: str
    name: str
    device_type: str = "unknown"
    protocol_version: int = 0
    incoming_capabilities: frozenset[str] = frozenset()
    outgoing_capabilities: frozenset[str] = frozenset()
    host: str | None = None
    tcp_port: int | None = None

    @classmethod
    def from_identity(cls, packet: Packet, host: str | None = None) -> DeviceInfo:
        """Build device info from an identity packet."""
        if packet.type != PACKET_TYPE_IDENTITY:
            raise ProtocolError(f"Expected an identity packet, got {packet.type}")
        body = packet.body
        device_id = body.get("deviceId")
        if not is_valid_device_id(device_id):
            raise ProtocolError("Identity packet has an invalid device id")
        version = body.get("protocolVersion")
        tcp_port = body.get("tcpPort")
        return cls(
            device_id=device_id,
            name=filter_device_name(body.get("deviceName")) or device_id,
            device_type=str(body.get("deviceType") or "unknown"),
            protocol_version=version if isinstance(version, int) else 0,
            incoming_capabilities=frozenset(
                _str_list(body.get("incomingCapabilities"))
            ),
            outgoing_capabilities=frozenset(
                _str_list(body.get("outgoingCapabilities"))
            ),
            host=host,
            tcp_port=tcp_port if isinstance(tcp_port, int) else None,
        )

    def merge(self, other: DeviceInfo) -> None:
        """Take over the fields a later identity packet filled in."""
        self.name = other.name
        if other.device_type != "unknown":
            self.device_type = other.device_type
        if other.protocol_version:
            self.protocol_version = other.protocol_version
        if other.incoming_capabilities or other.outgoing_capabilities:
            self.incoming_capabilities = other.incoming_capabilities
            self.outgoing_capabilities = other.outgoing_capabilities
        if other.host:
            self.host = other.host
        if other.tcp_port:
            self.tcp_port = other.tcp_port


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


@dataclass(slots=True)
class Identity:
    """Our own KDE Connect identity."""

    device_id: str
    name: str
    certificate_pem: str
    private_key_pem: str
    device_type: str = "desktop"

    @property
    def certificate_der(self) -> bytes:
        """Return our certificate in DER form."""
        return pem_to_der(self.certificate_pem)

    def identity_packet(
        self,
        incoming: list[str],
        outgoing: list[str],
        tcp_port: int | None = None,
    ) -> Packet:
        """Return the identity packet we announce."""
        body: dict[str, Any] = {
            "deviceId": self.device_id,
            "deviceName": self.name,
            "deviceType": self.device_type,
            "protocolVersion": PROTOCOL_VERSION,
            "incomingCapabilities": incoming,
            "outgoingCapabilities": outgoing,
        }
        if tcp_port is not None:
            body["tcpPort"] = tcp_port
        return Packet(PACKET_TYPE_IDENTITY, body)


def generate_identity(name: str) -> Identity:
    """Create a new device id with a self-signed certificate.

    This generates an RSA key, so run it in an executor.
    """
    device_id = uuid.uuid4().hex
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, device_id),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "KDE Connect"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "KDE"),
        ]
    )
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(10)
        .not_valid_before(now - datetime.timedelta(days=365))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    return Identity(
        device_id=device_id,
        name=filter_device_name(name) or "Home Assistant",
        certificate_pem=certificate.public_bytes(serialization.Encoding.PEM).decode(),
        private_key_pem=key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
    )


def pem_to_der(pem: str) -> bytes:
    """Convert a PEM certificate to DER."""
    return x509.load_pem_x509_certificate(pem.encode()).public_bytes(
        serialization.Encoding.DER
    )


def der_to_pem(der: bytes) -> str:
    """Convert a DER certificate to PEM."""
    return (
        x509.load_der_x509_certificate(der)
        .public_bytes(serialization.Encoding.PEM)
        .decode()
    )


def certificate_common_name(der: bytes) -> str | None:
    """Return the common name, which KDE Connect sets to the device id."""
    names = x509.load_der_x509_certificate(der).subject.get_attributes_for_oid(
        NameOID.COMMON_NAME
    )
    return str(names[0].value) if names else None


def certificate_fingerprint(der: bytes) -> str:
    """Return the SHA-256 fingerprint the way KDE Connect shows it."""
    digest = hashlib.sha256(der).hexdigest()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def verification_key(own_der: bytes, peer_der: bytes, timestamp: int | None) -> str:
    """Return the key both devices show while pairing.

    Protocol 8 mixes in the pairing timestamp; older peers do not.
    """
    keys = sorted((_public_key_der(own_der), _public_key_der(peer_der)), reverse=True)
    digest = hashlib.sha256(keys[0] + keys[1])
    if timestamp is not None:
        digest.update(str(timestamp).encode())
    return digest.hexdigest()[:8].upper()


def _public_key_der(cert_der: bytes) -> bytes:
    return (
        x509.load_der_x509_certificate(cert_der)
        .public_key()
        .public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
