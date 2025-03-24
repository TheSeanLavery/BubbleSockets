# BubbleSockets 🫧

A real-time collaborative bubble wrap popping experience built with WebSockets and modern web technologies.

![BubbleSockets Demo](https://i.imgur.com/placeholder.gif)

## Features

- **Real-time Synchronization**: Pop bubbles and see others' pops in real-time
- **Realistic Bubble Animations**: 10 unique wrinkled variants for popped bubbles
- **Pattern-Based Reset**: When all bubbles are popped, they reset in cool visual patterns
- **Drag-to-Pop**: Hold down your mouse and drag to pop multiple bubbles
- **Satisfying Sound Effects**: Toggle-able pop sounds with variety
- **Responsive Design**: Works on desktop and mobile devices
- **Network Optimized**: Uses binary protocol (MessagePack) and delta updates for efficiency

## Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python with WebSockets
- **Real-time Communication**: WebSockets for bidirectional communication
- **Data Serialization**: MessagePack for efficient binary encoding
- **Patterns**: Various algorithmic patterns for bubble reset animations

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/BubbleSockets.git
   cd BubbleSockets
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python simple_server.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:8080
   ```

## How It Works

### Architecture

BubbleSockets uses a client-server architecture:

- **Server**: A Python WebSocket server that maintains the state of all bubbles and broadcasts updates to connected clients
- **Client**: A web browser that displays the bubble wrap interface and sends user interactions to the server

### Network Optimization

The application uses several techniques to minimize network traffic:

1. **Binary Protocol**: MessagePack encoding reduces payload size by ~40% compared to JSON
2. **Delta Updates**: Only changed bubble states are sent over the network
3. **Fallback Mechanism**: Automatically falls back to JSON when needed for compatibility

### Reset Animations

When all bubbles are popped, they reset in one of these patterns:

- Spiral (inward or outward)
- Wave (horizontal or vertical)
- Diagonal
- Checkerboard
- Random
- Corners-in

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the simple joy of popping bubble wrap
- Built with modern web technologies to create a satisfying interactive experience
