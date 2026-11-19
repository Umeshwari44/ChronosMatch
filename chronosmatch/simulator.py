"""asyncio synthetic order producer writing into the shared ring buffer."""
import asyncio
import random
import time

from .ring import MMapRing
from .record import BUY, SELL


async def produce(path="chronosmatch.ipc", count=100_000, capacity=8192):
    ring = MMapRing(path, capacity=capacity, create=True)
    sent, started = 0, time.perf_counter_ns()
    try:
        while sent < count:
            ok = ring.push(sent + 1, time.monotonic_ns(),
                           random.randint(9_900, 10_100),
                           random.choice((1, 5, 10, 25)),
                           random.choice((BUY, SELL)))
            if ok:
                sent += 1
                if sent % 1000 == 0:
                    await asyncio.sleep(0)
            else:
                await asyncio.sleep(0)   # ring full: yield until the consumer frees slots
    finally:
        elapsed = (time.perf_counter_ns() - started) / 1e9
        ring.close()
    print(f"Produced {sent:,} orders in {elapsed:.3f}s ({sent / elapsed:,.0f} orders/s)")


if __name__ == "__main__":
    asyncio.run(produce())
