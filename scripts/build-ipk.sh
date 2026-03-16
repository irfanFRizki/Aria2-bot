#!/bin/bash
set -e

PKG_NAME="luci-app-aria2-bot-IRF"
VERSION="${1:-1.0.0}"
ARCH="all"
DIST_DIR="dist"
IPK_FILE="${PKG_NAME}_${VERSION}_${ARCH}.ipk"

BUILD_DIR="$(mktemp -d)"
DATA_DIR="${BUILD_DIR}/data"
CTRL_DIR="${BUILD_DIR}/control"
mkdir -p "$DATA_DIR" "$CTRL_DIR"

echo "Building ${PKG_NAME} v${VERSION}..."

install -Dm644 luasrc/controller/aria2bot.lua         "${DATA_DIR}/usr/lib/lua/luci/controller/aria2bot.lua"
install -Dm644 luasrc/model/cbi/aria2bot/settings.lua "${DATA_DIR}/usr/lib/lua/luci/model/cbi/aria2bot/settings.lua"
install -Dm644 luasrc/view/aria2bot/dashboard.htm     "${DATA_DIR}/usr/lib/lua/luci/view/aria2bot/dashboard.htm"
install -Dm755 root/usr/bin/telegram_download_bot.py  "${DATA_DIR}/usr/bin/telegram_download_bot.py"
install -Dm755 root/etc/init.d/aria2rpc               "${DATA_DIR}/etc/init.d/aria2rpc"
install -Dm755 root/etc/init.d/telegram_bot           "${DATA_DIR}/etc/init.d/telegram_bot"
install -Dm644 root/etc/config/aria2bot               "${DATA_DIR}/etc/config/aria2bot"
install -Dm755 root/etc/uci-defaults/luci-aria2bot    "${DATA_DIR}/etc/uci-defaults/luci-aria2bot"
install -Dm755 root/etc/aria2bot/install-deps.sh      "${DATA_DIR}/etc/aria2bot/install-deps.sh"
install -Dm644 root/usr/share/rpcd/acl.d/luci-app-aria2bot.json "${DATA_DIR}/usr/share/rpcd/acl.d/luci-app-aria2bot.json"

INSTALLED_SIZE=$(du -sk "$DATA_DIR" | awk '{print $1}')

cat > "${CTRL_DIR}/control" << CTRL
Package: ${PKG_NAME}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: irfanFRizki <https://github.com/irfanFRizki>
Installed-Size: ${INSTALLED_SIZE}
Depends: luci-base, python3, python3-pip, aria2
Section: luci
Priority: optional
Description: Telegram Download Bot untuk Aria2 dengan antarmuka LuCI.
CTRL

cat > "${CTRL_DIR}/postinst" << 'POSTINST'
#!/bin/sh
chmod +x /etc/init.d/aria2rpc /etc/init.d/telegram_bot 2>/dev/null || true
chmod +x /etc/aria2bot/install-deps.sh /usr/bin/telegram_download_bot.py 2>/dev/null || true
install -Dm644 root/usr/share/rpcd/acl.d/luci-app-aria2bot.json "${DATA_DIR}/usr/share/rpcd/acl.d/luci-app-aria2bot.json"
[ -f /etc/uci-defaults/luci-aria2bot ] && sh /etc/uci-defaults/luci-aria2bot && rm -f /etc/uci-defaults/luci-aria2bot
rm -rf /tmp/luci-* /tmp/luci_* 2>/dev/null || true
echo "✅ Aria2 Bot installed! Buka LuCI > Services > Aria2 Bot > Settings"
exit 0
POSTINST

cat > "${CTRL_DIR}/prerm" << 'PRERM'
#!/bin/sh
/etc/init.d/telegram_bot stop    2>/dev/null || true
/etc/init.d/telegram_bot disable 2>/dev/null || true
exit 0
PRERM

chmod 755 "${CTRL_DIR}/postinst" "${CTRL_DIR}/prerm"

( cd "$DATA_DIR" && tar --numeric-owner --group=0 --owner=0 -czf "${BUILD_DIR}/data.tar.gz" . )
( cd "$CTRL_DIR" && tar --numeric-owner --group=0 --owner=0 -czf "${BUILD_DIR}/control.tar.gz" . )
printf '2.0\n' > "${BUILD_DIR}/debian-binary"

mkdir -p "$DIST_DIR"
( cd "${BUILD_DIR}" && tar --numeric-owner --group=0 --owner=0 -czf \
    "${OLDPWD}/${DIST_DIR}/${IPK_FILE}" \
    ./debian-binary ./control.tar.gz ./data.tar.gz )

rm -rf "$BUILD_DIR"
echo "✅ DONE: ${DIST_DIR}/${IPK_FILE} ($(du -sh ${DIST_DIR}/${IPK_FILE} | cut -f1))"
