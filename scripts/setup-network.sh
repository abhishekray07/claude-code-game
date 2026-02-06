#!/usr/bin/env bash
# Create the sandbox-net Docker network with egress restrictions.
# Blocks access to private networks, allows DNS (53) and HTTPS (443).
# Safe to run multiple times — handles "already exists" gracefully.
#
# Usage: sudo bash scripts/setup-network.sh

set -euo pipefail

NETWORK="sandbox-net"
SUBNET="172.30.0.0/16"

# Create the network if it doesn't already exist
if docker network inspect "$NETWORK" >/dev/null 2>&1; then
    echo "Network '$NETWORK' already exists — skipping creation."
else
    docker network create \
        --driver bridge \
        --subnet "$SUBNET" \
        "$NETWORK"
    echo "Created network '$NETWORK' ($SUBNET)."
fi

# Get the bridge interface name for our network
BRIDGE=$(docker network inspect "$NETWORK" -f '{{.Options.com.docker.network.bridge.name}}' 2>/dev/null)
if [ -z "$BRIDGE" ]; then
    # Docker auto-generates bridge names like br-<id>
    BRIDGE=$(docker network inspect "$NETWORK" -f '{{.Id}}' | head -c 12 | xargs -I{} echo "br-{}")
fi

echo "Bridge interface: $BRIDGE"

# Flush existing DOCKER-USER rules for this bridge to make script idempotent
iptables -F DOCKER-USER 2>/dev/null || true

# Default: allow established connections (return traffic)
iptables -A DOCKER-USER -i "$BRIDGE" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN

# Allow DNS (UDP + TCP port 53)
iptables -A DOCKER-USER -i "$BRIDGE" -p udp --dport 53 -j RETURN
iptables -A DOCKER-USER -i "$BRIDGE" -p tcp --dport 53 -j RETURN

# Allow HTTPS (TCP port 443) — needed for Anthropic API
iptables -A DOCKER-USER -i "$BRIDGE" -p tcp --dport 443 -j RETURN

# Block private networks (RFC 1918 + link-local + loopback)
iptables -A DOCKER-USER -i "$BRIDGE" -d 10.0.0.0/8 -j DROP
iptables -A DOCKER-USER -i "$BRIDGE" -d 172.16.0.0/12 -j DROP
iptables -A DOCKER-USER -i "$BRIDGE" -d 192.168.0.0/16 -j DROP
iptables -A DOCKER-USER -i "$BRIDGE" -d 169.254.0.0/16 -j DROP
iptables -A DOCKER-USER -i "$BRIDGE" -d 127.0.0.0/8 -j DROP

# Allow everything else (public internet on allowed ports)
iptables -A DOCKER-USER -i "$BRIDGE" -j RETURN

echo "Egress rules applied for '$NETWORK'."
echo "Allowed: DNS (53), HTTPS (443). Blocked: private networks."
