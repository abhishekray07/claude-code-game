"""Spike: Test WebSocket proxy pattern."""
import asyncio
import websockets


async def proxy_handler(websocket):
    """Proxy WebSocket - simplified echo for testing."""
    print(f"Client connected")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            # Echo back for testing
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")


async def main():
    print("Starting WebSocket proxy on ws://localhost:8765")
    print("Open test_ws_client.html in a browser to test")
    print("Press Ctrl+C to stop")
    async with websockets.serve(proxy_handler, "localhost", 8765):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
