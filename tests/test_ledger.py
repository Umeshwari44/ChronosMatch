import sqlite3

from chronosmatch.ledger import TradeLedger


def test_trade_ledger_flushes_records_to_sqlite(tmp_path):
    db_path = str(tmp_path / "audit.db")
    with TradeLedger(db_path) as ledger:
        ledger.submit(202, 101, 10000, 5, 1_000_000, 1_000_100, 1_000_250)
        ledger.submit(203, 102, 10025, 2, 2_000_000, 2_000_100, 2_000_300)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT buy_order_id, sell_order_id, price_cents, quantity, "
            "engine_latency_ns, end_to_end_latency_ns FROM trades ORDER BY trade_id"
        ).fetchall()

    assert rows == [
        (202, 101, 10000, 5, 150, 250),
        (203, 102, 10025, 2, 200, 300),
    ]
