include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-aria2-bot-IRF
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)

include $(INCLUDE_DIR)/package.mk

define Package/luci-app-aria2-bot-IRF
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=Aria2 Bot - Telegram Download Bot
  DEPENDS:=+luci-base +python3 +aria2 +curl
  PKGARCH:=all
endef

define Package/luci-app-aria2-bot-IRF/description
  LuCI interface for Aria2 Telegram Download Bot by irfanFRizki.
  Includes Dashboard and Settings UI.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/luci-app-aria2-bot-IRF/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./root/usr/bin/telegram_download_bot.py $(1)/usr/bin/telegram_download_bot.py

	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./root/etc/init.d/telegram_bot $(1)/etc/init.d/telegram_bot

	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_CONF) ./root/etc/config/aria2bot $(1)/etc/config/aria2bot

	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./root/etc/uci-defaults/luci-aria2bot $(1)/etc/uci-defaults/luci-aria2bot

	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/controller
	$(INSTALL_DATA) ./luasrc/controller/aria2bot.lua $(1)/usr/lib/lua/luci/controller/aria2bot.lua

	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/model/cbi
	$(INSTALL_DATA) ./luasrc/model/cbi/aria2bot.lua $(1)/usr/lib/lua/luci/model/cbi/aria2bot.lua

	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/view/aria2bot
	$(INSTALL_DATA) ./luasrc/view/aria2bot/dashboard.htm $(1)/usr/lib/lua/luci/view/aria2bot/dashboard.htm
endef

define Package/luci-app-aria2-bot-IRF/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
  /etc/uci-defaults/luci-aria2bot 2>/dev/null
  /etc/init.d/telegram_bot enable
  echo "==================================="
  echo "  Aria2 Bot berhasil diinstall!"
  echo "  Buka LuCI: Services > Aria2 Bot"
  echo "==================================="
}
exit 0
endef

define Package/luci-app-aria2-bot-IRF/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
  /etc/init.d/telegram_bot stop 2>/dev/null
  /etc/init.d/telegram_bot disable 2>/dev/null
}
exit 0
endef

$(eval $(call BuildPackage,luci-app-aria2-bot-IRF))
