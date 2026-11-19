import pytest
from chronosmatch import record


def make(**over):
    buf = bytearray(record.SIZE)
    args = dict(sequence=0, order_id=7, timestamp_ns=123, price_cents=10025,
                quantity=10, symbol_id=1, side=record.BUY)
    args.update(over)
    record.encode_into(buf, 0, **args)
    return buf


def test_size_is_48_bytes():
    assert record.SIZE == 48


def test_round_trip():
    o = record.decode(make(), 0, expected_sequence=0)
    assert (o.order_id, o.price_cents, o.quantity, o.side) == (7, 10025, 10, record.BUY)


def test_checksum_detects_corruption():
    buf = make()
    buf[25] ^= 0xFF
    with pytest.raises(record.InvalidRecord, match="checksum"):
        record.decode(buf)


def test_rejects_bad_side_zero_qty_bad_price():
    with pytest.raises(record.InvalidRecord, match="side"):
        record.decode(make(side=5))
    with pytest.raises(record.InvalidRecord, match="quantity"):
        record.decode(make(quantity=0))
    with pytest.raises(record.InvalidRecord, match="price"):
        record.decode(make(price_cents=0))


def test_sequence_gap_detected():
    with pytest.raises(record.InvalidRecord, match="sequence"):
        record.decode(make(sequence=5), 0, expected_sequence=4)
