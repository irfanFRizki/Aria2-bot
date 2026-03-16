include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-aria2-bot-IRF
PKG_VERSION:=1.0
PKG_RELEASE:=2
PKG_MAINTAINER:=irfanFRizki

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=Telegram Bot for Aria2 Downloads
  DEPENDS:=+python3 +python3-pip +aria2 +curl +python3-telegram-bot
  PKGARCH:=all
endef

define Build/Compile
endef

define Package/$(PKG_NAME)/install
# Salin file root (config, init.d, bin)
$(CP) ./root/* $(1)/
# Salin file LuCI ke folder library Lua di OpenWrt
mkdir -p $(1)/usr/lib/lua/luci/controller
mkdir -p $(1)/usr/lib/lua/luci/model/cbi
$(CP) ./luasrc/controller/* $(1)/usr/lib/lua/luci/controller/
$(CP) ./luasrc/model/cbi/* $(1)/usr/lib/lua/luci/model/cbi/
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
