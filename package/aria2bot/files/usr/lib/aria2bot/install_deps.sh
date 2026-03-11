#!/bin/sh
# Aria2 Bot - Dependency Installer
# Runs during package postinst

set -e

echo "=== Aria2 Bot: Installing dependencies ==="

# Update opkg
echo "[1/5] Updating package list..."
opkg update 2>/dev/null || echo "Warning: opkg update failed, continuing..."

# Install system packages
echo "[2/5] Installing system packages..."
for pkg in aria2 python3 python3-pip curl ca-certificates; do
    if opkg list-installed 2>/dev/null | grep -q "^$pkg "; then
        echo "  ✓ $pkg (already installed)"
    else
        echo "  Installing $pkg..."
        opkg install "$pkg" 2>/dev/null && echo "  ✓ $pkg" || echo "  ✗ $pkg (failed, skipped)"
    fi
done

# Install Python packages via pip
echo "[3/5] Installing Python packages..."
if command -v pip3 >/dev/null 2>&1; then
    echo "  Installing python-telegram-bot..."
    pip3 install --quiet --no-cache-dir "python-telegram-bot>=20.0" \
        --break-system-packages 2>/dev/null \
        && echo "  ✓ python-telegram-bot" \
        || echo "  ✗ python-telegram-bot (failed)"

    echo "  Installing aiohttp..."
    pip3 install --quiet --no-cache-dir aiohttp \
        --break-system-packages 2>/dev/null \
        && echo "  ✓ aiohttp" \
        || echo "  ✗ aiohttp (failed)"
else
    echo "  ✗ pip3 not found! Install dengan: opkg install python3-pip"
fi

# Create directories
echo "[4/5] Setting up directories..."
DOWNLOAD_DIR=$(uci get aria2bot.settings.download_dir 2>/dev/null || echo "/tmp/downloads")
mkdir -p "$DOWNLOAD_DIR"
mkdir -p /etc/aria2
mkdir -p /var/log

# Set executable permissions
echo "[5/5] Setting permissions..."
chmod +x /usr/bin/telegram_download_bot.py
chmod +x /etc/init.d/aria2bot
chmod +x /etc/init.d/aria2rpc
chmod +x /etc/init.d/aria2

echo ""
echo "=== Dependencies installation complete! ==="
echo ""
echo "Next steps:"
echo "  1. Go to LuCI > Services > Aria2 Bot > Settings"
echo "  2. Enter your Telegram Bot Token (from @BotFather)"
echo "  3. Enter your Telegram User ID (from @userinfobot)"
echo "  4. Set Download Directory (default: /tmp/downloads)"
echo "  5. Save & Apply"
echo "  6. Start the service from Dashboard tab"
echo ""
echo "  Or via command line:"
echo "  uci set aria2bot.settings.bot_token='YOUR_TOKEN'"
echo "  uci set aria2bot.settings.allowed_users='YOUR_USER_ID'"
echo "  uci set aria2bot.settings.enabled='1'"
echo "  uci commit aria2bot"
echo "  /etc/init.d/aria2rpc start"
echo "  /etc/init.d/aria2bot start"
echo ""
