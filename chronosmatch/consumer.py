"""Consumes mmap orders, matches them, and asynchronously audits executions."""
import argparse
import gc
import time

from .ring import MMapRing
from .record import BUY
from .ledger import TradeLedger

try:
    from .matching_engine import CythonMatcher as Matcher
    ENGINE = "cython"
except ImportError:
    from .matcher_py import PyMatcher as Matcher
    ENGINE = "python-fallback"


def consume(path="chronosmatch.ipc", count=100_000, db_path="chronosmatch.db"):
    ring = MMapRing(path, create=False)
    matcher = Matcher()
    processed = trades = 0
    engine_latencies = []
    started = time.perf_counter_ns()
    gc_was_enabled = gc.isenabled()
    if gc_was_enabled:
        gc.disable()
    ledger = TradeLedger(db_path)
    try:
        while processed < count:
            order = ring.pop()
            if order is None:
                time.sleep(0)
                continue
            engine_enter = time.perf_counter_ns()
            result = matcher.process(order.order_id, order.price_cents,
                                     order.quantity, order.side == BUY)
            engine_exit = time.perf_counter_ns()
            if result[0]:
                trades += 1
                engine_latencies.append(engine_exit - engine_enter)
                ledger.submit(result[3], result[4], result[1], result[2],
                              order.timestamp_ns, engine_enter, engine_exit)
            processed += 1
    finally:
        if gc_was_enabled:
            gc.enable()
        elapsed_ns = time.perf_counter_ns() - started
        ledger.close()
        ring.close()
    seconds = elapsed_ns / 1e9
    print(f"[{ENGINE}] consumed {processed:,}, trades={trades:,}, "
          f"{seconds:.3f}s, {processed / seconds:,.0f} orders/s")
    if engine_latencies:
        ordered = sorted(engine_latencies)
        p50 = ordered[len(ordered) // 2]
        p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
        p99 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))]
        print(f"Engine latency: p50={p50:,} ns, p95={p95:,} ns, p99={p99:,} ns")
    print(f"Audit database: {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChronosMatch order consumer")
    parser.add_argument("--path", default="chronosmatch.ipc")
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--db", default="chronosmatch.db")
    args = parser.parse_args()
    consume(args.path, args.count, args.db)
