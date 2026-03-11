include $(TOPDIR)/rules.mk

PKG_NAME:=aria2bot
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

PKG_MAINTAINER:=irfanFRizki
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/aria2bot
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Aria2 Telegram Download Bot
  DEPENDS:=+aria2 +python3 +python3-pip +python3-asyncio +curl
  PKGARCH:=all
endef

define Package/aria2bot/description
  Aria2 Telegram Bot for OpenWrt.
  Control aria2 downloads via Telegram Bot.
  Includes LuCI web interface under Services > Aria2 Bot.
endef

define Package/aria2bot/conffiles
/etc/config/aria2bot
/etc/aria2/aria2.conf
endef

define Build/Compile
endef

define Package/aria2bot/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./files/usr/bin/telegram_download_bot.py $(1)/usr/bin/telegram_download_bot.py

	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/etc/init.d/aria2bot $(1)/etc/init.d/aria2bot
	$(INSTALL_BIN) ./files/etc/init.d/aria2rpc $(1)/etc/init.d/aria2rpc
	$(INSTALL_BIN) ./files/etc/init.d/aria2 $(1)/etc/init.d/aria2

	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_CONF) ./files/etc/config/aria2bot $(1)/etc/config/aria2bot

	$(INSTALL_DIR) $(1)/etc/aria2
	$(INSTALL_CONF) ./files/etc/aria2/aria2.conf $(1)/etc/aria2/aria2.conf

	$(INSTALL_DIR) $(1)/usr/lib/aria2bot
	$(INSTALL_BIN) ./files/usr/lib/aria2bot/install_deps.sh $(1)/usr/lib/aria2bot/install_deps.sh
endef

define Package/aria2bot/postinst
#!/bin/sh
set -e
echo ">>> Installing Python dependencies for Aria2 Bot..."
if [ -x /usr/lib/aria2bot/install_deps.sh ]; then
    /usr/lib/aria2bot/install_deps.sh
fi

echo ">>> Enabling services..."
/etc/init.d/aria2 enable 2>/dev/null || true
/etc/init.d/aria2rpc enable 2>/dev/null || true
/etc/init.d/aria2bot enable 2>/dev/null || true

echo ">>> Starting Aria2 services..."
/etc/init.d/aria2 start 2>/dev/null || true
/etc/init.d/aria2rpc start 2>/dev/null || true

echo ">>> Aria2 Bot installed. Configure your Telegram Bot Token at:"
echo "    LuCI > Services > Aria2 Bot > Settings"
echo "    or edit /etc/config/aria2bot directly, then run:"
echo "    /etc/init.d/aria2bot start"
exit 0
endef

define Package/aria2bot/prerm
#!/bin/sh
echo ">>> Stopping Aria2 Bot services..."
/etc/init.d/aria2bot stop 2>/dev/null || true
/etc/init.d/aria2rpc stop 2>/dev/null || true
/etc/init.d/aria2 stop 2>/dev/null || true
/etc/init.d/aria2bot disable 2>/dev/null || true
/etc/init.d/aria2rpc disable 2>/dev/null || true
/etc/init.d/aria2 disable 2>/dev/null || true
exit 0
endef

$(eval $(call BuildPackage,aria2bot))
