# ChronosMatch Benchmark Results

Author: Umeshwari B

## Test setup

| Item | Value |
|------|-------|
| CPU | Intel Xeon @ 2.10 GHz (cloud VM), 2 vCPU |
| Memory | 8 GB |
| OS | Linux 6.18, x86_64 |
| Python | 3.13 |
| Topology | 2 processes: 1 producer, 1 consumer |
| Transport | File-backed `mmap` ring buffer, 8,192 slots, 48-byte records |
| Synchronisation | Process-shared `multiprocessing.Lock` around index updates |
| Timing | `time.monotonic_ns` (system-wide monotonic clock) |
| Verification | Consumer checks CRC-32 and sequence continuity on every record |

Script: `tools/bench_ipc.py` (run with `N` and `RATE` environment variables).
Each figure is the **median of 5 runs**. Latency is **end-to-end**: from the producer's timestamp inside the record to the moment the consumer has read it.

> These numbers come from a shared 2-vCPU cloud VM, not dedicated hardware. Both processes busy-poll, so they compete with the OS for the only two cores. Re-run on your own machine and add a row to the table at the bottom.

## Results

### 1. Saturated throughput (producer as fast as possible, 200,000 events per run)

| Metric | Result |
|--------|-------:|
| Throughput (median) | **~482,000 events/s** |
| Range across 5 runs | 322,000 to 520,000 events/s |
| Corrupt or out-of-order records | 0 |

At saturation the ring fills up and events wait in the queue, so latency here mostly measures queueing, not transport cost (median 3.3 us, p95 6.9 ms, p99 9.5 ms). Use the paced runs below for latency.

### 2. Paced latency (producer at a fixed offered rate, 100,000 events per run)

| Offered rate | p50 | p95 | p99 | Corrupt / out-of-order |
|-------------:|----:|----:|----:|-----------------------:|
| 20,000 events/s | 1.9 us | 6.0 us | 494 us | 0 |
| 50,000 events/s | 1.5 us | 10.7 us | 1.78 ms | 0 |

## Interpretation

- **Throughput target (100,000 events/s):** met by a wide margin on this VM (about 4.8x), with every record validated.
- **Typical latency:** a few microseconds at p50, well under 50 us.
- **Tail latency (p99):** does **not** meet a 50 us target on this VM. The occasional millisecond-scale delays are consistent with operating-system scheduling on shared vCPUs, though this was not isolated with profiling. A dedicated machine, CPU pinning, and moving index updates out of Python are the next steps.
- These results measure the IPC path only. They do not include the matching engine's own cost.

## Reproducing

```bash
# saturated throughput
N=200000 python tools/bench_ipc.py
# paced latency
N=100000 RATE=50000 python tools/bench_ipc.py
```

## Add your own hardware

| Machine | CPU / cores | RAM | OS | Python | Throughput (events/s) | p50 | p95 | p99 |
|---------|-------------|-----|----|--------|----------------------:|----:|----:|----:|
| Cloud VM (above) | Xeon 2.1 GHz / 2 vCPU | 8 GB | Linux 6.18 | 3.13 | ~482,000 | 1.5 us | 10.7 us | 1.78 ms |
| *your laptop* | | | | | | | | |
