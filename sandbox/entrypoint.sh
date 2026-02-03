#!/bin/bash
# sandbox/entrypoint.sh
set -euo pipefail

# Copy level exercise files to workspace
LEVEL_NUM=$(printf '%02d' "${LEVEL_NUMBER:-1}")
LEVEL_DIR=$(find /home/claude/levels -maxdepth 1 -type d -name "${LEVEL_NUM}-*" 2>/dev/null | head -1 || true)

if [ -n "$LEVEL_DIR" ] && [ -d "$LEVEL_DIR/exercise" ]; then
    cp -r "$LEVEL_DIR/exercise/"* /home/claude/workspace/
fi

# Start ttyd without authentication (port only accessible on localhost via Docker port mapping)
exec ttyd -p 7681 bash -l
