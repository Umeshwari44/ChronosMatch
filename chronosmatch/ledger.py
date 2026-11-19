"""Asynchronous SQLite audit writer for matched trades.

The matching process submits compact trade tuples to a dedicated background
process. SQLite I/O and commits therefore stay off the matching hot path.
The order-ingress IPC path remains the mmap binary ring; this audit queue is a
separate persistence channel and is not used to transport incoming orders.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import queue
import sqlite3
import time
from typing import Optional


_STOP = None


def _ledger_worker(db_path: str, trade_queue) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                buy_order_id INTEGER NOT NULL,
                sell_order_id INTEGER NOT NULL,
                price_cents INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                order_timestamp_ns INTEGER NOT NULL,
                engine_enter_ns INTEGER NOT NULL,
                engine_exit_ns INTEGER NOT NULL,
                engine_latency_ns INTEGER NOT NULL,
                end_to_end_latency_ns INTEGER NOT NULL,
                recorded_at_ns INTEGER NOT NULL
            )
        """)
        conn.commit()
        batch = []
        stopping = False
        while not stopping:
            try:
                item = trade_queue.get(timeout=0.25)
                if item is _STOP:
                    stopping = True
                else:
                    batch.append(item)
            except queue.Empty:
                pass
            if batch and (len(batch) >= 250 or stopping):
                conn.executemany("""
                    INSERT INTO trades (
                        buy_order_id, sell_order_id, price_cents, quantity,
                        order_timestamp_ns, engine_enter_ns, engine_exit_ns,
                        engine_latency_ns, end_to_end_latency_ns, recorded_at_ns
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch.clear()
        if batch:
            conn.executemany("""
                INSERT INTO trades (
                    buy_order_id, sell_order_id, price_cents, quantity,
                    order_timestamp_ns, engine_enter_ns, engine_exit_ns,
                    engine_latency_ns, end_to_end_latency_ns, recorded_at_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
    finally:
        conn.close()


class TradeLedger:
    """Non-blocking trade submission with a dedicated SQLite writer process."""

    def __init__(self, db_path: str = "chronosmatch.db", max_queue: int = 100_000):
        self.db_path = db_path
        self._queue = mp.Queue(maxsize=max_queue)
        self._worker = mp.Process(
            target=_ledger_worker, args=(db_path, self._queue),
            name="chronosmatch-ledger", daemon=True,
        )
        self._closed = False
        self._worker.start()

    def submit(self, buy_order_id: int, sell_order_id: int, price_cents: int,
               quantity: int, order_timestamp_ns: int, engine_enter_ns: int,
               engine_exit_ns: int) -> None:
        if self._closed:
            raise RuntimeError("trade ledger is closed")
        self._queue.put((int(buy_order_id), int(sell_order_id), int(price_cents),
                         int(quantity), int(order_timestamp_ns),
                         int(engine_enter_ns), int(engine_exit_ns),
                         int(engine_exit_ns - engine_enter_ns),
                         int(engine_exit_ns - order_timestamp_ns),
                         time.time_ns()))

    def close(self, timeout: Optional[float] = 30.0) -> None:
        if self._closed:
            return
        self._closed = True
        self._queue.put(_STOP)
        self._worker.join(timeout)
        if self._worker.is_alive():
            self._worker.terminate()
            self._worker.join()
            raise TimeoutError("SQLite ledger worker did not shut down cleanly")
        self._queue.close()
        self._queue.join_thread()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
