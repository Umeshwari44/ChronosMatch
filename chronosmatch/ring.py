"""File-backed memory-mapped SPSC ring buffer of 48-byte order records.

Header (64 bytes): magic(4) version(4) capacity(4) slot_size(4) head@16 tail@32.
The producer is the only writer of `head`; the consumer is the only writer of
`tail`. An optional (process-shared) lock guards the index reads/writes.
"""
import mmap
import struct
import threading

from . import record

MAGIC = b"CHRM"
VERSION = 1
HEADER_SIZE = 64
HEAD_OFF, TAIL_OFF = 16, 32
_U64 = struct.Struct("<Q")


class MMapRing:
    def __init__(self, path, capacity=8192, create=False, lock=None):
        self.capacity = capacity
        self.lock = lock or threading.Lock()
        size = HEADER_SIZE + capacity * record.SIZE
        if create:
            with open(path, "wb") as f:
                f.truncate(size)
            self._f = open(path, "r+b")
            self._mm = mmap.mmap(self._f.fileno(), size)
            struct.pack_into("<4sIII", self._mm, 0, MAGIC, VERSION, capacity, record.SIZE)
            _U64.pack_into(self._mm, HEAD_OFF, 0)
            _U64.pack_into(self._mm, TAIL_OFF, 0)
        else:
            self._f = open(path, "r+b")
            self._mm = mmap.mmap(self._f.fileno(), 0)
            magic, version, cap, slot = struct.unpack_from("<4sIII", self._mm, 0)
            if magic != MAGIC or version != VERSION or slot != record.SIZE:
                raise ValueError("not a ChronosMatch ring buffer")
            self.capacity = cap

    def _head(self):
        return _U64.unpack_from(self._mm, HEAD_OFF)[0]

    def _tail(self):
        return _U64.unpack_from(self._mm, TAIL_OFF)[0]

    def __len__(self):
        return self._head() - self._tail()

    def push(self, order_id, timestamp_ns, price_cents, quantity, side,
             symbol_id=1, order_type=0):
        """Append an order. Returns False if the ring is full (backpressure)."""
        with self.lock:
            head, tail = self._head(), self._tail()
            if head - tail >= self.capacity:
                return False
        off = HEADER_SIZE + (head % self.capacity) * record.SIZE
        record.encode_into(self._mm, off, head, order_id, timestamp_ns, price_cents,
                           quantity, symbol_id, side, order_type)
        _U64.pack_into(self._mm, HEAD_OFF, head + 1)
        return True

    def pop(self):
        """Remove and return the oldest Order, or None if the ring is empty."""
        head, tail = self._head(), self._tail()
        if tail >= head:
            return None
        off = HEADER_SIZE + (tail % self.capacity) * record.SIZE
        order = record.decode(self._mm, off, expected_sequence=tail)
        with self.lock:
            _U64.pack_into(self._mm, TAIL_OFF, tail + 1)
        return order

    def close(self):
        self._mm.close()
        self._f.close()
