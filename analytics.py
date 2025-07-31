# Utility functions for order book analytics
import time
from collections import deque

# Track order flow dynamics
order_flow_stats = {
    'new_orders': 0,
    'cancellations': 0,
    'executions': 0
}

# Track recent large orders to detect spoofing
recent_orders = deque(maxlen=100)
SPOOF_SIZE_THRESHOLD = 1000  # quantity threshold
CANCEL_WINDOW_SECONDS = 2

def update_order_flow(old_qty, new_qty):
    """Update order flow metrics based on quantity change."""
    if new_qty > old_qty:
        order_flow_stats['new_orders'] += new_qty - old_qty
    elif new_qty < old_qty:
        order_flow_stats['cancellations'] += old_qty - new_qty
        # treat remaining qty decrease as execution
        order_flow_stats['executions'] += old_qty - new_qty

def record_large_order(price, qty, side, timestamp):
    """Store large orders to monitor potential spoofing."""
    if qty >= SPOOF_SIZE_THRESHOLD:
        recent_orders.append({'price': price, 'qty': qty, 'side': side, 'time': timestamp})

def detect_spoofing(price, qty, side, timestamp):
    """Check if a large order was cancelled quickly."""
    suspicious = False
    for order in list(recent_orders):
        if (order['side'] == side and order['price'] == price and
                timestamp - order['time'] <= CANCEL_WINDOW_SECONDS and
                qty < order['qty'] * 0.2):
            suspicious = True
    return suspicious

def largest_order(bids, asks):
    """Return the largest bid and ask orders."""
    max_bid = max(bids, key=lambda x: x['qty']) if bids else None
    max_ask = max(asks, key=lambda x: x['qty']) if asks else None
    return max_bid, max_ask

def spread_opportunity(best_bid, best_ask):
    """Return True if spread exceeds transaction cost."""
    if not best_bid or not best_ask:
        return False, 0.0
    spread = best_ask['price'] - best_bid['price']
    mid = (best_ask['price'] + best_bid['price']) / 2
    if mid == 0:
        return False, 0.0
    bps = (spread / mid) * 10000
    return bps > 0.06, bps
