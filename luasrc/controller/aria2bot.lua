module("luci.controller.aria2bot", package.seeall)
function index()
    entry({"admin", "services", "aria2bot"}, cbi("aria2bot"), _("Aria2 Bot"), 10).dependent = true
end
