# ChronosMatch Architecture

Author: Umeshwari B

## 1. System topology

```
 Process A (producer)                         Process B (consumer)
 ┌──────────────────────┐   shared file    ┌────────────────────────────┐
 │ asyncio simulator    │  (memory-mapped) │ consumer loop              │
 │  - random orders     │ ───────────────► │  - pop + validate record   │
 │  - encodes 48-byte   │   ring buffer    │  - matcher (Cython/Python) │
 │    records           │   head / tail    │  - throughput statistics   │
 └──────────────────────┘                  └────────────────────────────┘
                                                        ▲
                                  Process C (optional): curses monitor
                                  (read-only view of head, depth, rate)
```

The two main processes never exchange Python objects. They share one memory-mapped file and agree on a binary layout (see `protocol.md`).

## 2. Components

| Module | Responsibility |
|--------|----------------|
| `record.py` | Defines the 48-byte layout; encodes, decodes and validates records (checksum, side, quantity, price, sequence). |
| `ring.py` | Memory-mapped SPSC ring buffer: header, slots, `push` with backpressure, `pop` with validation. |
| `simulator.py` | asyncio producer that generates random buy and sell orders and pushes them into the ring. |
| `consumer.py` | Pops orders, feeds the matcher, reports throughput. Picks the Cython matcher when built, otherwise the Python one. |
| `matching_engine.pyx` | Compiled top-of-book matcher using C-typed state and a C struct for trades. |
| `matcher_py.py` | Pure-Python reference matcher with identical behaviour; fallback and test oracle. |
| `monitor.py` | curses display of produced events, buffer depth and produce rate. Does not consume events. |

## 3. Data flow for one order

1. The simulator builds an order and calls `ring.push(...)`.
2. `push` checks for space. If the ring is full it returns `False` and the simulator yields and retries (backpressure).
3. The record is written into slot `head mod capacity` with its CRC-32, then `head` is advanced to publish it.
4. The consumer sees `tail < head`, reads the slot, validates it, and advances `tail`.
5. The order goes to the matcher. A crossing order produces a trade tuple `(traded, price, quantity, buy_id, sell_id)`.

## 4. Concurrency model

- One producer and one consumer only (SPSC).
- `head` is written only by the producer; `tail` only by the consumer. This is why the producer can never overwrite an unread slot.
- A lock guards index reads and writes in the Python prototype. Python has no portable atomics, so a production version would move this into native code.
- Records are validated on every read, so a torn or corrupted slot is detected rather than silently matched.

## 5. Key design decisions

| Decision | Reason |
|----------|--------|
| Fixed 48-byte binary record | Known size, no encode/decode of text or objects, easy to index. |
| Integer cents for price | Avoids floating-point rounding errors. |
| CRC-32 and sequence number | Detects corruption, gaps and reordering. |
| Pure-Python fallback matcher | Lets the project run and be tested without a C compiler. |
| Top-of-book matcher | Keeps the first version simple and verifiable. |

## 6. Known limits and extension points

- Replace the lock with atomic head/tail updates in native code.
- Replace the top-of-book matcher with per-price FIFO queues, cancel and replace.
- Add per-record timestamps at the consumer for full pipeline latency, including matching.
- Add risk checks and crash recovery.
