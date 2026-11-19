from chronosmatch.matcher_py import PyMatcher


def test_crossing_orders_trade_at_resting_price():
    m = PyMatcher()
    assert m.process(101, 10000, 10, False)[0] is False
    assert m.process(202, 10050, 10, True) == (True, 10000, 10, 202, 101)


def test_non_crossing_orders_rest():
    m = PyMatcher()
    m.process(1, 10100, 5, False)
    assert m.process(2, 10000, 5, True)[0] is False
    assert m.top_of_book() == (10000, 10100)


def test_partial_fill_leaves_remainder():
    m = PyMatcher()
    m.process(1, 10000, 10, False)
    assert m.process(2, 10000, 4, True) == (True, 10000, 4, 2, 1)
    assert m.process(3, 10000, 10, True) == (True, 10000, 6, 3, 1)
    assert m.top_of_book()[1] is None


def test_zero_quantity_ignored():
    assert PyMatcher().process(1, 10000, 0, True)[0] is False
