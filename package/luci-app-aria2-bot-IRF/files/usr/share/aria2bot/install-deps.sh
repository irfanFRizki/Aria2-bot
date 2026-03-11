#!/bin/sh
# Auto-install dependencies for luci-app-aria2-bot-IRF
# Maintainer: irfanFRizki

LOG="/tmp/aria2bot-install.log"
exec > "$LOG" 2>&1

echo "============================================"
echo " Aria2 Bot - Dependency Installer"
echo " $(date)"
echo "============================================"

# Update package list
echo ""
echo "[1/6] Updating package list..."
opkg update
if [ $? -ne 0 ]; then
    echo "WARNING: opkg update gagal. Lanjut dengan cache yang ada."
fi

# Install aria2
echo ""
echo "[2/6] Checking aria2..."
if command -v aria2c >/dev/null 2>&1; then
    echo "aria2 sudah terinstall: $(aria2c --version | head -1)"
else
    echo "Menginstall aria2..."
    opkg install aria2
    if [ $? -eq 0 ]; then
        echo "aria2 berhasil diinstall"
    else
        echo "ERROR: Gagal install aria2"
    fi
fi

# Install curl
echo ""
echo "[3/6] Checking curl..."
if command -v curl >/dev/null 2>&1; then
    echo "curl sudah terinstall"
else
    opkg install curl
fi

# Install python3
echo ""
echo "[4/6] Checking python3..."
if command -v python3 >/dev/null 2>&1; then
    echo "python3 sudah terinstall: $(python3 --version)"
else
    echo "Menginstall python3..."
    opkg install python3
    if [ $? -ne 0 ]; then
        echo "ERROR: Gagal install python3"
        exit 1
    fi
fi

# Install pip
echo ""
echo "[5/6] Checking pip3..."
if ! command -v pip3 >/dev/null 2>&1; then
    echo "Menginstall python3-pip..."
    opkg install python3-pip
fi

# Upgrade pip
python3 -m pip install --upgrade pip --quiet

# Install python packages
echo ""
echo "[6/6] Installing Python packages via pip..."

echo "  Installing python-telegram-bot[all]..."
pip3 install "python-telegram-bot[all]" --quiet
if [ $? -eq 0 ]; then
    echo "  ✅ python-telegram-bot berhasil"
else
    echo "  Mencoba versi stable..."
    pip3 install "python-telegram-bot==20.8" --quiet
fi

echo "  Installing aiohttp..."
pip3 install aiohttp --quiet
if [ $? -eq 0 ]; then
    echo "  ✅ aiohttp berhasil"
else
    echo "  ERROR: Gagal install aiohttp"
fi

echo ""
echo "============================================"
echo " VERIFIKASI INSTALASI:"
echo "============================================"

check_pkg() {
    python3 -c "import $1" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✅ $1: OK"
    else
        echo "  ❌ $1: GAGAL"
    fi
}

check_pkg telegram
check_pkg aiohttp
check_pkg asyncio

echo ""
if command -v aria2c >/dev/null 2>&1; then
    echo "  ✅ aria2c: OK ($(aria2c --version | head -1))"
else
    echo "  ❌ aria2c: GAGAL"
fi

echo ""
echo "============================================"
echo " Instalasi selesai! $(date)"
echo " Silakan start bot dari LuCI > Services > Aria2 Bot > Dashboard"
echo "============================================"
