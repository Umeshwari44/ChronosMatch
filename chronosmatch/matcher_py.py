"""Pure-Python reference matcher (top-of-book). Same behaviour as matching_engine.pyx.

Used as a fallback when the Cython extension has not been built, and as the
reference the Cython version is checked against.
"""


class PyMatcher:
    def __init__(self):
        self.best_bid = self.best_ask = None      # (price, order_id, qty)

    def process(self, order_id, price_cents, quantity, is_buy):
        """Returns (traded, price_cents, quantity, buy_id, sell_id)."""
        if quantity <= 0:
            return (False, 0, 0, 0, 0)
        if is_buy:
            if self.best_ask and price_cents >= self.best_ask[0]:
                px, sid, qty = self.best_ask
                filled = min(quantity, qty)
                self.best_ask = (px, sid, qty - filled) if qty - filled else None
                return (True, px, filled, order_id, sid)
            self.best_bid = (price_cents, order_id, quantity)
        else:
            if self.best_bid and price_cents <= self.best_bid[0]:
                px, bid, qty = self.best_bid
                filled = min(quantity, qty)
                self.best_bid = (px, bid, qty - filled) if qty - filled else None
                return (True, px, filled, bid, order_id)
            self.best_ask = (price_cents, order_id, quantity)
        return (False, 0, 0, 0, 0)

    def top_of_book(self):
        return (self.best_bid[0] if self.best_bid else None,
                self.best_ask[0] if self.best_ask else None)
