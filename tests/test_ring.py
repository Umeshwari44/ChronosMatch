import pytest
from chronosmatch.ring import MMapRing
from chronosmatch.record import BUY, SELL


@pytest.fixture
def ring(tmp_path):
    r = MMapRing(str(tmp_path / "t.ipc"), capacity=4, create=True)
    yield r
    r.close()


def test_empty_pop_returns_none(ring):
    assert ring.pop() is None


def test_fifo_order(ring):
    for i in range(1, 4):
        assert ring.push(i, 1000 + i, 10000 + i, 5, BUY)
    assert [ring.pop().order_id for _ in range(3)] == [1, 2, 3]


def test_full_ring_applies_backpressure(ring):
    for i in range(4):
        assert ring.push(i + 1, 0, 10000, 1, SELL)
    assert ring.push(99, 0, 10000, 1, SELL) is False
    ring.pop()
    assert ring.push(99, 0, 10000, 1, SELL) is True


def test_wrap_around_keeps_order(ring):
    seen = []
    for i in range(1, 11):          # 10 events through 4 slots
        assert ring.push(i, 0, 10000, 1, BUY)
        seen.append(ring.pop().order_id)
    assert seen == list(range(1, 11))


def test_reopen_checks_magic(tmp_path):
    p = tmp_path / "bad.ipc"
    p.write_bytes(b"\x00" * 4096)
    with pytest.raises(ValueError):
        MMapRing(str(p), create=False)


def test_second_handle_sees_data(tmp_path):
    path = str(tmp_path / "shared.ipc")
    a = MMapRing(path, capacity=8, create=True)
    a.push(42, 1, 10100, 3, SELL)
    b = MMapRing(path, create=False)
    assert b.pop().order_id == 42
    a.close(); b.close()
