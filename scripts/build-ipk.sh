#!/bin/bash
# scripts/build-ipk.sh
# Build IPK package without the full OpenWrt SDK
# Works for architecture-independent packages (PKGARCH=all)
# Usage: ./scripts/build-ipk.sh [VERSION]

set -e

PKG_NAME="luci-app-aria2-bot-IRF"
VERSION="${1:-1.0.0}"
ARCH="all"
MAINTAINER="irfanFRizki <https://github.com/irfanFRizki>"
DEPENDS="luci-base, python3, python3-pip, aria2"
DESCRIPTION="Telegram Download Bot untuk Aria2 dengan antarmuka LuCI.\n Memungkinkan kontrol download via Telegram langsung dari OpenWrt."

# Output file
DIST_DIR="dist"
IPK_FILE="${DIST_DIR}/${PKG_NAME}_${VERSION}_${ARCH}.ipk"

# Temp build dirs
BUILD_DIR="$(mktemp -d)"
DATA_DIR="${BUILD_DIR}/data"
CTRL_DIR="${BUILD_DIR}/control"
mkdir -p "$DATA_DIR" "$CTRL_DIR"

echo "======================================================"
echo "  Building: ${PKG_NAME}"
echo "  Version : ${VERSION}"
echo "  Output  : ${IPK_FILE}"
echo "======================================================"

# ── 1. Populate DATA directory ────────────────────────────────────
echo "[1/5] Copying package files..."

# LuCI controller
install -Dm644 luasrc/controller/aria2bot.lua \
    "${DATA_DIR}/usr/lib/lua/luci/controller/aria2bot.lua"

# LuCI CBI model
install -Dm644 luasrc/model/cbi/aria2bot/settings.lua \
    "${DATA_DIR}/usr/lib/lua/luci/model/cbi/aria2bot/settings.lua"

# LuCI view templates
install -Dm644 luasrc/view/aria2bot/dashboard.htm \
    "${DATA_DIR}/usr/lib/lua/luci/view/aria2bot/dashboard.htm"

# Bot Python script
install -Dm755 root/usr/bin/telegram_download_bot.py \
    "${DATA_DIR}/usr/bin/telegram_download_bot.py"

# Init.d scripts
install -Dm755 root/etc/init.d/aria2rpc \
    "${DATA_DIR}/etc/init.d/aria2rpc"
install -Dm755 root/etc/init.d/telegram_bot \
    "${DATA_DIR}/etc/init.d/telegram_bot"

# UCI config (only install if not already present — handled by postinst)
install -Dm644 root/etc/config/aria2bot \
    "${DATA_DIR}/etc/config/aria2bot"

# UCI defaults
install -Dm755 root/etc/uci-defaults/luci-aria2bot \
    "${DATA_DIR}/etc/uci-defaults/luci-aria2bot"

# Dependency installer
install -Dm755 root/etc/aria2bot/install-deps.sh \
    "${DATA_DIR}/etc/aria2bot/install-deps.sh"

# ── 2. Compute installed size ─────────────────────────────────────
INSTALLED_SIZE=$(du -sk "$DATA_DIR" | awk '{print $1}')

# ── 3. Write CONTROL files ────────────────────────────────────────
echo "[2/5] Writing control files..."

cat > "${CTRL_DIR}/control" << EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Installed-Size: ${INSTALLED_SIZE}
Depends: ${DEPENDS}
Section: luci
Priority: optional
Description: ${DESCRIPTION}
EOF

# ── postinst script ───────────────────────────────────────────────
cat > "${CTRL_DIR}/postinst" << 'POSTINST'
#!/bin/sh
# Post-install script

echo "=== Aria2 Bot: Post-install setup ==="

# Make scripts executable
chmod +x /etc/init.d/aria2rpc      2>/dev/null || true
chmod +x /etc/init.d/telegram_bot  2>/dev/null || true
chmod +x /etc/aria2bot/install-deps.sh 2>/dev/null || true
chmod +x /etc/uci-defaults/luci-aria2bot 2>/dev/null || true
chmod +x /usr/bin/telegram_download_bot.py 2>/dev/null || true

# Run uci-defaults (first-time setup)
if [ -f /etc/uci-defaults/luci-aria2bot ]; then
    sh /etc/uci-defaults/luci-aria2bot && \
        rm -f /etc/uci-defaults/luci-aria2bot
fi

# Clear LuCI cache so new menu appears immediately
rm -rf /tmp/luci-*        2>/dev/null || true
rm -rf /tmp/luci_*        2>/dev/null || true

echo "=== Instalasi selesai! ==="
echo ""
echo "  ✅ Buka LuCI > Services > Aria2 Bot > Settings"
echo "     untuk mengatur Telegram Bot Token dan Chat ID."
echo ""
echo "  📦 Instalasi Python dependency berjalan di background."
echo "     Cek log: tail -f /tmp/aria2bot-install.log"
echo ""

exit 0
POSTINST

# ── prerm script ──────────────────────────────────────────────────
cat > "${CTRL_DIR}/prerm" << 'PRERM'
#!/bin/sh
# Pre-remove script

echo "=== Aria2 Bot: Menghentikan layanan ==="

/etc/init.d/telegram_bot stop   2>/dev/null || true
/etc/init.d/telegram_bot disable 2>/dev/null || true
/etc/init.d/aria2rpc disable    2>/dev/null || true

# Note: we do NOT stop aria2rpc here because the user may use it independently

echo "=== Layanan dihentikan ==="
exit 0
PRERM

chmod 755 "${CTRL_DIR}/postinst" "${CTRL_DIR}/prerm"

# ── 4. Create tarballs ────────────────────────────────────────────
echo "[3/5] Creating tarballs..."

# data.tar.gz — from inside the data dir so paths start with ./
( cd "$DATA_DIR" && tar czf "${BUILD_DIR}/data.tar.gz" . )

# control.tar.gz — from inside the control dir
( cd "$CTRL_DIR" && tar czf "${BUILD_DIR}/control.tar.gz" . )

# debian-binary
echo "2.0" > "${BUILD_DIR}/debian-binary"

# ── 5. Pack as .ipk (ar archive) ─────────────────────────────────
echo "[4/5] Packing IPK..."
mkdir -p "$DIST_DIR"

ar rcs "$IPK_FILE" \
    "${BUILD_DIR}/debian-binary" \
    "${BUILD_DIR}/control.tar.gz" \
    "${BUILD_DIR}/data.tar.gz"

# ── Cleanup ───────────────────────────────────────────────────────
rm -rf "$BUILD_DIR"
echo "[5/5] Cleanup done."

echo ""
echo "======================================================"
echo "  ✅ IPK built successfully!"
echo "  📦 File : ${IPK_FILE}"
echo "  📏 Size : $(du -sh ${IPK_FILE} | cut -f1)"
echo "======================================================"
echo ""
echo "  Install di router:"
echo "  scp ${IPK_FILE} root@192.168.1.1:/tmp/"
echo "  ssh root@192.168.1.1 opkg install /tmp/$(basename ${IPK_FILE})"
echo ""
