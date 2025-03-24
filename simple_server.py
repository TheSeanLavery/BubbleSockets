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

# Global state
connected_clients = set()
bubble_state = {}  # Maps bubble_id to popped state (True/False)
previous_state = {}  # For tracking changes
TOTAL_BUBBLES = 150  # 10 rows x 15 columns

# Initialize all bubbles as not popped
for i in range(TOTAL_BUBBLES):
    bubble_state[str(i)] = False
    previous_state[str(i)] = False

# HTTP Server for static files
class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="static", **kwargs)
        
    def log_message(self, format, *args):
        # Suppress log messages
        pass

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

# Reset bubbles in a pattern
async def reset_bubbles_with_pattern():
    # Define different reset patterns
    patterns = [
        'spiral_in',
        'spiral_out',
        'wave_horizontal',
        'wave_vertical',
        'diagonal',
        'checkerboard',
        'random',
        'corners_in'
    ]
    
    # Choose a random pattern
    pattern = random.choice(patterns)
    
    # Get the sequence of bubble IDs based on the pattern
    bubble_sequence = get_bubble_sequence(pattern)
    
    # Reset bubbles in the sequence
    for bubble_id in bubble_sequence:
        bubble_state[str(bubble_id)] = False
        await broadcast_state()
        await asyncio.sleep(0.02)  # Small delay between each bubble reset

# Generate a sequence of bubble IDs based on the pattern
def get_bubble_sequence(pattern):
    rows = 10
    cols = 15
    
    if pattern == 'spiral_in':
        return spiral_pattern(rows, cols, inward=True)
    elif pattern == 'spiral_out':
        return spiral_pattern(rows, cols, inward=False)
    elif pattern == 'wave_horizontal':
        return wave_pattern(rows, cols, horizontal=True)
    elif pattern == 'wave_vertical':
        return wave_pattern(rows, cols, horizontal=False)
    elif pattern == 'diagonal':
        return diagonal_pattern(rows, cols)
    elif pattern == 'checkerboard':
        return checkerboard_pattern(rows, cols)
    elif pattern == 'random':
        return random_pattern(rows, cols)
    elif pattern == 'corners_in':
        return corners_in_pattern(rows, cols)
    else:
        # Default to random if pattern not recognized
        return random_pattern(rows, cols)

# Pattern generators
def spiral_pattern(rows, cols, inward=True):
    result = []
    top, bottom = 0, rows - 1
    left, right = 0, cols - 1
    direction = 0  # 0: right, 1: down, 2: left, 3: up
    
    while top <= bottom and left <= right:
        if direction == 0:  # Move right
            for i in range(left, right + 1):
                result.append(top * cols + i)
            top += 1
        elif direction == 1:  # Move down
            for i in range(top, bottom + 1):
                result.append(i * cols + right)
            right -= 1
        elif direction == 2:  # Move left
            for i in range(right, left - 1, -1):
                result.append(bottom * cols + i)
            bottom -= 1
        elif direction == 3:  # Move up
            for i in range(bottom, top - 1, -1):
                result.append(i * cols + left)
            left += 1
        direction = (direction + 1) % 4
    
    if inward:
        return result
    else:
        return result[::-1]  # Reverse for outward spiral

def wave_pattern(rows, cols, horizontal=True):
    result = []
    
    if horizontal:
        for r in range(rows):
            row_bubbles = []
            for c in range(cols):
                row_bubbles.append(r * cols + c)
            
            # Alternate direction for even/odd rows
            if r % 2 == 1:
                row_bubbles.reverse()
                
            result.extend(row_bubbles)
    else:  # vertical
        for c in range(cols):
            col_bubbles = []
            for r in range(rows):
                col_bubbles.append(r * cols + c)
            
            # Alternate direction for even/odd columns
            if c % 2 == 1:
                col_bubbles.reverse()
                
            result.extend(col_bubbles)
    
    return result

def diagonal_pattern(rows, cols):
    result = []
    
    # Process all diagonals from top-left to bottom-right
    for sum_idx in range(rows + cols - 1):
        diagonal = []
        for i in range(max(0, sum_idx - cols + 1), min(rows, sum_idx + 1)):
            j = sum_idx - i
            if 0 <= j < cols:
                diagonal.append(i * cols + j)
        
        # Alternate direction for even/odd diagonals
        if sum_idx % 2 == 1:
            diagonal.reverse()
            
        result.extend(diagonal)
    
    return result

def checkerboard_pattern(rows, cols):
    # First all evens, then all odds
    evens = []
    odds = []
    
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if (r + c) % 2 == 0:
                evens.append(idx)
            else:
                odds.append(idx)
    
    return evens + odds

def random_pattern(rows, cols):
    indices = list(range(rows * cols))
    random.shuffle(indices)
    return indices

def corners_in_pattern(rows, cols):
    # Calculate distance from center for each cell
    center_r, center_c = (rows - 1) / 2, (cols - 1) / 2
    cells_with_distances = []
    
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            # Use max distance (Manhattan distance) from center
            distance = max(abs(r - center_r), abs(c - center_c))
            cells_with_distances.append((idx, distance))
    
    # Sort by distance (descending) to go from corners inward
    cells_with_distances.sort(key=lambda x: -x[1])
    return [idx for idx, _ in cells_with_distances]

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
    http_port = 8080
    handler = HttpRequestHandler
    httpd = socketserver.TCPServer(("", http_port), handler)
    print(f"HTTP Server running on http://localhost:{http_port}")
    httpd.serve_forever()

# Start WebSocket server
async def start_websocket_server():
    ws_port = 8081
    server = await websockets.serve(
        handle_websocket, 
        "localhost", 
        ws_port
    )
    print(f"WebSocket Server running on ws://localhost:{ws_port}")
    await server.wait_closed()

# Main function
def main():
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=start_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # Start WebSocket server in the main thread
    asyncio.run(start_websocket_server())

if __name__ == "__main__":
    main()
