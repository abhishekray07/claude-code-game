#!/usr/bin/env python3
"""Test Fly exec API directly to debug verification issues."""
import asyncio
import base64
import json
import os
import httpx

# Configuration - update these
MACHINE_ID = os.environ.get("MACHINE_ID", "7815744ae5e2e8")
FLY_APP = os.environ.get("FLY_SANDBOX_APP", "claude-game-sandbox")
FLY_API_TOKEN = os.environ.get("FLY_API_TOKEN", "")

FLY_MACHINES_API = "https://api.machines.dev/v1"


async def exec_command(machine_id: str, cmd: str) -> dict:
    """Execute command and return raw response."""
    headers = {
        "Authorization": f"Bearer {FLY_API_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{FLY_MACHINES_API}/apps/{FLY_APP}/machines/{machine_id}/exec",
            headers=headers,
            json={"cmd": cmd},
        )

        print(f"\n=== Command: {cmd} ===")
        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error: {response.text}")
            return {}

        data = response.json()
        return data


def try_decode(value: str, label: str) -> str:
    """Try to decode as base64, show both versions."""
    if not value:
        print(f"{label}: (empty)")
        return ""

    print(f"\n{label} raw ({len(value)} chars): {value[:200]}...")

    try:
        decoded = base64.b64decode(value).decode("utf-8")
        print(f"{label} base64-decoded ({len(decoded)} chars): {decoded[:200]}...")
        return decoded
    except Exception as e:
        print(f"{label} base64 decode failed: {e}")
        return value


async def list_machines() -> list[dict]:
    """List all machines in the app."""
    headers = {"Authorization": f"Bearer {FLY_API_TOKEN}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{FLY_MACHINES_API}/apps/{FLY_APP}/machines",
            headers=headers,
        )
        if response.status_code == 200:
            return response.json()
        print(f"Failed to list machines: {response.text}")
        return []


async def main():
    if not FLY_API_TOKEN:
        print("Error: FLY_API_TOKEN not set")
        print("Run: export FLY_API_TOKEN=your_token")
        return

    # Find running machines
    print(f"Checking machines in app: {FLY_APP}")
    machines = await list_machines()

    running = [m for m in machines if m.get("state") == "started"]
    print(f"Found {len(machines)} machines, {len(running)} running")

    for m in machines:
        print(f"  - {m['id']}: {m.get('state')} (region: {m.get('region')})")

    if not running:
        print("\nNo running machines! Start a new session in the frontend first.")
        return

    machine_id = MACHINE_ID if MACHINE_ID in [m['id'] for m in running] else running[0]['id']
    print(f"\nTesting against machine: {machine_id}")
    print(f"App: {FLY_APP}")

    # Test 1: Simple echo
    print("\n" + "="*60)
    print("TEST 1: Simple echo")
    print("="*60)
    data = await exec_command(machine_id, "echo hello")
    stdout = try_decode(data.get("stdout", ""), "stdout")
    print(f"Exit code: {data.get('exit_code')}")

    # Test 2: Read CLAUDE.md
    print("\n" + "="*60)
    print("TEST 2: Read CLAUDE.md")
    print("="*60)
    data = await exec_command(machine_id, "cat /home/claude/workspace/CLAUDE.md")
    stdout = try_decode(data.get("stdout", ""), "stdout")
    print(f"Exit code: {data.get('exit_code')}")
    print(f"Contains 'camelCase': {'camelCase' in stdout}")

    # Test 3: Find .jsonl files - search everywhere
    print("\n" + "="*60)
    print("TEST 3: Find .jsonl files (searching broadly)")
    print("="*60)

    # Check if .claude directory exists
    data = await exec_command(machine_id, "ls -la /home/claude/.claude 2>&1 || echo 'DIR NOT FOUND'")
    try_decode(data.get("stdout", ""), ".claude dir")

    # Search in multiple locations
    data = await exec_command(machine_id, "find /home/claude -name '*.jsonl' -type f 2>/dev/null | head -20")
    stdout = try_decode(data.get("stdout", ""), "stdout")
    print(f"Exit code: {data.get('exit_code')}")
    if stdout.strip():
        files = stdout.strip().split("\n")
        print(f"Found {len(files)} files:")
        for f in files[:10]:
            print(f"  - {f}")
    else:
        print("No .jsonl files found anywhere in /home/claude")

    # Also check for any claude-related directories
    print("\n--- Looking for Claude Code data directories ---")
    data = await exec_command(machine_id, "find /home/claude -type d -name '*claude*' 2>/dev/null")
    stdout = try_decode(data.get("stdout", ""), "claude dirs")

    # Check root .claude too
    data = await exec_command(machine_id, "ls -la /root/.claude 2>&1 || echo 'No /root/.claude'")
    try_decode(data.get("stdout", ""), "/root/.claude")

    # Test 4: Read messages directly from known path
    print("\n" + "="*60)
    print("TEST 4: Read messages from known paths")
    print("="*60)

    # List projects directory
    data = await exec_command(machine_id, "ls -la /home/claude/.claude/projects/ 2>&1")
    try_decode(data.get("stdout", ""), "projects dir")

    # List the workspace project directory
    data = await exec_command(machine_id, "ls -la /home/claude/.claude/projects/-home-claude-workspace/ 2>&1")
    workspace_files = try_decode(data.get("stdout", ""), "workspace dir")

    # First, find the actual .jsonl files (not in subagents)
    data = await exec_command(machine_id,
        "find /home/claude/.claude/projects/-home-claude-workspace -maxdepth 1 -name '*.jsonl' -type f")
    files_output = try_decode(data.get("stdout", ""), "find jsonl")
    print(f"Find exit code: {data.get('exit_code')}")

    content = ""
    if files_output.strip():
        # Get first file and cat it (no pipe - Fly exec doesn't handle pipes well)
        first_file = files_output.strip().split("\n")[0]
        print(f"Reading file: {first_file}")

        # Try plain cat
        data = await exec_command(machine_id, f"cat {first_file}")
        content = try_decode(data.get("stdout", ""), "cat file")
        print(f"Cat exit code: {data.get('exit_code')}")

        # If that fails, try head directly
        if not content.strip():
            print("Plain cat failed, trying head...")
            data = await exec_command(machine_id, f"head -30 {first_file}")
            content = try_decode(data.get("stdout", ""), "head file")
            print(f"Head exit code: {data.get('exit_code')}")

        # If still fails, try with bash -c
        if not content.strip():
            print("Head failed, trying bash -c...")
            data = await exec_command(machine_id, f"bash -c 'cat {first_file}'")
            content = try_decode(data.get("stdout", ""), "bash cat")
            print(f"Bash cat exit code: {data.get('exit_code')}")
    else:
        print("No .jsonl files found")

    # Parse and count message types
    if content:
        types = {}
        for line in content.strip().split("\n"):
            try:
                msg = json.loads(line)
                msg_type = msg.get("type", "unknown")
                types[msg_type] = types.get(msg_type, 0) + 1
            except:
                pass
        print(f"\nMessage types found: {types}")
        print(f"User messages: {types.get('user', 0)}")
    else:
        print("No content found in .jsonl files")


if __name__ == "__main__":
    asyncio.run(main())
