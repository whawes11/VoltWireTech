#!/usr/bin/env bash
# ==============================================================================
# VoltWire Instant Live Publishing Tunnel
# Exposes local VoltWire (running on port 8080 or MAMP) to the live internet
# with instant HTTPS/SSL for testing mobile apps, external clients, and web.
# ==============================================================================

TARGET_PORT=${1:-8080}

echo "========================================================"
echo "⚡ VOLTWIRE INSTANT LIVE PUBLISHING TUNNEL"
echo "Target Local Port: $TARGET_PORT"
echo "========================================================"
echo ""

# Method 1: Cloudflare Tunnel (Free, no account needed for quick tunnels)
if command -v cloudflared >/dev/null 2>&1; then
    echo "▶ Launching Cloudflare Tunnel on port $TARGET_PORT..."
    echo "  (Your temporary public HTTPS URL will be displayed below)"
    cloudflared tunnel --url "http://localhost:$TARGET_PORT"
    exit 0
fi

# Method 2: ngrok
if command -v ngrok >/dev/null 2>&1; then
    echo "▶ Launching ngrok on port $TARGET_PORT..."
    ngrok http "$TARGET_PORT"
    exit 0
fi

# Fallback instructions if neither tool is installed
echo "To publish your local VoltWire server to the live internet instantly:"
echo ""
echo "Option 1 (Recommended - 100% Free with Cloudflare):"
echo "  brew install cloudflared"
echo "  cloudflared tunnel --url http://localhost:$TARGET_PORT"
echo ""
echo "Option 2 (ngrok):"
echo "  brew install ngrok"
echo "  ngrok http $TARGET_PORT"
echo ""
echo "Both tools provide an instant https:// public URL you can enter into"
echo "capacitor.config.json or share with external clients and technicians."
