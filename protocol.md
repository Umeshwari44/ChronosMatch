# ChronosMatch Protocol Specification

Author: Umeshwari B

Version 1 · All multi-byte fields are **little-endian** · Prices are **integer cents**

## 1. Order event record (48 bytes)

Python format string: `"<QQQqIIBBHI"` (`struct.calcsize == 48`)

| Offset | Size | Type | Field | Description |
|-------:|-----:|------|-------|-------------|
| 0  | 8 | uint64 | `sequence`     | Monotonic slot counter, starts at 0, increases by 1 per event |
| 8  | 8 | uint64 | `order_id`     | Unique order identifier |
| 16 | 8 | uint64 | `timestamp_ns` | Producer timestamp from a monotonic clock (`time.monotonic_ns`) |
| 24 | 8 | int64  | `price_cents`  | Limit price in integer cents (10000 = 100.00) |
| 32 | 4 | uint32 | `quantity`     | Order size in units |
| 36 | 4 | uint32 | `symbol_id`    | Numeric instrument identifier |
| 40 | 1 | uint8  | `side`         | `0` = BUY, `1` = SELL |
| 41 | 1 | uint8  | `order_type`   | `0` = LIMIT (other values reserved) |
| 42 | 2 | uint16 | `flags`        | Reserved, must be `0` in version 1 |
| 44 | 4 | uint32 | `checksum`     | CRC-32 of bytes 0 to 43 |

Total: **48 bytes**, with no padding between fields.

### Validation rules

A decoder rejects a record when any of these is true:

1. `checksum` does not match the CRC-32 of bytes 0 to 43.
2. `side` is not 0 or 1.
3. `quantity` is 0.
4. `price_cents` is not positive.
5. `sequence` is not exactly one greater than the previous record's (gap or reorder detected).

## 2. Ring buffer layout

The ring buffer is a file-backed memory map made of a 64-byte header followed by `capacity` slots of 48 bytes each.

| Offset | Size | Type | Field | Description |
|-------:|-----:|------|-------|-------------|
| 0  | 4 | bytes  | `magic`     | ASCII `CHRM`, rejected on mismatch |
| 4  | 4 | uint32 | `version`   | Protocol version (1) |
| 8  | 4 | uint32 | `capacity`  | Number of slots |
| 12 | 4 | uint32 | `slot_size` | Bytes per slot (48) |
| 16 | 8 | uint64 | `head`      | Next slot to write; written **only by the producer** |
| 24 | 8 | -      | reserved    | |
| 32 | 8 | uint64 | `tail`      | Next slot to read; written **only by the consumer** |
| 40 | 24 | -     | reserved    | Pads the header to 64 bytes |

Slot `n` starts at byte offset `64 + (n mod capacity) * 48`.

### Protocol

- **Producer:** if `head - tail >= capacity` the ring is full, so the producer yields and retries (backpressure). Otherwise it writes the 48-byte record into slot `head mod capacity`, then publishes it by advancing `head`.
- **Consumer:** if `tail >= head` the ring is empty. Otherwise it reads slot `tail mod capacity`, validates it, then advances `tail`.
- Because each index has a single writer, the producer never overwrites a slot the consumer has not read.
- Index updates are guarded by a process-shared lock in the Python prototype. A production version would use atomic loads and stores with the correct memory ordering instead.
