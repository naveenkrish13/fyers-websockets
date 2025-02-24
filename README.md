# Fyers Market Depth Viewer

A real-time market depth viewer application that connects to Fyers WebSocket API to stream Tick-by-Tick (TBT) market depth data for BANKNIFTY futures. Built with Flask and Socket.IO for real-time updates, and DaisyUI for a modern UI.

## Features

- Real-time market depth data streaming via WebSocket
- Display of 50 depth levels for both bid and ask orders
- Total bid and ask quantities display
- Price formatting with proper decimal places
- Order quantity formatting with Indian number system
- Dark/Light theme toggle
- Responsive table layout with pinned headers
- Auto-reconnect WebSocket functionality

## Prerequisites

- Python 3.8 or higher
- Fyers API credentials (App ID and Access Token)
- Active Fyers trading account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/marketcalls/fyers-websockets.git
cd fyers-websockets
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Update the `.env` file with your Fyers credentials:
```
FYERS_APP_ID=your_app_id
FYERS_ACCESS_TOKEN=your_access_token
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## WebSocket Connection Details

- WebSocket URL: `wss://rtsocket-api.fyers.in/versova`
- Protocol: Protobuf for efficient message encoding/decoding
- Subscription: BANKNIFTY futures market depth data
- Auto-ping enabled to maintain connection

## Data Display

The application shows:
- Total bid and ask quantities at the top
- Two tables showing bid and ask orders with:
  - Level number (1-50)
  - Price (formatted with 2 decimal places)
  - Quantity (formatted with Indian number system)
  - Number of orders at each level

## UI Features

- Responsive design using DaisyUI and Tailwind CSS
- Dark/Light theme toggle
- Scrollable tables with pinned headers
- Color-coded bid (green) and ask (red) orders
- Monospace font for better number readability

## Error Handling

- Automatic WebSocket reconnection on disconnection
- Error logging for WebSocket and data processing issues
- User-friendly error messages in the UI

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Fyers API Documentation](https://api-docs.fyers.in/)
- [DaisyUI](https://daisyui.com/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)

## Author

**marketcalls**
- GitHub: [@marketcalls](https://github.com/marketcalls)

## Support

If you found this project helpful, please consider giving it a ⭐!
