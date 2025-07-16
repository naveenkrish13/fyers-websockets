import os
import json
import time
import asyncio
import websockets
from flask import Flask, render_template
from flask_socketio import SocketIO
from dotenv import load_dotenv
import msg_pb2

# Load environment variables
load_dotenv()

# Configuration
FYERS_APP_ID = os.getenv('FYERS_APP_ID').strip("'")
FYERS_ACCESS_TOKEN = os.getenv('FYERS_ACCESS_TOKEN').strip("'")
WEBSOCKET_URL = "wss://rtsocket-api.fyers.in/versova"
SYMBOL = os.getenv('SYMBOL', 'NSE:NIFTY25JULFUT').strip("'")

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global order book storage for maintaining full depth
order_books = {}

def update_order_book(ticker, bids, asks, tbq, tsq, timestamp, is_snapshot):
    """Enhanced order book update with guaranteed 50-level depth maintenance"""
    global order_books
    
    if ticker not in order_books:
        # Initialize empty order book with 50 levels
        order_books[ticker] = {
            'bids': {i: {'price': 0.0, 'qty': 0, 'orders': 0, 'level': i} for i in range(50)},
            'asks': {i: {'price': 0.0, 'qty': 0, 'orders': 0, 'level': i} for i in range(50)},
            'tbq': 0,
            'tsq': 0,
            'timestamp': 0,
            'initialized': False
        }
    
    # Update total quantities and timestamp
    order_books[ticker]['tbq'] = tbq
    order_books[ticker]['tsq'] = tsq
    order_books[ticker]['timestamp'] = timestamp
    
    # Check if this is truly the first update
    first_update = not order_books[ticker].get('initialized', False)
    
    if is_snapshot or first_update:
        if first_update:
            print(f"[SNAPSHOT] FIRST UPDATE: Initializing order book for {ticker}")
            # Only reset on very first update
            for i in range(50):
                order_books[ticker]['bids'][i] = {'price': 0.0, 'qty': 0, 'orders': 0, 'level': i}
                order_books[ticker]['asks'][i] = {'price': 0.0, 'qty': 0, 'orders': 0, 'level': i}
        else:
            print(f"[SNAPSHOT] SNAPSHOT: Updating order book for {ticker}")
    else:
        print(f"[INCREMENTAL] INCREMENTAL: Updating {len(bids)} bid levels and {len(asks)} ask levels for {ticker}")
    
    # Process bid updates (same logic for both snapshot and incremental)
    for bid in bids:
        level = bid['level']
        if 0 <= level < 50:
            old_data = order_books[ticker]['bids'][level]
            
            # Enhanced logic to handle invalid market data (zero price with non-zero quantity)
            if bid['price'] == 0.0 and bid['qty'] > 0:
                # INVALID: Zero price with non-zero quantity - preserve old price structure
                if old_data['price'] > 0:
                    order_books[ticker]['bids'][level] = {
                        'price': old_data['price'], 
                        'qty': bid['qty'],  # Use the new quantity but keep old price
                        'orders': bid['orders'], 
                        'level': level
                    }
                    print(f"   [BID] BID Level {level}: {old_data['price']:.2f} qty:{bid['qty']:,} orders:{bid['orders']} (INVALID DATA - preserved price)")
                else:
                    # No valid old price, skip this invalid update
                    print(f"   [BID] BID Level {level}: SKIPPED invalid update (price:0.00 qty:{bid['qty']:,})")
            elif bid['qty'] == 0:
                # For zero quantity, preserve the level if we have valid existing data
                if bid['price'] == 0.0 and old_data['price'] > 0:
                    # Keep the old price but set quantity to 0 - this preserves depth structure
                    order_books[ticker]['bids'][level] = {
                        'price': old_data['price'], 
                        'qty': 0, 
                        'orders': bid['orders'], 
                        'level': level
                    }
                    print(f"   [BID] BID Level {level}: {old_data['price']:.2f} qty:0 orders:{bid['orders']} (preserving level)")
                elif bid['price'] > 0:
                    # Update with new price but zero quantity
                    order_books[ticker]['bids'][level] = bid
                    print(f"   [BID] BID Level {level}: {bid['price']:.2f} qty:0 orders:{bid['orders']} (was {old_data['price']:.2f} qty:{old_data['qty']:,})")
                else:
                    # Both price and quantity are zero, only remove if old price was also zero
                    if old_data['price'] == 0.0:
                        order_books[ticker]['bids'][level] = {'price': 0.0, 'qty': 0, 'orders': 0, 'level': level}
                    else:
                        # Preserve the old price structure
                        order_books[ticker]['bids'][level] = {
                            'price': old_data['price'], 
                            'qty': 0, 
                            'orders': bid['orders'], 
                            'level': level
                        }
                        print(f"   [BID] BID Level {level}: {old_data['price']:.2f} qty:0 orders:{bid['orders']} (preserving structure)")
            else:
                # Valid update with both price and quantity > 0
                order_books[ticker]['bids'][level] = bid
                if old_data['price'] != bid['price'] or old_data['qty'] != bid['qty']:
                    print(f"   [BID] BID Level {level}: {bid['price']:.2f} qty:{bid['qty']:,} orders:{bid['orders']} (was {old_data['price']:.2f} qty:{old_data['qty']:,})")
    
    # Process ask updates (enhanced logic matching bid handling)
    for ask in asks:
        level = ask['level']
        if 0 <= level < 50:
            old_data = order_books[ticker]['asks'][level]
            
            # Enhanced logic to handle invalid market data (zero price with non-zero quantity)
            if ask['price'] == 0.0 and ask['qty'] > 0:
                # INVALID: Zero price with non-zero quantity - preserve old price structure
                if old_data['price'] > 0:
                    order_books[ticker]['asks'][level] = {
                        'price': old_data['price'], 
                        'qty': ask['qty'],  # Use the new quantity but keep old price
                        'orders': ask['orders'], 
                        'level': level
                    }
                    print(f"   [ASK] ASK Level {level}: {old_data['price']:.2f} qty:{ask['qty']:,} orders:{ask['orders']} (INVALID DATA - preserved price)")
                else:
                    # No valid old price, skip this invalid update
                    print(f"   [ASK] ASK Level {level}: SKIPPED invalid update (price:0.00 qty:{ask['qty']:,})")
            elif ask['qty'] == 0:
                # For zero quantity, preserve the level if we have valid existing data
                if ask['price'] == 0.0 and old_data['price'] > 0:
                    # Keep the old price but set quantity to 0 - this preserves depth structure
                    order_books[ticker]['asks'][level] = {
                        'price': old_data['price'], 
                        'qty': 0, 
                        'orders': ask['orders'], 
                        'level': level
                    }
                    print(f"   [ASK] ASK Level {level}: {old_data['price']:.2f} qty:0 orders:{ask['orders']} (preserving level)")
                elif ask['price'] > 0:
                    # Update with new price but zero quantity
                    order_books[ticker]['asks'][level] = ask
                    print(f"   [ASK] ASK Level {level}: {ask['price']:.2f} qty:0 orders:{ask['orders']} (was {old_data['price']:.2f} qty:{old_data['qty']:,})")
                else:
                    # Both price and quantity are zero, only remove if old price was also zero
                    if old_data['price'] == 0.0:
                        order_books[ticker]['asks'][level] = {'price': 0.0, 'qty': 0, 'orders': 0, 'level': level}
                    else:
                        # Preserve the old price structure
                        order_books[ticker]['asks'][level] = {
                            'price': old_data['price'], 
                            'qty': 0, 
                            'orders': ask['orders'], 
                            'level': level
                        }
                        print(f"   [ASK] ASK Level {level}: {old_data['price']:.2f} qty:0 orders:{ask['orders']} (preserving structure)")
            else:
                # Valid update with both price and quantity > 0
                order_books[ticker]['asks'][level] = ask
                if old_data['price'] != ask['price'] or old_data['qty'] != ask['qty']:
                    print(f"   [ASK] ASK Level {level}: {ask['price']:.2f} qty:{ask['qty']:,} orders:{ask['orders']} (was {old_data['price']:.2f} qty:{old_data['qty']:,})")
    
    # Mark as initialized after processing updates
    order_books[ticker]['initialized'] = True
    
    # Post-update validation
    active_bids = len([b for b in order_books[ticker]['bids'].values() if b['price'] > 0])
    active_asks = len([a for a in order_books[ticker]['asks'].values() if a['price'] > 0])
    
    print(f"   [STATUS] Update complete: {active_bids} active bid levels, {active_asks} active ask levels")
    
    if active_bids < 5 or active_asks < 5:
        print(f"   [CRITICAL] CRITICAL: Very low depth - Bids: {active_bids}, Asks: {active_asks}")
        
    # Enhanced depth verification - only for logging, don't reset
    missing_bid_levels = [i for i in range(min(10, 50)) if order_books[ticker]['bids'][i]['price'] == 0.0]
    missing_ask_levels = [i for i in range(min(10, 50)) if order_books[ticker]['asks'][i]['price'] == 0.0]
    
    if missing_bid_levels:
        print(f"   [WARNING] Missing bid levels in top 10: {missing_bid_levels}")
    if missing_ask_levels:
        print(f"   [WARNING] Missing ask levels in top 10: {missing_ask_levels}")

def get_full_order_book(ticker):
    """Get the complete 50-level order book for display with proper depth reconstruction"""
    if ticker not in order_books:
        return None
    
    book = order_books[ticker]
    
    # Get all bid levels with valid prices, sorted by price (descending for bids)
    raw_bids = []
    for i in range(50):
        bid = book['bids'][i]
        if bid['price'] > 0:  # Include all levels with valid prices, even if qty is 0
            raw_bids.append({
                'price': bid['price'],
                'qty': bid['qty'], 
                'orders': bid['orders'],
                'level': len(raw_bids)  # Reassign sequential level numbers
            })
    
    # Sort bids by price (highest first) and reassign levels
    raw_bids.sort(key=lambda x: x['price'], reverse=True)
    active_bids = []
    for i, bid in enumerate(raw_bids[:50]):  # Limit to 50 levels
        active_bids.append({
            'price': bid['price'],
            'qty': bid['qty'],
            'orders': bid['orders'],
            'level': i  # Sequential level 0-49
        })
    
    # Get all ask levels with valid prices, sorted by price (ascending for asks)
    raw_asks = []
    for i in range(50):
        ask = book['asks'][i]
        if ask['price'] > 0:  # Include all levels with valid prices, even if qty is 0
            raw_asks.append({
                'price': ask['price'],
                'qty': ask['qty'],
                'orders': ask['orders'],
                'level': len(raw_asks)  # Reassign sequential level numbers
            })
    
    # Sort asks by price (lowest first) and reassign levels
    raw_asks.sort(key=lambda x: x['price'])
    active_asks = []
    for i, ask in enumerate(raw_asks[:50]):  # Limit to 50 levels
        active_asks.append({
            'price': ask['price'],
            'qty': ask['qty'],
            'orders': ask['orders'],
            'level': i  # Sequential level 0-49
        })
    
    # Enhanced logging for reconstructed depth
    print(f"\n[DEPTH] DEPTH RECONSTRUCTION:")
    print(f"   [BIDS] Raw bids found: {len(raw_bids)} -> Active bids: {len(active_bids)}")
    print(f"   [ASKS] Raw asks found: {len(raw_asks)} -> Active asks: {len(active_asks)}")
    
    if len(active_bids) > 0:
        print(f"   [BID] Best bid: {active_bids[0]['price']:.2f} (qty: {active_bids[0]['qty']:,})")
    if len(active_asks) > 0:
        print(f"   [ASK] Best ask: {active_asks[0]['price']:.2f} (qty: {active_asks[0]['qty']:,})")
    
    return {
        'ticker': ticker,
        'tbq': book['tbq'],
        'tsq': book['tsq'],
        'timestamp': book['timestamp'],
        'bids': active_bids,
        'asks': active_asks,
        'bidprice': [bid['price'] for bid in active_bids],
        'askprice': [ask['price'] for ask in active_asks],
        'bidqty': [bid['qty'] for bid in active_bids],
        'askqty': [ask['qty'] for ask in active_asks],
        'bidordn': [bid['orders'] for bid in active_bids],
        'askordn': [ask['orders'] for ask in active_asks]
    }

def process_market_depth(message_bytes):
    """Process market depth protobuf message with proper order book management"""
    try:
        socket_message = msg_pb2.SocketMessage()
        socket_message.ParseFromString(message_bytes)
        
        if socket_message.error:
            print(f"Error in socket message: {socket_message.msg}")
            return None
            
        market_data = {}
        for ticker, feed in socket_message.feeds.items():
            # Extract raw update data
            timestamp = feed.feed_time.value if feed.feed_time else None
            tbq = feed.depth.tbq.value if feed.depth.tbq else 0
            tsq = feed.depth.tsq.value if feed.depth.tsq else 0
            is_snapshot = socket_message.snapshot
            
            # Process bids from update
            update_bids = []
            for bid in feed.depth.bids:
                bid_data = {
                    'price': bid.price.value / 100.0,
                    'qty': bid.qty.value,
                    'orders': bid.nord.value,
                    'level': bid.num.value
                }
                update_bids.append(bid_data)
            
            # Process asks from update
            update_asks = []
            for ask in feed.depth.asks:
                ask_data = {
                    'price': ask.price.value / 100.0,
                    'qty': ask.qty.value,
                    'orders': ask.nord.value,
                    'level': ask.num.value
                }
                update_asks.append(ask_data)
            
            # Debug: Log raw update data
            print(f"\n[RAW] RAW UPDATE DATA for {ticker}:")
            print(f"   [BIDS] Raw bids in update: {len(update_bids)}")
            print(f"   [ASKS] Raw asks in update: {len(update_asks)}")
            if len(update_bids) > 0:
                print(f"   [BID] First bid: Level {update_bids[0]['level']} Price {update_bids[0]['price']:.2f} Qty {update_bids[0]['qty']}")
            if len(update_asks) > 0:
                print(f"   [ASK] First ask: Level {update_asks[0]['level']} Price {update_asks[0]['price']:.2f} Qty {update_asks[0]['qty']}")
            
            # Update the order book
            update_order_book(ticker, update_bids, update_asks, tbq, tsq, timestamp, is_snapshot)
            
            # Get the complete order book for display
            full_book = get_full_order_book(ticker)
            if full_book:
                # Debug check - ensure we have valid data before processing
                if len(full_book['bids']) == 0 and len(full_book['asks']) == 0:
                    print(f"   [WARNING] WARNING: No valid bids or asks found for {ticker}")
                    print(f"   [STATUS] Raw order book state:")
                    for i in range(min(10, 50)):
                        bid = order_books[ticker]['bids'][i]
                        ask = order_books[ticker]['asks'][i]
                        if bid['price'] > 0 or ask['price'] > 0:
                            print(f"     Level {i}: Bid={bid['price']:.2f}(qty:{bid['qty']}) Ask={ask['price']:.2f}(qty:{ask['qty']})")
                    return None
                # Enhanced logging to show COMPLETE 50 depth levels
                print(f"\n{'='*60}")
                print(f"[ORDERBOOK] COMPLETE ORDER BOOK - {ticker}")
                print(f"{'='*60}")
                print(f"Total Buy Qty: {full_book['tbq']:,}")
                print(f"Total Sell Qty: {full_book['tsq']:,}")
                print(f"Active Bid Levels: {len(full_book['bids'])}")
                print(f"Active Ask Levels: {len(full_book['asks'])}")
                print(f"Update Type: {'SNAPSHOT' if is_snapshot else 'INCREMENTAL'}")
                print(f"Timestamp: {full_book['timestamp']}")
                
                # Show ALL ACTIVE BID LEVELS
                print(f"\n{'='*25} ALL ACTIVE BIDS {'='*25}")
                print(f"{'Level':<5} {'Price':<10} {'Qty':<10} {'Orders':<8}")
                print(f"{'-'*40}")
                for bid in full_book['bids']:
                    print(f"{bid['level']:<5} {bid['price']:<10.2f} {bid['qty']:<10,} {bid['orders']:<8}")
                
                # Show ALL ACTIVE ASK LEVELS
                print(f"\n{'='*25} ALL ACTIVE ASKS {'='*25}")
                print(f"{'Level':<5} {'Price':<10} {'Qty':<10} {'Orders':<8}")
                print(f"{'-'*40}")
                for ask in full_book['asks']:
                    print(f"{ask['level']:<5} {ask['price']:<10.2f} {ask['qty']:<10,} {ask['orders']:<8}")
                
                print(f"{'='*60}")
                
                # Transform data structure to match frontend expectations
                frontend_data = {
                    'ticker': full_book['ticker'],
                    'timestamp': full_book['timestamp'] * 1000,  # Convert to milliseconds for JavaScript
                    'total_bid_qty': full_book['tbq'],  # Frontend expects total_bid_qty
                    'total_sell_qty': full_book['tsq'],  # Frontend expects total_sell_qty
                    'bids': [
                        {
                            'level': bid['level'],
                            'price': bid['price'],
                            'quantity': bid['qty'],  # Frontend expects 'quantity'
                            'orders': bid['orders']
                        }
                        for bid in full_book['bids']
                    ],
                    'asks': [
                        {
                            'level': ask['level'],
                            'price': ask['price'],
                            'quantity': ask['qty'],  # Frontend expects 'quantity'
                            'orders': ask['orders']
                        }
                        for ask in full_book['asks']
                    ],
                    'bidprice': full_book['bidprice'],
                    'askprice': full_book['askprice'],
                    'bidqty': full_book['bidqty'],
                    'askqty': full_book['askqty'],
                    'bidordn': full_book['bidordn'],
                    'askordn': full_book['askordn']
                }
                
                # Enhanced frontend data logging
                print(f"\n[FRONTEND] FRONTEND DATA SUMMARY:")
                print(f"   [BIDS] Bids sent to frontend: {len(frontend_data['bids'])}")
                print(f"   [ASKS] Asks sent to frontend: {len(frontend_data['asks'])}")
                if len(frontend_data['bids']) > 0:
                    print(f"   [BID] Best bid sent: {frontend_data['bids'][0]['price']:.2f}")
                if len(frontend_data['asks']) > 0:
                    print(f"   [ASK] Best ask sent: {frontend_data['asks'][0]['price']:.2f}")
                print(f"   [BIDS] Total bid qty: {frontend_data['total_bid_qty']:,}")
                print(f"   [ASKS] Total ask qty: {frontend_data['total_sell_qty']:,}")
                
                market_data[ticker] = frontend_data
            else:
                print(f"   [WARNING] Skipping {ticker} - no valid order book data")
        
        if len(market_data) == 0:
            print("   [ERROR] No market data to send to frontend")
            return None
            
        return market_data
    except Exception as e:
        print(f"Error processing market depth: {e}")
        import traceback
        traceback.print_exc()
        return None

async def subscribe_symbols():
    """Subscribe to market depth data for symbols"""
    try:
        # Updated subscription message format for TBT WebSocket
        subscribe_msg = {
            "type": 1,
            "data": {
                "subs": 1,
                "symbols": [SYMBOL],
                "mode": "depth",
                "channel": "1"
            }
        }
        
        print(f"\n=== Sending Subscribe Message ===")
        print(f"Message: {json.dumps(subscribe_msg, indent=2)}")
        
        if websocket:
            await websocket.send(json.dumps(subscribe_msg))
            print("Subscribe message sent successfully")
            
            # Resume channel message
            resume_msg = {
                "type": 2,
                "data": {
                    "resumeChannels": ["1"],
                    "pauseChannels": []
                }
            }
            
            print(f"\n=== Sending Channel Resume Message ===")
            print(f"Message: {json.dumps(resume_msg, indent=2)}")
            
            await websocket.send(json.dumps(resume_msg))
            print("Channel resume message sent successfully")
            
    except Exception as e:
        print(f"Error in subscribe_symbols: {e}")

websocket = None
last_ping_time = 0

async def websocket_client():
    global websocket, last_ping_time
    
    while True:
        try:
            print("\n=== Attempting WebSocket Connection ===")
            auth_header = f"{FYERS_APP_ID}:{FYERS_ACCESS_TOKEN}"
            
            print(f"WebSocket URL: {WEBSOCKET_URL}")
            print(f"App ID: {FYERS_APP_ID}")
            print(f"Auth Header Format: {FYERS_APP_ID}:<access_token>")
            print(f"Full Auth Header Length: {len(auth_header)}")
            
            async with websockets.connect(
                WEBSOCKET_URL,
                extra_headers={
                    "Authorization": auth_header
                }
            ) as ws:
                websocket = ws
                print("WebSocket connection established!")
                
                # Subscribe to symbols
                await subscribe_symbols()
                last_ping_time = time.time()
                
                while True:
                    try:
                        # Send ping every 30 seconds
                        current_time = time.time()
                        if current_time - last_ping_time >= 30:
                            await ws.send("ping")
                            last_ping_time = current_time
                            print("Ping sent")
                        
                        message = await ws.recv()
                        if isinstance(message, bytes):
                            market_data = process_market_depth(message)
                            if market_data:
                                print(f"[EMIT] Emitting market_depth data to frontend with {len(market_data)} symbols")
                                socketio.emit('market_depth', market_data)
                            else:
                                print("[EMIT] No market_depth data to emit (empty or invalid)")
                        else:
                            print(f"Received text message: {message}")
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket connection closed")
                        break
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        
        except websockets.exceptions.WebSocketException as e:
            print("\n=== Connection Failed ===")
            print(f"WebSocket Error: {str(e)}")
            print(f"Please check your Fyers API credentials")
            
        except Exception as e:
            print(f"\n=== Unexpected Error ===")
            print(f"Error: {str(e)}")
            
        print("\nRetrying connection in 5 seconds...")
        await asyncio.sleep(5)

@app.route('/')
def index():
    return render_template('index.html', symbol=SYMBOL)

@app.route('/api/config')
def get_config():
    """Get application configuration including symbol"""
    return {
        'symbol': SYMBOL,
        'app_name': 'Fyers Dom Analyzer'
    }

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send a test message to verify connection
    socketio.emit('test_message', {'message': 'Hello from backend!'})

def run_websocket():
    asyncio.run(websocket_client())

if __name__ == '__main__':
    # Start WebSocket client in a separate thread
    import threading
    ws_thread = threading.Thread(target=run_websocket)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Run Flask application
    socketio.run(app, debug=True, port=5001)
