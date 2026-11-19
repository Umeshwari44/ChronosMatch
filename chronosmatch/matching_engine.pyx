# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True
"""C-level top-of-book matcher.

The matching decision and state mutation run in a noexcept nogil function.
Python tuple creation happens only after the GIL is reacquired by process().
"""

cdef struct TradeRecord:
    long long price_cents
    int quantity
    long long buy_id
    long long sell_id

cdef class CythonMatcher:
    cdef long long best_bid
    cdef long long best_ask
    cdef long long bid_id
    cdef long long ask_id
    cdef int bid_qty
    cdef int ask_qty
    cdef bint has_bid
    cdef bint has_ask

    def __cinit__(self):
        self.has_bid = False
        self.has_ask = False
        self.best_bid = self.best_ask = 0
        self.bid_qty = self.ask_qty = 0
        self.bid_id = self.ask_id = 0

    cdef int _process_nogil(self, long long order_id, long long price_cents,
                            int quantity, bint is_buy,
                            TradeRecord* trade) noexcept nogil:
        cdef int filled
        if quantity <= 0:
            return 0
        if is_buy:
            if self.has_ask and price_cents >= self.best_ask:
                filled = quantity if quantity < self.ask_qty else self.ask_qty
                trade.price_cents = self.best_ask
                trade.quantity = filled
                trade.buy_id = order_id
                trade.sell_id = self.ask_id
                self.ask_qty -= filled
                if self.ask_qty == 0:
                    self.has_ask = False
                return 1
            self.best_bid = price_cents
            self.bid_id = order_id
            self.bid_qty = quantity
            self.has_bid = True
        else:
            if self.has_bid and price_cents <= self.best_bid:
                filled = quantity if quantity < self.bid_qty else self.bid_qty
                trade.price_cents = self.best_bid
                trade.quantity = filled
                trade.buy_id = self.bid_id
                trade.sell_id = order_id
                self.bid_qty -= filled
                if self.bid_qty == 0:
                    self.has_bid = False
                return 1
            self.best_ask = price_cents
            self.ask_id = order_id
            self.ask_qty = quantity
            self.has_ask = True
        return 0

    cpdef tuple process(self, long long order_id, long long price_cents,
                        int quantity, bint is_buy):
        cdef TradeRecord trade
        cdef int traded
        with nogil:
            traded = self._process_nogil(order_id, price_cents, quantity,
                                         is_buy, &trade)
        if traded:
            return (True, trade.price_cents, trade.quantity,
                    trade.buy_id, trade.sell_id)
        return (False, 0, 0, 0, 0)

    cpdef tuple top_of_book(self):
        return (self.best_bid if self.has_bid else None,
                self.best_ask if self.has_ask else None)
