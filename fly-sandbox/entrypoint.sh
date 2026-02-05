#!/bin/bash
# Copy exercise files for the current level to workspace
LEVEL_NUM=$(printf '%02d' ${LEVEL_NUMBER:-1})
LEVEL_DIR=$(find /home/claude/levels -maxdepth 1 -type d -name "${LEVEL_NUM}-*" | head -1)

if [ -n "$LEVEL_DIR" ] && [ -d "$LEVEL_DIR/exercise" ]; then
    cp -r "$LEVEL_DIR/exercise/"* /home/claude/workspace/
fi

# Start ttyd on internal port 7682
ttyd -p 7682 bash -l &
TTYD_PID=$!

# Wait for ttyd to be ready
sleep 1

# Start the router on port 7681 (external port)
node /home/claude/router.js &
ROUTER_PID=$!

echo "Started ttyd (PID: $TTYD_PID) and router (PID: $ROUTER_PID)"

# Wait for either process to exit
wait -n $TTYD_PID $ROUTER_PID

# If one exits, kill the other
kill $TTYD_PID $ROUTER_PID 2>/dev/null
