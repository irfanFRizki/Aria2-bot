module("luci.controller.aria2bot", package.seeall)

function index()
    -- admin/services/aria2bot akan memanggil model/cbi/aria2bot.lua
    entry({"admin", "services", "aria2bot"}, cbi("aria2bot"), _("Aria2 Bot"), 10).dependent = true
end
