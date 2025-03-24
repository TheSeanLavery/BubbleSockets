import asyncio
import json
import websockets
import http.server
import socketserver
import threading
import os
import time
import random
import msgpack
import traceback
from urllib.parse import urlparse

# Global state
connected_clients = set()
bubble_state = {}  # Maps bubble_id to popped state (True/False)
previous_state = {}  # For tracking changes
TOTAL_BUBBLES = 150  # 10 rows x 15 columns

# Initialize all bubbles as not popped
for i in range(TOTAL_BUBBLES):
    bubble_state[str(i)] = False
    previous_state[str(i)] = False

# Get port from environment variable (for Replit)
HTTP_PORT = int(os.environ.get('PORT', 8080))
WS_PORT = int(os.environ.get('WS_PORT', 8081))

# Determine if we're running on Replit
IS_REPLIT = 'REPL_ID' in os.environ
REPLIT_URL = os.environ.get('REPL_SLUG', '') + '.' + os.environ.get('REPL_OWNER', '') + '.repl.co'

# WebSocket server handler
async def handle_websocket(websocket, path):
    connected_clients.add(websocket)
    try:
        # Send initial state to the new client
        await send_state_update(websocket, full_state=True)
        
        # Process messages from this client
        async for message in websocket:
            try:
                # Try to unpack as MessagePack first
                try:
                    if isinstance(message, bytes):
                        data = msgpack.unpackb(message, raw=False)
                        print(f"Received binary message: {data}")
                    else:
                        # Fall back to JSON if not binary
                        data = json.loads(message)
                        print(f"Received JSON message: {data}")
                except Exception as e:
                    print(f"Error unpacking message: {e}")
                    print(f"Message type: {type(message)}, content: {message[:100] if isinstance(message, bytes) else message}")
                    # Last resort - try JSON
                    data = json.loads(message)
                
                if data['type'] == 'pop_bubble':
                    bubble_id = data['bubble_id']
                    bubble_state[bubble_id] = True
                    print(f"Popping bubble {bubble_id}")
                    
                    # Check if all bubbles are popped
                    if all(bubble_state.values()):
                        # Schedule a pattern-based reset
                        asyncio.create_task(reset_bubbles_with_pattern())
                    
                    # Broadcast the updated state to all clients
                    await broadcast_state()
                    
                elif data['type'] == 'reset_request':
                    # Schedule a pattern-based reset
                    asyncio.create_task(reset_bubbles_with_pattern())
            except Exception as e:
                print(f"Error processing message: {e}")
                traceback.print_exc()
    
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
    finally:
        connected_clients.remove(websocket)
        await broadcast_state()

# Reset all bubbles in a pattern
async def reset_bubbles_with_pattern():
    print("Resetting all bubbles with pattern...")
    
    # Choose a random pattern
    pattern = random.choice([
        "spiral_in", "spiral_out", "wave_horizontal", "wave_vertical", 
        "diagonal", "checkerboard", "random", "corners_in"
    ])
    
    print(f"Using pattern: {pattern}")
    
    # Get bubbles in the desired order based on pattern
    bubbles_order = get_bubbles_in_pattern(pattern)
    
    # Reset bubbles one by one with a small delay
    for bubble_id in bubbles_order:
        bubble_state[bubble_id] = False
        await broadcast_state()
        await asyncio.sleep(0.02)  # 20ms delay between each bubble

# Get bubbles in a specific pattern order
def get_bubbles_in_pattern(pattern):
    rows, cols = 10, 15
    bubbles = []
    
    if pattern == "spiral_in":
        # Start from outside and spiral inward
        top, bottom = 0, rows - 1
        left, right = 0, cols - 1
        
        while top <= bottom and left <= right:
            # Top row
            for i in range(left, right + 1):
                bubbles.append(str(top * cols + i))
            top += 1
            
            # Right column
            for i in range(top, bottom + 1):
                bubbles.append(str(i * cols + right))
            right -= 1
            
            # Bottom row
            if top <= bottom:
                for i in range(right, left - 1, -1):
                    bubbles.append(str(bottom * cols + i))
                bottom -= 1
            
            # Left column
            if left <= right:
                for i in range(bottom, top - 1, -1):
                    bubbles.append(str(i * cols + left))
                left += 1
    
    elif pattern == "spiral_out":
        # Same as spiral_in but reversed
        bubbles = get_bubbles_in_pattern("spiral_in")
        bubbles.reverse()
    
    elif pattern == "wave_horizontal":
        # Reset in horizontal waves
        for r in range(rows):
            for c in range(cols):
                bubbles.append(str(r * cols + c))
    
    elif pattern == "wave_vertical":
        # Reset in vertical waves
        for c in range(cols):
            for r in range(rows):
                bubbles.append(str(r * cols + c))
    
    elif pattern == "diagonal":
        # Reset in diagonal lines
        for s in range(rows + cols - 1):
            for r in range(rows):
                c = s - r
                if 0 <= c < cols:
                    bubbles.append(str(r * cols + c))
    
    elif pattern == "checkerboard":
        # Reset in a checkerboard pattern
        # First all even positions
        for r in range(rows):
            for c in range(cols):
                if (r + c) % 2 == 0:
                    bubbles.append(str(r * cols + c))
        # Then all odd positions
        for r in range(rows):
            for c in range(cols):
                if (r + c) % 2 == 1:
                    bubbles.append(str(r * cols + c))
    
    elif pattern == "random":
        # Reset in a random order
        bubbles = [str(i) for i in range(rows * cols)]
        random.shuffle(bubbles)
    
    elif pattern == "corners_in":
        # Start from the four corners and work inward
        visited = set()
        for distance in range(max(rows, cols)):
            for r in range(rows):
                for c in range(cols):
                    # Calculate distance from nearest edge
                    edge_distance = min(r, rows - 1 - r, c, cols - 1 - c)
                    if edge_distance == distance:
                        bubble_id = str(r * cols + c)
                        if bubble_id not in visited:
                            bubbles.append(bubble_id)
                            visited.add(bubble_id)
    
    return bubbles

# Send state update to a specific client
async def send_state_update(websocket, full_state=False):
    global previous_state
    
    try:
        if full_state:
            # Send full state for new connections
            message = {
                'type': 'state_update',
                'full_state': True,
                'bubble_state': bubble_state,
                'connected_users': len(connected_clients)
            }
            
            # Try MessagePack first
            try:
                packed_message = msgpack.packb(message, use_bin_type=True)
                await websocket.send(packed_message)
                print(f"Sent binary state update to client, size: {len(packed_message)} bytes")
            except Exception as e:
                print(f"Error sending binary message: {e}")
                # Fall back to JSON
                await websocket.send(json.dumps(message))
                print(f"Sent JSON state update to client")
        else:
            # Calculate delta (only changed bubbles)
            delta = {}
            for bubble_id, is_popped in bubble_state.items():
                if bubble_id not in previous_state or previous_state[bubble_id] != is_popped:
                    delta[bubble_id] = is_popped
            
            # Only send if there are changes
            if delta:
                message = {
                    'type': 'delta_update',
                    'delta': delta,
                    'connected_users': len(connected_clients)
                }
                
                # Try MessagePack first
                try:
                    packed_message = msgpack.packb(message, use_bin_type=True)
                    await websocket.send(packed_message)
                    print(f"Sent binary delta update with {len(delta)} changes, size: {len(packed_message)} bytes")
                except Exception as e:
                    print(f"Error sending binary delta: {e}")
                    # Fall back to JSON
                    await websocket.send(json.dumps(message))
                    print(f"Sent JSON delta update with {len(delta)} changes")
    except Exception as e:
        print(f"Error in send_state_update: {e}")
        traceback.print_exc()

# Broadcast state to all connected clients
async def broadcast_state():
    global previous_state
    
    if connected_clients:
        try:
            # Calculate delta (only changed bubbles)
            delta = {}
            for bubble_id, is_popped in bubble_state.items():
                if bubble_id not in previous_state or previous_state[bubble_id] != is_popped:
                    delta[bubble_id] = is_popped
            
            # Update previous state
            previous_state = bubble_state.copy()
            
            # Only send if there are changes
            if delta:
                message = {
                    'type': 'delta_update',
                    'delta': delta,
                    'connected_users': len(connected_clients)
                }
                
                # Try MessagePack first with fallback to JSON
                for client in connected_clients:
                    try:
                        packed_message = msgpack.packb(message, use_bin_type=True)
                        await client.send(packed_message)
                    except Exception as e:
                        print(f"Error sending binary broadcast: {e}")
                        # Fall back to JSON
                        await client.send(json.dumps(message))
                
                print(f"Broadcast update to {len(connected_clients)} clients with {len(delta)} changes")
        except Exception as e:
            print(f"Error in broadcast_state: {e}")
            traceback.print_exc()

# Start HTTP server
def start_http_server():
    # Serve files from the static directory
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", HTTP_PORT), handler)
    print(f"HTTP Server running on http://localhost:{HTTP_PORT}")
    httpd.serve_forever()

# Modify index.html for Replit
def modify_index_html_for_replit():
    if not IS_REPLIT:
        return
    
    try:
        # Read the current index.html
        with open('static/index.html', 'r') as file:
            content = file.read()
        
        # Replace the WebSocket URL to use the same domain with a different path
        content = content.replace(
            "const wsUrl = `ws://localhost:8081`;",
            f"const wsUrl = `wss://{REPLIT_URL}/ws`;"
        )
        
        # Write the modified content back
        with open('static/index.html', 'w') as file:
            file.write(content)
        
        print(f"Modified index.html for Replit environment")
    except Exception as e:
        print(f"Error modifying index.html: {e}")

# Main function to start everything
async def main():
    # Modify index.html if on Replit
    modify_index_html_for_replit()
    
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=start_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # Start WebSocket server
    if IS_REPLIT:
        # On Replit, we need to use a single port with path routing
        print(f"WebSocket Server running at wss://{REPLIT_URL}/ws")
        async with websockets.serve(handle_websocket, "", HTTP_PORT, process_request=process_request):
            await asyncio.Future()  # Run forever
    else:
        # Local development with separate ports
        print(f"WebSocket Server running on ws://localhost:{WS_PORT}")
        async with websockets.serve(handle_websocket, "", WS_PORT):
            await asyncio.Future()  # Run forever

# Process HTTP requests for path-based routing on Replit
async def process_request(path, request_headers):
    if IS_REPLIT and urlparse(path).path == '/ws':
        # This is a WebSocket request, let it through
        return None
    
    # For all other paths, serve static files
    return await serve_static_file(path)

# Serve static files for path-based routing
async def serve_static_file(path):
    parsed_path = urlparse(path).path
    
    # Default to index.html
    if parsed_path == '/':
        parsed_path = '/index.html'
    
    # Prepend 'static' directory
    file_path = os.path.join('static', parsed_path.lstrip('/'))
    
    # Check if file exists
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return http.HTTPStatus.NOT_FOUND, [], b'404 Not Found'
    
    # Determine content type
    content_type = 'text/plain'
    if file_path.endswith('.html'):
        content_type = 'text/html'
    elif file_path.endswith('.css'):
        content_type = 'text/css'
    elif file_path.endswith('.js'):
        content_type = 'application/javascript'
    elif file_path.endswith('.png'):
        content_type = 'image/png'
    elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
        content_type = 'image/jpeg'
    elif file_path.endswith('.mp3'):
        content_type = 'audio/mpeg'
    elif file_path.endswith('.wav'):
        content_type = 'audio/wav'
    
    # Read file content
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Return file content with appropriate headers
    headers = [
        ('Content-Type', content_type),
        ('Content-Length', str(len(content)))
    ]
    
    return http.HTTPStatus.OK, headers, content

# Run the main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        traceback.print_exc()
