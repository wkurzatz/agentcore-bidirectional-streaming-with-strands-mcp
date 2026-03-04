import asyncio
import websockets
import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---

AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT","ws://localhost:8080/ws")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL")


def get_jwt():

    """Fetches a JWT from your configured OAuth provider."""

    payload = {

        'grant_type': 'client_credentials',

        'client_id': CLIENT_ID,

        'client_secret': CLIENT_SECRET,

        'scope': 'eadp.client.slf-drug-demo.read ' # Adjust based on your agent's config

    }

    response = requests.post(OAUTH_TOKEN_URL, data=payload)

    response.raise_for_status()

    return response.json().get('access_token')

async def chat_with_agent():
    uri = AGENT_ENDPOINT
    print(f"Connecting to agent at {uri[:50]}...")
    # Get JWT token and set up authorization header (skip if CLIENT_ID not configured)
    headers = {}
    if CLIENT_ID:
        jwt_token = get_jwt()
        headers = {"Authorization": f"Bearer {jwt_token}"}
    else:
        print("Note: CLIENT_ID not set, connecting without JWT authentication")
    
    # Increase ping timeout to handle long MCP tool calls (default is 20s)
    async with websockets.connect(
        uri, 
        additional_headers=headers,
        ping_interval=30,      # Send ping every 30 seconds
        ping_timeout=120,      # Wait 120 seconds for pong response
        close_timeout=30       # Wait 30 seconds for close handshake
    ) as websocket:
        print("Connected to the agent. Type your messages below (type 'exit' to quit):")
        while True:
            # Run input() in a thread to avoid blocking the event loop
            # This allows WebSocket pings to be handled while waiting for input
            loop = asyncio.get_event_loop()
            query = await loop.run_in_executor(None, lambda: input("\nYou: "))
            
            if query.lower() in ["exit", "quit"]:
                break
                
            # Send prompt to the agent
            await websocket.send(json.dumps({"prompt": query}))
            
            # Read the streaming response
            print("Agent: ", end="", flush=True)
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data["type"] == "chunk":
                    print(data["content"], end="", flush=True)
                elif data["type"] == "end_of_turn":
                    break
                elif data["type"] == "error":
                    print(f"\n[Error: {data.get('message', 'Unknown error')}]")
                    break

asyncio.run(chat_with_agent())