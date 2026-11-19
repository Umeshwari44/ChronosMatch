"""48-byte binary order record: encode, decode and validate.

Layout (little-endian, see docs/protocol.md):
    0  u64 sequence      8  u64 order_id     16 u64 timestamp_ns
    24 i64 price_cents   32 u32 quantity     36 u32 symbol_id
    40 u8  side          41 u8  order_type   42 u16 flags
    44 u32 checksum (CRC-32 of bytes 0..43)
"""
import struct
import zlib
from typing import NamedTuple, Optional

RECORD = struct.Struct("<QQQqIIBBHI")
SIZE = RECORD.size  # 48
BODY = 44           # bytes covered by the checksum
BUY, SELL = 0, 1


class InvalidRecord(ValueError):
    """Raised when a record fails validation."""


class Order(NamedTuple):
    sequence: int
    order_id: int
    timestamp_ns: int
    price_cents: int
    quantity: int
    symbol_id: int
    side: int
    order_type: int
    flags: int
    checksum: int


def encode_into(buf, offset, sequence, order_id, timestamp_ns, price_cents,
                quantity, symbol_id, side, order_type=0, flags=0):
    """Write one record into `buf` at `offset` and stamp its checksum."""
    RECORD.pack_into(buf, offset, sequence, order_id, timestamp_ns, price_cents,
                     quantity, symbol_id, side, order_type, flags, 0)
    crc = zlib.crc32(bytes(buf[offset:offset + BODY]))
    struct.pack_into("<I", buf, offset + BODY, crc)


def decode(buf, offset=0, expected_sequence: Optional[int] = None) -> Order:
    """Read and validate one record. Raises InvalidRecord on any violation."""
    order = Order(*RECORD.unpack_from(buf, offset))
    if zlib.crc32(bytes(buf[offset:offset + BODY])) != order.checksum:
        raise InvalidRecord("checksum mismatch")
    if order.side not in (BUY, SELL):
        raise InvalidRecord(f"bad side {order.side}")
    if order.quantity == 0:
        raise InvalidRecord("zero quantity")
    if order.price_cents <= 0:
        raise InvalidRecord("non-positive price")
    if expected_sequence is not None and order.sequence != expected_sequence:
        raise InvalidRecord(f"sequence gap: expected {expected_sequence}, got {order.sequence}")
    return order
