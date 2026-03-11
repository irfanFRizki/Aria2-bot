include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-aria2-bot-IRF
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

PKG_MAINTAINER:=irfanFRizki <https://github.com/irfanFRizki>
PKG_LICENSE:=MIT

LUCI_TITLE:=Aria2 Bot
LUCI_DESCRIPTION:=Telegram Download Bot untuk Aria2 dengan antarmuka LuCI. \
	Memungkinkan kontrol download via Telegram langsung dari OpenWrt.
LUCI_DEPENDS:=+luci-base +python3 +python3-pip +aria2

include $(TOPDIR)/feeds/luci/luci.mk

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/controller
	$(INSTALL_DATA) ./luasrc/controller/aria2bot.lua \
		$(1)/usr/lib/lua/luci/controller/

	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/model/cbi/aria2bot
	$(INSTALL_DATA) ./luasrc/model/cbi/aria2bot/settings.lua \
		$(1)/usr/lib/lua/luci/model/cbi/aria2bot/

	$(INSTALL_DIR) $(1)/usr/lib/lua/luci/view/aria2bot
	$(INSTALL_DATA) ./luasrc/view/aria2bot/*.htm \
		$(1)/usr/lib/lua/luci/view/aria2bot/

	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./root/usr/bin/telegram_download_bot.py $(1)/usr/bin/

	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./root/etc/init.d/aria2rpc $(1)/etc/init.d/
	$(INSTALL_BIN) ./root/etc/init.d/telegram_bot $(1)/etc/init.d/

	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_DATA) ./root/etc/config/aria2bot $(1)/etc/config/

	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./root/etc/uci-defaults/luci-aria2bot \
		$(1)/etc/uci-defaults/

	$(INSTALL_DIR) $(1)/etc/aria2bot
	$(INSTALL_BIN) ./root/etc/aria2bot/install-deps.sh \
		$(1)/etc/aria2bot/
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
