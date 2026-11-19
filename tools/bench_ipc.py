import mmap, struct, time, zlib, multiprocessing as mp, statistics, sys, os
REC = struct.Struct("<QQQqIIBBHI")          # 48 bytes
assert REC.size == 48
HDR = 64
MAGIC = b"CHRM"
CAP = 8192
N = int(os.environ.get("N","200000")); RATE = int(os.environ.get("RATE","0"))

def mk(path):
    size = HDR + CAP * 48
    with open(path, "wb") as f: f.truncate(size)
    f = open(path, "r+b"); mm = mmap.mmap(f.fileno(), size)
    struct.pack_into("<4sIII", mm, 0, MAGIC, 1, CAP, 48)   # magic, version, capacity, slot size
    struct.pack_into("<Q", mm, 16, 0); struct.pack_into("<Q", mm, 32, 0)  # head @16, tail @32
    return f, mm

def producer(path, lock, n, rate=0):
    f = open(path, "r+b"); mm = mmap.mmap(f.fileno(), 0)
    buf = bytearray(48); head = 0
    t_start = time.monotonic_ns()
    for i in range(n):
        if rate:
            due = t_start + int(i * 1e9 / rate)
            while time.monotonic_ns() < due: pass
        while True:
            with lock:
                tail = struct.unpack_from("<Q", mm, 32)[0]
                if head - tail < CAP: break
        REC.pack_into(buf, 0, head, i + 1, time.monotonic_ns(), 10000 + (i % 200), 10, 1, i & 1, 0, 0, 0)
        crc = zlib.crc32(bytes(buf[:44]))
        struct.pack_into("<I", buf, 44, crc)
        off = HDR + (head % CAP) * 48
        mm[off:off + 48] = buf
        head += 1
        struct.pack_into("<Q", mm, 16, head)

def consumer(path, lock, n, q):
    f = open(path, "r+b"); mm = mmap.mmap(f.fileno(), 0)
    tail = 0; lat = []; bad = 0; t0 = None
    while tail < n:
        head = struct.unpack_from("<Q", mm, 16)[0]
        if tail >= head: continue
        off = HDR + (tail % CAP) * 48
        rec = REC.unpack_from(mm, off)
        now = time.monotonic_ns()
        if t0 is None: t0 = now
        if zlib.crc32(mm[off:off + 44]) != rec[9]: bad += 1
        if rec[0] != tail: bad += 1
        lat.append((now - rec[2]) / 1000)
        tail += 1
        with lock:
            struct.pack_into("<Q", mm, 32, tail)
    el = (time.monotonic_ns() - t0) / 1e9
    lat.sort()
    q.put((n / el, lat[len(lat)//2], lat[int(len(lat)*.95)], lat[int(len(lat)*.99)], bad))

if __name__ == "__main__":
    path = "chronosmatch_bench.ipc"; res = []
    for r in range(5):
        f, mm = mk(path); mm.close(); f.close()
        lock = mp.Lock(); q = mp.Queue()
        c = mp.Process(target=consumer, args=(path, lock, N, q)); p = mp.Process(target=producer, args=(path, lock, N, RATE))
        c.start(); p.start(); out = q.get(); p.join(); c.join()
        res.append(out); print("run", r + 1, [round(x, 1) for x in out], flush=True)
    print("MEDIAN thr", round(statistics.median(x[0] for x in res)), "p50", statistics.median(x[1] for x in res),
          "p95", statistics.median(x[2] for x in res), "p99", statistics.median(x[3] for x in res), "bad", sum(x[4] for x in res))
