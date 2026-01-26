"""Spike: Test reading Claude's messages.jsonl from sandbox."""
import modal

app = modal.App("claude-game-spike-messages")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("nodejs", "npm", "curl")
    .run_commands(
        "npm install -g @anthropic-ai/claude-code",
        "useradd -m -s /bin/bash claude",
        "mkdir -p /home/claude/.claude/projects",
        "chown -R claude:claude /home/claude",
    )
)

@app.function(image=image, timeout=300, secrets=[modal.Secret.from_name("anthropic-credentials")])
def test_messages_read() -> dict:
    import subprocess
    import glob
    import os
    import json

    result_data = {
        "success": False,
        "logs": [],
        "claude_exit_code": None,
        "claude_stdout": "",
        "claude_stderr": "",
        "jsonl_files": [],
        "messages": [],
    }

    def log(msg):
        result_data["logs"].append(msg)

    # Setup credentials (try both key names)
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_KEY")
    if not api_key:
        log("FAILED: No ANTHROPIC_API_KEY or ANTHROPIC_KEY in environment")
        return result_data

    log("Setting up credentials...")
    creds = {"apiKey": api_key}
    os.makedirs("/home/claude/.claude", exist_ok=True)
    with open("/home/claude/.claude/.credentials.json", "w") as f:
        json.dump(creds, f)
    os.system("chown -R claude:claude /home/claude/.claude")
    os.system("chmod 600 /home/claude/.claude/.credentials.json")

    # Run a simple Claude command
    log("Running Claude with a simple prompt...")
    try:
        proc_result = subprocess.run(
            ["su", "-", "claude", "-c",
             "cd /home/claude && claude -p --dangerously-skip-permissions 'say hello' </dev/null"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        result_data["claude_exit_code"] = proc_result.returncode
        result_data["claude_stdout"] = proc_result.stdout[:2000]
        result_data["claude_stderr"] = proc_result.stderr[:2000]
        log(f"Claude exit code: {proc_result.returncode}")
    except subprocess.TimeoutExpired:
        log("Claude command timed out after 120s")
        return result_data
    except Exception as e:
        log(f"Claude command failed: {e}")
        return result_data

    # Debug: show directory structure
    log("Checking directory structure...")
    find_result = subprocess.run(
        ["find", "/home/claude/.claude", "-type", "f"],
        capture_output=True,
        text=True,
    )
    log(f"Files in .claude dir: {find_result.stdout}")

    # Find and read messages.jsonl
    patterns = [
        "/home/claude/.claude/projects/**/*.jsonl",
        "/home/claude/.claude/**/*.jsonl",
        "/home/claude/**/*.jsonl",
    ]

    jsonl_files = []
    for pattern in patterns:
        jsonl_files = glob.glob(pattern, recursive=True)
        if jsonl_files:
            log(f"Found {len(jsonl_files)} .jsonl files with pattern: {pattern}")
            break

    result_data["jsonl_files"] = jsonl_files

    if not jsonl_files:
        log("No .jsonl files found anywhere")
        return result_data

    # Read first jsonl file
    for f in jsonl_files[:1]:
        log(f"Reading file: {f}")
        with open(f, "r") as fp:
            lines = fp.readlines()[:10]
            for i, line in enumerate(lines):
                try:
                    data = json.loads(line)
                    msg_type = data.get('type', 'unknown')
                    result_data["messages"].append({
                        "line": i + 1,
                        "type": msg_type,
                    })
                except json.JSONDecodeError as e:
                    log(f"JSON decode error on line {i+1}: {e}")

    result_data["success"] = len(jsonl_files) > 0
    return result_data

if __name__ == "__main__":
    with app.run():
        result = test_messages_read.remote()

        print("\n" + "="*60)
        print("SPIKE RESULTS: Test Reading messages.jsonl from Sandbox")
        print("="*60)

        print("\nLogs:")
        for log in result["logs"]:
            print(f"  {log}")

        print(f"\nClaude exit code: {result['claude_exit_code']}")

        if result["claude_stdout"]:
            print(f"\nClaude stdout (truncated):\n{result['claude_stdout'][:500]}")

        if result["claude_stderr"]:
            print(f"\nClaude stderr (truncated):\n{result['claude_stderr'][:500]}")

        print(f"\nJSONL files found: {result['jsonl_files']}")

        if result["messages"]:
            print("\nMessage types found:")
            for msg in result["messages"]:
                print(f"  Line {msg['line']}: {msg['type']}")

        print(f"\n{'='*60}")
        print(f"Test result: {'PASS' if result['success'] else 'FAIL'}")
