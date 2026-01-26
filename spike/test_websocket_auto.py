"""Spike: Automated WebSocket proxy test (no browser needed)."""
import asyncio
import websockets


async def echo_handler(websocket):
    """Echo server handler."""
    async for message in websocket:
        await websocket.send(f"Echo: {message}")


async def run_test():
    """Run WebSocket server and client test."""
    print("Starting WebSocket echo server on ws://localhost:8766...")

    # Start server
    server = await websockets.serve(echo_handler, "localhost", 8766)

    print("Server started. Testing client connection...")

    # Test client
    try:
        async with websockets.connect("ws://localhost:8766") as ws:
            # Test 1: Simple message
            await ws.send("Hello, WebSocket!")
            response = await ws.recv()
            assert response == "Echo: Hello, WebSocket!", f"Unexpected response: {response}"
            print(f"  Test 1 PASS: Sent 'Hello, WebSocket!' -> Received '{response}'")

            # Test 2: Multiple messages
            for i in range(3):
                msg = f"Message {i}"
                await ws.send(msg)
                response = await ws.recv()
                assert response == f"Echo: {msg}", f"Unexpected response: {response}"
            print("  Test 2 PASS: Multiple messages work correctly")

            # Test 3: Binary-like data (JSON)
            import json
            data = json.dumps({"type": "terminal", "data": "ls -la"})
            await ws.send(data)
            response = await ws.recv()
            assert "terminal" in response, f"Unexpected response: {response}"
            print("  Test 3 PASS: JSON data transmitted correctly")

        print("\nAll WebSocket tests PASSED!")
        return True

    except Exception as e:
        print(f"\nWebSocket test FAILED: {e}")
        return False

    finally:
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    result = asyncio.run(run_test())
    print(f"\n{'='*50}")
    print(f"Test result: {'PASS' if result else 'FAIL'}")
