"""Terminal monitor for ring-buffer activity and recent audited executions.

Run in a real terminal. On Windows, use WSL or install the windows-curses
package in the active virtual environment.
"""
import argparse
import curses
import sqlite3
import time

from .ring import MMapRing


def _latest_trade(db_path):
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.1)
        try:
            return conn.execute(
                "SELECT buy_order_id, sell_order_id, price_cents, quantity, "
                "engine_latency_ns FROM trades ORDER BY trade_id DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return None


def run(stdscr, path="chronosmatch.ipc", db_path="chronosmatch.db", whale_qty=1000):
    curses.curs_set(0)
    ring = MMapRing(path, create=False)
    last_head, last_t, rate = 0, time.perf_counter(), 0.0
    last_trade = None
    last_db_check = 0.0
    try:
        while True:
            head, depth = ring._head(), len(ring)
            now = time.perf_counter()
            if now - last_t >= 0.5:
                rate = (head - last_head) / (now - last_t)
                last_head, last_t = head, now
            if now - last_db_check >= 0.5:
                last_trade = _latest_trade(db_path)
                last_db_check = now
            stdscr.erase()
            stdscr.addstr(0, 0, "ChronosMatch | Low-Latency Trading Monitor")
            stdscr.addstr(2, 0, f"Events produced : {head:,}")
            stdscr.addstr(3, 0, f"Buffer depth    : {depth:,} / {ring.capacity:,}")
            stdscr.addstr(4, 0, f"Produce rate    : {rate:,.0f} orders/s")
            stdscr.addstr(6, 0, "Latest audited execution:")
            if last_trade:
                buy_id, sell_id, price, qty, latency = last_trade
                stdscr.addstr(7, 0, f"BUY {buy_id} / SELL {sell_id} | "
                                      f"Price {price / 100:.2f} | Qty {qty} | "
                                      f"Engine {latency:,} ns")
                if qty >= whale_qty:
                    stdscr.addstr(9, 0, f"*** WHALE ORDER EXECUTED: {qty:,} units ***")
            else:
                stdscr.addstr(7, 0, "No audited trades yet (start the consumer).")
            stdscr.addstr(11, 0, "Ctrl+C to exit")
            stdscr.refresh()
            time.sleep(0.05)
    finally:
        ring.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChronosMatch terminal monitor")
    parser.add_argument("--path", default="chronosmatch.ipc")
    parser.add_argument("--db", default="chronosmatch.db")
    parser.add_argument("--whale-qty", type=int, default=1000)
    args = parser.parse_args()
    curses.wrapper(run, args.path, args.db, args.whale_qty)
