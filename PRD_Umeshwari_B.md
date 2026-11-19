# Product Requirements Document: ChronosMatch

| Item | Detail |
|------|--------|
| Product | ChronosMatch: Zero-Copy High-Frequency Trading Engine |
| Author | Umeshwari B |
| Organization | Infotact Solutions, Python Development internship |
| Role | Data Associate L1 Intern |
| Project Ref | ITS/PY/1102 |
| Project window | 10 October 2026 to 10 November 2026 |
| Status | Prototype, mid-project review on 03 November 2026 |

## 1. Purpose

Build an educational low-latency trading-engine prototype that moves order events between processes as fixed-width binary records, matches crossing orders, and reports honest performance measurements. The project gives practical exposure to Python backend work: efficient algorithms, inter-process communication, compiled extensions, testing and documentation.

## 2. Problem statement

Trading systems must handle large streams of market events with low and predictable delay. Passing Python objects between processes through JSON or Pickle adds encoding, copying and decoding work to every event, and the Python runtime adds unpredictable pauses. This project explores an alternative: binary records in shared memory and a compiled matching core.

## 3. Goals

1. Move order events between two processes without JSON or Pickle.
2. Match crossing buy and sell orders correctly.
3. Generate realistic bursts of synthetic orders.
4. Show live activity in a terminal monitor.
5. Measure throughput and latency, and record the hardware used.

## 4. Non-goals

- A production exchange, real market connectivity or real money.
- A full multi-level order book with cancel and replace (future work).
- Multiple producers or consumers (the ring buffer is SPSC).

## 5. Users and use case

**User:** an analyst or student studying low-latency system design.
**Use case:** simulate a burst of buy and sell orders after an earnings announcement, push them through shared memory, match them, and watch throughput and buffer depth live.

## 6. Functional requirements

| ID | Requirement |
|----|-------------|
| F1 | Orders are encoded as 48-byte little-endian records with sequence, order ID, timestamp, price in integer cents, quantity, symbol, side, type, flags and CRC-32. |
| F2 | A file-backed memory-mapped ring buffer carries records from one producer process to one consumer process. |
| F3 | When the ring is full the producer waits and retries; no unread record is ever overwritten. |
| F4 | The consumer rejects records with a bad checksum, bad side, zero quantity, non-positive price or a sequence gap. |
| F5 | A buy at or above the resting ask, or a sell at or below the resting bid, produces a trade at the resting order's price, with partial fills. |
| F6 | An asyncio simulator produces synthetic random orders at configurable volume. |
| F7 | A curses monitor shows events produced, buffer depth and produce rate. |
| F8 | A benchmark tool reports throughput and latency percentiles. |

## 7. Non-functional requirements and targets

| Target | Status |
|--------|--------|
| 100,000 orders per second through the IPC path | Met on the test VM for the ring buffer path (see `docs/benchmark-results.md`) |
| Under 50 microseconds typical latency | p50 met; p99 not met on a shared VM |
| No JSON or Pickle on the event path | Met |
| Core logic covered by automated tests | Record, ring buffer, matcher and two-process pipeline tests |

Targets are verified by measurement, not assumed.

## 8. Architecture summary

asyncio simulator, then memory-mapped ring buffer of 48-byte records, then consumer, then matcher (Cython, with a Python fallback), then statistics and monitor. Details are in `docs/architecture.md`; the wire format is in `docs/protocol.md`.

## 9. Development plan

| Stage | Work |
|-------|------|
| Week 1 | Memory-mapped ring buffer with `mmap` and `struct`; binary record format; asyncio order generator; producer rate measurement. |
| Week 2 | Cython matching engine with C types; consumer integration; curses monitor. |
| Mid-project review | IPC audit (no JSON or Pickle), engine verification with crossing orders, benchmark methodology and results. |
| Final | Documentation, report, presentation and demonstration. |

## 10. Deliverables

Source code, project documentation, project report, presentation (PPT), benchmark and evaluation results, and a final demonstration.

## 11. Acceptance criteria

1. `pytest` passes.
2. `python tools/verify_matcher.py` shows a trade at 10000 cents, quantity 10, buy 202, sell 101.
3. `python tools/run_demo.py` completes with all orders consumed.
4. Benchmark results are recorded with hardware details.
5. Limitations are stated plainly in the documentation.

## 12. Risks

| Risk | Mitigation |
|------|------------|
| No C compiler available for Cython | Pure-Python fallback matcher |
| Python lock limits throughput and adds jitter | Documented; native atomics listed as future work |
| Shared or busy machine inflates tail latency | Record hardware; use paced runs; consider CPU pinning |
| Overstating results | Report only measured figures with test conditions |
