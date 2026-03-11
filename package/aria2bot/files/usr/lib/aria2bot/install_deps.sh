#!/bin/sh
# Aria2 Bot - Dependency Installer
# Runs during package postinst

set -e

echo "=== Aria2 Bot: Installing dependencies ==="

# Update opkg
echo "[1/4] Updating package list..."
opkg update 2>/dev/null || echo "Warning: opkg update failed, continuing..."

# Install system packages
echo "[2/4] Installing system packages..."
PKGS="aria2 python3 python3-asyncio curl ca-certificates"
for pkg in $PKGS; do
    if ! opkg list-installed | grep -q "^$pkg "; then
        echo "  Installing $pkg..."
        opkg install "$pkg" 2>/dev/null && echo "  ✓ $pkg" || echo "  ✗ $pkg (skipped)"
    else
        echo "  ✓ $pkg (already installed)"
    fi
done

# Install python packages via pip if available
echo "[3/4] Checking Python modules..."
if command -v pip3 >/dev/null 2>&1; then
    pip3 install --quiet --no-cache-dir requests 2>/dev/null && echo "  ✓ requests" || echo "  ✗ requests (optional)"
else
    echo "  pip3 not available, skipping Python pip packages"
fi

# Create download directory
echo "[4/4] Setting up directories..."
DOWNLOAD_DIR=$(uci get aria2bot.settings.download_dir 2>/dev/null || echo "/tmp/downloads")
mkdir -p "$DOWNLOAD_DIR"
mkdir -p /etc/aria2
mkdir -p /var/log

echo ""
echo "=== Dependencies installation complete! ==="
echo ""
echo "Next steps:"
echo "  1. Go to LuCI > Services > Aria2 Bot > Settings"
echo "  2. Enter your Telegram Bot Token"
echo "  3. Save & Apply"
echo "  4. Start the service"
echo ""
