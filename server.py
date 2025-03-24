import asyncio
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Set, List

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store connected clients
connected_clients: Set[WebSocket] = set()

# Store the current state of bubbles (popped or not)
# Format: {bubble_id: is_popped}
bubble_state: Dict[str, bool] = {}

# Fixed bubble grid configuration
GRID_ROWS = 10
GRID_COLS = 15
TOTAL_BUBBLES = GRID_ROWS * GRID_COLS

# Initialize bubble state
for i in range(TOTAL_BUBBLES):
    bubble_state[str(i)] = False

async def broadcast_state(exclude_client=None):
    """Broadcast the current state to all connected clients"""
    if connected_clients:
        message = {
            "type": "state_update",
            "bubble_state": bubble_state,
            "connected_users": len(connected_clients)
        }
        
        encoded_message = json.dumps(message)
        
        await asyncio.gather(
            *[client.send_text(encoded_message) for client in connected_clients if client != exclude_client]
        )

async def reset_bubbles():
    """Reset all bubbles to unpopped state"""
    for i in range(TOTAL_BUBBLES):
        bubble_state[str(i)] = False
    
    await broadcast_state()

@app.get("/")
async def get_index():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    
    # Send current state to the new client
    initial_state = {
        "type": "state_update",
        "bubble_state": bubble_state,
        "connected_users": len(connected_clients)
    }
    await websocket.send_text(json.dumps(initial_state))
    
    # Notify all clients about new connection
    await broadcast_state(exclude_client=websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "pop_bubble":
                bubble_id = message["bubble_id"]
                if bubble_id in bubble_state and not bubble_state[bubble_id]:
                    bubble_state[bubble_id] = True
                    
                    # Check if all bubbles are popped
                    if all(bubble_state.values()):
                        # Reset after a short delay
                        await broadcast_state()
                        await asyncio.sleep(1)
                        await reset_bubbles()
                    else:
                        await broadcast_state()
            
            elif message["type"] == "reset_request":
                await reset_bubbles()
                
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        await broadcast_state()

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
