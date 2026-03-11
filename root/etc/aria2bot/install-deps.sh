#!/bin/sh
# install-deps.sh — Install semua Python dependency untuk Aria2 Bot
# Dipanggil otomatis saat pertama kali install atau dari LuCI dashboard

LOG_TAG="aria2bot-deps"

_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    logger -t "$LOG_TAG" "$*"
}

_log "=== Memulai instalasi dependency Aria2 Bot ==="

# ── 1. Pastikan opkg update ────────────────────────────
_log "Menjalankan opkg update..."
opkg update 2>&1 | tail -3
if [ $? -ne 0 ]; then
    _log "WARNING: opkg update gagal. Melanjutkan dengan cache..."
fi

# ── 2. Install paket opkg yang diperlukan ─────────────
_log "Menginstall paket system..."
OPKG_PKGS="python3 python3-pip python3-asyncio python3-aiohttp aria2"
for pkg in $OPKG_PKGS; do
    if ! opkg status "$pkg" 2>/dev/null | grep -q "Status: install ok installed"; then
        _log "  Install: $pkg"
        opkg install "$pkg" 2>&1
    else
        _log "  OK (sudah ada): $pkg"
    fi
done

# ── 3. Upgrade pip ────────────────────────────────────
_log "Mengupgrade pip..."
pip3 install --upgrade pip 2>&1 | tail -2

# ── 4. Install Python packages via pip ───────────────
_log "Menginstall python-telegram-bot..."
pip3 install "python-telegram-bot[job-queue]" 2>&1
if [ $? -eq 0 ]; then
    _log "  python-telegram-bot: OK"
else
    _log "  python-telegram-bot: GAGAL - coba tanpa extras..."
    pip3 install "python-telegram-bot" 2>&1
fi

_log "Menginstall aiohttp..."
pip3 install aiohttp 2>&1
[ $? -eq 0 ] && _log "  aiohttp: OK" || _log "  aiohttp: GAGAL"

_log "Menginstall aiofiles..."
pip3 install aiofiles 2>&1
[ $? -eq 0 ] && _log "  aiofiles: OK" || _log "  aiofiles: GAGAL"

# ── 5. Verifikasi import ──────────────────────────────
_log "Memverifikasi import..."
python3 -c "import telegram; import aiohttp; print('OK')" 2>&1
if [ $? -eq 0 ]; then
    _log "✅ Semua dependency berhasil diinstall!"
else
    _log "⚠️  Beberapa dependency mungkin belum bisa di-import."
    _log "   Cek koneksi internet dan jalankan ulang dari Dashboard."
fi

# ── 6. Ensure aria2rpc is started ────────────────────
if ! pgrep -x aria2c >/dev/null 2>&1; then
    _log "Memulai Aria2 RPC..."
    /etc/init.d/aria2rpc start 2>&1
fi

_log "=== Instalasi selesai ==="
