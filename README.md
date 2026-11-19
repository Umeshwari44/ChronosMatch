# ChronosMatch: Zero-Copy High-Frequency Trading Engine

**Author:** Umeshwari B
**Programme:** Infotact Solutions, Python Development internship (Data Associate L1 Intern)
**Project Ref:** ITS/PY/1102

## 1. Project Overview

ChronosMatch is an educational low-latency trading-engine prototype. Order events move between processes as **fixed-width 48-byte binary records** in a **memory-mapped single-producer / single-consumer (SPSC) ring buffer**, so no JSON or Pickle serialization is used on the event path. A matching engine consumes the events and a terminal monitor shows activity live.

**Goals**

- Pass order events between processes without object serialization.
- Match crossing buy and sell orders (compiled Cython core, with a pure-Python reference).
- Generate synthetic order bursts with `asyncio`.
- Measure throughput and latency honestly, with the test hardware recorded.

**Pipeline**

```
asyncio simulator -> mmap ring buffer (48-byte records) -> consumer -> matcher -> stats / monitor
```

**Design notes**

- Prices are stored as integer cents to avoid floating-point rounding errors.
- Every record carries a CRC-32 and a sequence number, so corruption, gaps and reordering are detected.
- This is a learning prototype. The ring buffer uses Python `struct` calls and a lock for index updates, so it avoids serialization but is not lock-free or strictly zero-copy. The matcher is a top-of-book matcher, not a full multi-level order book.

## 2. Repository Layout

```
ChronosMatch/
├── README.md                     # Overview, layout, setup and results summary
├── requirements.txt              # Cython, setuptools, pytest
├── setup.py                      # Builds the Cython matcher extension
├── .gitignore
├── docs/
│   ├── protocol.md               # 48-byte record and ring-buffer specification
│   └── benchmark-results.md      # Measured benchmark results and hardware
├── chronosmatch/
│   ├── __init__.py               # Package marker (v0.1.0)
│   ├── record.py                 # Encode, decode and validate 48-byte records
│   ├── ring.py                   # Memory-mapped SPSC ring buffer
│   ├── matching_engine.pyx       # Cython top-of-book matcher
│   ├── matcher_py.py             # Pure-Python reference matcher / fallback
│   ├── simulator.py              # asyncio synthetic order producer
│   ├── consumer.py               # Reads the ring and feeds the matcher
│   └── monitor.py                # curses ring-buffer monitor
├── tools/
│   ├── bench_ipc.py              # Two-process IPC throughput / latency benchmark
│   ├── verify_matcher.py         # Crossing-order check for the matcher
│   └── bench_engine.py           # Cython/Python call-latency benchmark
└── tests/
    ├── test_record.py            # Record format, checksum and validation rules
    ├── test_ring.py              # FIFO, wrap-around, backpressure, reopen checks
    ├── test_matcher.py           # Matching, partial fills, resting orders
    ├── test_cython_matcher.py    # Compiled Cython engine verification
    └── test_ledger.py            # Background SQLite persistence checks
```

## 3. Setup

Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python setup.py build_ext --inplace     # optional: builds the Cython matcher
pytest -q
python tools/verify_matcher.py
```

Building the extension needs a C compiler (build-essential on Linux, Xcode tools on macOS, Microsoft C++ Build Tools on Windows). Without it, the consumer automatically uses the pure-Python matcher.

On Windows, install Microsoft C++ Build Tools before compiling the extension. For the optional terminal dashboard, run under WSL or install `windows-curses` with `pip install windows-curses`.

## 4. Running the demo

Run each command in its own terminal, from the project root. Start the producer first so it creates the ring buffer file, then start the consumer.

```bash
python -m chronosmatch.simulator
python -m chronosmatch.consumer
python -m chronosmatch.monitor --db chronosmatch.db  # live view (Linux / macOS / WSL)
```

## 5. Documentation

- [Protocol specification](docs/protocol.md)
- [Measured benchmark results](docs/benchmark-results.md)


## 6. Week 3–4 implementation

### Week 3: C-level matching and latency metrics

The Cython matcher performs its matching decision and state mutation in a
`noexcept nogil` C-level function. The Python-facing wrapper creates the result
tuple only after the GIL is reacquired. The consumer measures each matching
call with `time.perf_counter_ns()` and reports p50, p95 and p99 engine latency.
This isolates the matching decision from Python object work; it does not make
the complete Python application GIL-free or guarantee that Python GC can never
run elsewhere in the process.

### Week 4: asynchronous trade audit and Whale highlighting

`chronosmatch.ledger.TradeLedger` starts a dedicated background process that
receives completed trade summaries, batches inserts, and writes them to SQLite
using WAL mode. The order-ingress path remains the mmap binary ring. The audit
queue is a separate persistence path and may use multiprocessing serialization;
it is not used to transfer incoming market orders. The monitor reads the latest
audited execution and highlights a trade when its quantity reaches the
configurable `--whale-qty` threshold (default 1,000 units).

Run the consumer with a database path:

```bash
python -m chronosmatch.consumer --count 100000 --db chronosmatch.db
python -m chronosmatch.monitor --db chronosmatch.db --whale-qty 1000
```

The SQLite table is `trades`. It stores order IDs, execution price and size,
producer timestamp, engine-entry/exit timestamps, engine latency and
end-to-end latency. Compare the Cython and Python matching-call paths with:

```bash
python tools/bench_engine.py --engine cython --orders 200000
python tools/bench_engine.py --engine python --orders 200000
```

## 7. Remaining engineering limitations

- The matching algorithm remains a single best-bid / best-ask prototype, not a
  full multi-level Price-Time Priority order book.
- The ring-buffer synchronization is still a Python-level prototype, not a
  lock-free native atomic SPSC implementation.
- The SQLite audit queue is separate from the mmap order path; its queue payloads
  are Python objects and are not claimed to be zero-copy.
- `curses` may require WSL or `windows-curses` on Windows.
- Latency and throughput must be benchmarked on the target machine; no fixed
  sub-50-microsecond guarantee is made.
