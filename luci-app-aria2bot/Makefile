include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-aria2bot
PKG_VERSION:=1.0.0
PKG_RELEASE:=1
PKG_MAINTAINER:=irfanFRizki
PKG_LICENSE:=MIT

LUCI_TITLE:=LuCI support for Aria2 Telegram Bot
LUCI_DEPENDS:=+aria2bot
LUCI_PKGARCH:=all

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
$(eval $(call BuildPackage,luci-app-aria2bot))
