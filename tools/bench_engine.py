"""Measure matching-call latency for the Cython or Python implementation.

Examples:
    python tools/bench_engine.py --engine cython --orders 200000
    python tools/bench_engine.py --engine python --orders 200000
"""
import argparse
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_matcher(name):
    if name == "cython":
        from chronosmatch.matching_engine import CythonMatcher
        return CythonMatcher, "cython"
    if name == "python":
        from chronosmatch.matcher_py import PyMatcher
        return PyMatcher, "python"
    try:
        from chronosmatch.matching_engine import CythonMatcher
        return CythonMatcher, "cython"
    except ImportError:
        from chronosmatch.matcher_py import PyMatcher
        return PyMatcher, "python-fallback"


def percentile(sorted_values, fraction):
    return sorted_values[min(len(sorted_values) - 1, int(len(sorted_values) * fraction))]


def run_once(matcher_type, order_count):
    matcher = matcher_type()
    samples = []
    start = time.perf_counter_ns()
    trades = 0
    for index in range(order_count):
        is_buy = bool(index & 1)
        enter = time.perf_counter_ns()
        result = matcher.process(index + 1, 10_000, 1, is_buy)
        exit_ns = time.perf_counter_ns()
        samples.append(exit_ns - enter)
        trades += int(result[0])
    elapsed_ns = time.perf_counter_ns() - start
    samples.sort()
    return (order_count / (elapsed_ns / 1e9),
            percentile(samples, 0.50),
            percentile(samples, 0.95),
            percentile(samples, 0.99), trades)


def main():
    parser = argparse.ArgumentParser(description="ChronosMatch engine latency benchmark")
    parser.add_argument("--engine", choices=("auto", "cython", "python"), default="auto")
    parser.add_argument("--orders", type=int, default=200_000)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    if args.orders < 2 or args.runs < 1:
        parser.error("--orders must be at least 2 and --runs must be at least 1")

    matcher_type, engine_name = load_matcher(args.engine)
    # Warm up imports, code paths and CPU frequency before collecting samples.
    run_once(matcher_type, min(args.orders, 10_000))
    results = [run_once(matcher_type, args.orders) for _ in range(args.runs)]
    print(f"Engine: {engine_name} | runs: {args.runs}")
    print(f"Orders per run: {args.orders:,} | Trades per run: {results[-1][4]:,}")
    print(f"Median throughput: {statistics.median(row[0] for row in results):,.0f} calls/s")
    print(f"Median call latency p50: {statistics.median(row[1] for row in results):,.0f} ns")
    print(f"Median call latency p95: {statistics.median(row[2] for row in results):,.0f} ns")
    print(f"Median call latency p99: {statistics.median(row[3] for row in results):,.0f} ns")
    print("Note: single-process microbenchmark; results depend on CPU, OS and Python build.")


if __name__ == "__main__":
    main()
