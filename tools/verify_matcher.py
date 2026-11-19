"""Checks the matcher on crossing orders. Uses the Cython build if present.

Run from the project root:  python tools/verify_matcher.py
"""
import sys
sys.path.insert(0, ".")

try:
    from chronosmatch.matching_engine import CythonMatcher as Matcher
    print("engine: cython")
except ImportError:
    from chronosmatch.matcher_py import PyMatcher as Matcher
    print("engine: python fallback (Cython extension not built)")

m = Matcher()
print("resting SELL :", m.process(101, 10000, 10, False))
print("crossing BUY :", m.process(202, 10000, 10, True))
assert m.process(303, 9900, 5, True)[0] is False, "non-crossing buy must not trade"
print("expected     : trade=True, price=10000, qty=10, buy=202, sell=101")
