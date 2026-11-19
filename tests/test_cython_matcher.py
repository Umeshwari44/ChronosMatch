import pytest

try:
    from chronosmatch.matching_engine import CythonMatcher
except ImportError:
    CythonMatcher = None


@pytest.mark.skipif(CythonMatcher is None, reason="Cython extension is not built")
def test_cython_matcher_crosses_and_reports_resting_price():
    matcher = CythonMatcher()
    assert matcher.process(101, 10000, 8, False) == (False, 0, 0, 0, 0)
    assert matcher.process(202, 10025, 5, True) == (True, 10000, 5, 202, 101)
    assert matcher.top_of_book() == (None, 10000)
