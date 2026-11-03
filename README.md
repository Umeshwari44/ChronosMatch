#  "ChronosMatch": Zero-Copy High-Frequency Trading Engine 

Organization / Program: Infotact Solutions - Python Development Internship
Project Window: 10 October 2026 – 10 November 2026
Systems & Integration Lead: Umeshwari

1. Project Overview
ChronosMatch is an educational low-latency trading-engine prototype. Order events move between processes as **fixed-width 48-byte binary records** in a **memory-mapped single-producer / single-consumer (SPSC) ring buffer**, so no JSON or Pickle serialization is used on the event path. A matching engine consumes the events and a terminal monitor shows activity live.

## 2. Repository Layout
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
│   └── verify_matcher.py         # Crossing-order check for the matcher
└── tests/
    ├── test_record.py            # Record format, checksum and validation rules
    ├── test_ring.py              # FIFO, wrap-around, backpressure, reopen checks
    └── test_matcher.py           # Matching, partial fills, resting orders

3. Setup
Python 3.10 or newer.
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python setup.py build_ext --inplace     # optional: builds the Cython matcher
pytest -q
python tools/verify_matcher.py
Building the extension needs a C compiler (build-essential on Linux, Xcode tools on macOS, Microsoft C++ Build Tools on Windows). Without it, the consumer automatically uses the pure-Python matcher.

 4. Running the demo
Run each command in its own terminal, from the project root. Start the producer first so it creates the ring buffer file, then start the consumer.
python -m chronosmatch.simulator
python -m chronosmatch.consumer
python -m chronosmatch.monitor      # optional live view (Linux / macOS / WSL)

 5. Documentation
- [Protocol specification](docs/protocol.md)
- [Measured benchmark results](docs/benchmark-results.md)

 6. Limitations and future work
- Index updates use a Python lock; a production version needs atomic loads and stores in native code.
- Top-of-book matching only; full per-price FIFO queues with cancel and replace are future work.
- Cython does not remove the GIL or garbage collection by itself; the hot path would need to be isolated in `nogil` C code.
- Tail latency (p99) depends heavily on OS scheduling; dedicated cores and CPU pinning are future work.
