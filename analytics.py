from collections import deque
from datetime import datetime, timedelta

# Sliding windows for HFT detection
_HFT_WINDOW_MS = 500
_HFT_MIN_MESSAGES = 10

# {ticker: deque([datetime])}
_hft_messages = {}


def record_order_book_update(ticker: str, timestamp_ns: int) -> bool:
    """Record an order book update and detect potential HFT strategic runs.

    Returns True if a strategic run (sequence of many updates within a short
    window) is detected."""
    ts = datetime.fromtimestamp(timestamp_ns / 1e9)
    q = _hft_messages.setdefault(ticker, deque())
    q.append(ts)
    cutoff = ts - timedelta(milliseconds=_HFT_WINDOW_MS)
    while q and q[0] < cutoff:
        q.popleft()
    return len(q) >= _HFT_MIN_MESSAGES


def largest_order(book: dict) -> dict | None:
    """Return the largest order in the current order book.

    The book format should follow get_full_order_book() output."""
    largest = None
    for side in ("bids", "asks"):
        for lvl in book.get(side, []):
            if lvl.get("qty", 0) <= 0:
                continue
            if not largest or lvl["qty"] > largest["qty"]:
                largest = {
                    "side": "buy" if side == "bids" else "sell",
                    "level": lvl.get("level"),
                    "price": lvl.get("price"),
                    "qty": lvl.get("qty"),
                }
    return largest

