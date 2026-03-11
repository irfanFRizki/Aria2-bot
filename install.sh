#!/bin/sh
# Auto-install script untuk Aria2 Bot di OpenWrt
# Usage: sh install.sh

set -e

echo "============================================"
echo "  Aria2 Bot - Auto Installer for OpenWrt"
echo "  by irfanFRizki"
echo "============================================"
echo ""

# 1. Update opkg
echo "[1/5] Update opkg..."
opkg update

# 2. Install system deps
echo "[2/5] Install system dependencies..."
opkg install python3 python3-pip aria2 curl wget 2>/dev/null || true

# 3. Install Python packages
echo "[3/5] Install Python packages..."
pip3 install python-telegram-bot aiohttp --break-system-packages 2>/dev/null || \
pip3 install python-telegram-bot aiohttp

# 4. Download latest IPK
echo "[4/5] Download latest IPK..."
LATEST_URL=$(wget -qO- "https://api.github.com/repos/irfanFRizki/Aria2-bot/releases/latest" 2>/dev/null | \
  grep "browser_download_url.*\.ipk" | head -1 | cut -d'"' -f4)

if [ -n "$LATEST_URL" ]; then
  wget -O /tmp/aria2bot.ipk "$LATEST_URL"
  echo "[5/5] Install IPK..."
  opkg install --force-reinstall /tmp/aria2bot.ipk
  rm -f /tmp/aria2bot.ipk
else
  echo "  [!] Tidak bisa ambil release terbaru dari GitHub"
  echo "  Download manual dari: https://github.com/irfanFRizki/Aria2-bot/releases"
  exit 1
fi

echo ""
echo "============================================"
echo "  ✅ Instalasi selesai!"
echo ""
echo "  Langkah selanjutnya:"
echo "  1. Buka LuCI: http://192.168.1.1"
echo "  2. Pergi ke: Services > Aria2 Bot > Settings"
echo "  3. Isi Bot Token dari @BotFather"
echo "  4. Isi User ID kamu (dari @userinfobot)"
echo "  5. Klik Save & Apply"
echo "  6. Klik Start Bot di Dashboard"
echo "============================================"
