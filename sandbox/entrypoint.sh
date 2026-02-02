#!/bin/bash
# sandbox/entrypoint.sh
set -euo pipefail

# Copy level exercise files to workspace
LEVEL_NUM=$(printf '%02d' "${LEVEL_NUMBER:-1}")
LEVEL_DIR=$(find /home/claude/levels -maxdepth 1 -type d -name "${LEVEL_NUM}-*" 2>/dev/null | head -1 || true)

if [ -n "$LEVEL_DIR" ] && [ -d "$LEVEL_DIR/exercise" ]; then
    cp -r "$LEVEL_DIR/exercise/"* /home/claude/workspace/
fi

# Generate random token if not provided
TTYD_TOKEN="${TTYD_TOKEN:-$(head -c 16 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24)}"

# Start ttyd with token authentication
exec ttyd -p 7681 -c "user:${TTYD_TOKEN}" bash -l
