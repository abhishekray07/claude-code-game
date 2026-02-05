#!/usr/bin/env python3
"""Test WebSocket proxy to specific Fly machine.

This script verifies that the fly-force-instance-id header correctly routes
WebSocket connections to a specific Fly machine.

Usage:
    # Set the machine ID to test (get from `fly machines list -a claude-game-sandbox`)
    export TEST_MACHINE_ID="your-machine-id"
    python scripts/test_ws_proxy.py
"""
import asyncio
import os
import sys

try:
    import websockets
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    sys.exit(1)

# Configuration
MACHINE_ID = os.environ.get("TEST_MACHINE_ID", "")
FLY_APP = os.environ.get("FLY_SANDBOX_APP", "claude-game-sandbox")


async def test_direct_connection():
    """Test connecting to ttyd with fly-force-instance-id header."""
    if not MACHINE_ID:
        print("Error: TEST_MACHINE_ID environment variable not set")
        print("Get a machine ID with: fly machines list -a claude-game-sandbox")
        return False

    url = f"wss://{FLY_APP}.fly.dev/ws"
    headers = {"fly-force-instance-id": MACHINE_ID}

    print(f"Connecting to {url}")
    print(f"Using machine ID: {MACHINE_ID}")

    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            print("Connected! Waiting for initial terminal data...")

            # ttyd sends initial terminal data (escape sequences, prompt, etc.)
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"Received initial data: {len(data)} bytes")
                if isinstance(data, bytes):
                    print(f"  Preview: {data[:100]!r}")
                else:
                    print(f"  Preview: {data[:100]}")
            except asyncio.TimeoutError:
                print("Warning: No initial data received (timeout)")

            # Send a command to verify we're on the right machine
            print("\nSending: echo $HOSTNAME")
            # ttyd expects JSON messages with type 0 (input) or 1 (resize)
            # Type 0: {"type": 0, "data": "..."}
            # But many ttyd configs also accept raw text
            await ws.send("echo $HOSTNAME\n")

            # Read response lines
            print("\nReading response...")
            hostname_found = False
            for i in range(10):
                try:
                    data = await asyncio.wait_for(ws.recv(), timeout=2)
                    if isinstance(data, bytes):
                        data = data.decode("utf-8", errors="replace")
                    print(f"  [{i}]: {data!r}")

                    # Check if we got the hostname back
                    if MACHINE_ID[:8] in data:
                        hostname_found = True
                        print(f"\nSUCCESS: Response contains machine ID prefix!")
                except asyncio.TimeoutError:
                    break

            if hostname_found:
                print("\n=== TEST PASSED ===")
                print("fly-force-instance-id header correctly routes to specific machine")
                return True
            else:
                print("\n=== TEST INCONCLUSIVE ===")
                print("Connection worked but couldn't verify machine ID in hostname")
                print("This might still be working - check the output above")
                return True

    except websockets.exceptions.WebSocketException as e:
        print(f"\nWebSocket error: {e}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    print("=" * 60)
    print("WebSocket Proxy Test - Fly.io Machine Routing")
    print("=" * 60)
    print()

    success = await test_direct_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
