# Spike Results

**Date:** 2026-01-26
**Purpose:** Validate core assumptions for Claude Code Learning Game

---

## Task 0.1: ttyd in Modal Sandbox

- **Result:** PASS
- **Test:** `test_ttyd_modal.py`
- **Notes:**
  - ttyd compiles and installs successfully from source in Modal sandbox
  - Process starts and runs on port 7681
  - Dependencies required: `curl`, `build-essential`, `cmake`, `git`, `libjson-c-dev`, `libwebsockets-dev`
- **Alternative if failed:** N/A (passed)

---

## Task 0.2: messages.jsonl Reading

- **Result:** PASS
- **Test:** `test_messages_read.py`
- **Notes:**
  - JSONL file location: `/home/claude/.claude/projects/-home-claude/<session-id>.jsonl`
  - Message types confirmed: `queue-operation`, `user`, `assistant`
  - File is created even when Claude exits with error
  - Can parse JSON lines to extract message types and content
- **Key finding:** Claude Code stores session logs at predictable path based on working directory
- **Alternative if failed:** N/A (passed)

---

## Task 0.3: WebSocket Proxy

- **Result:** PASS
- **Test:** `test_websocket_auto.py`, `test_websocket_proxy.py`
- **Notes:**
  - websockets library works for both server and client
  - JSON data transmits correctly
  - Multiple message bidirectional communication works
  - Basic echo proxy pattern validated
- **Next step:** Real implementation needs to proxy to Modal sandbox's ttyd WebSocket
- **Alternative if failed:** N/A (passed)

---

## Decision

[x] **All passed - proceed with Phase 1**

All three core assumptions have been validated:

1. ttyd runs in Modal sandboxes
2. We can read Claude's session logs for verification
3. WebSocket proxy pattern works

---

## Additional Notes

### Modal Secret Setup

- Secret name: `anthropic-credentials`
- Environment variable: `ANTHROPIC_KEY` (not `ANTHROPIC_API_KEY`)

### Credential Setup in Sandbox

Credentials are written to `/home/claude/.claude/.credentials.json`:

```json
{ "apiKey": "sk-ant-..." }
```

### Files Created

- `test_ttyd_modal.py` - ttyd installation and startup test
- `test_messages_read.py` - JSONL reading test
- `test_websocket_proxy.py` - Manual WebSocket test with HTML client
- `test_websocket_auto.py` - Automated WebSocket test
- `test_ws_client.html` - Browser-based WebSocket test client
- `debug_secret.py` - Modal secret debugging utility

---

**Ready for Phase 1: Core Infrastructure**
