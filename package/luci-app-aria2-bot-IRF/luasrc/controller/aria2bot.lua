module("luci.controller.aria2bot", package.seeall)

function index()
  if not nixio.fs.access("/etc/config/aria2bot") then
    return
  end

  local page = entry({"admin", "services", "aria2bot"}, firstchild(), _("Aria2 Bot"), 60)
  page.dependent = false
  page.acl_depends = { "luci-app-aria2-bot-IRF" }

  entry({"admin", "services", "aria2bot", "dashboard"},
    template("aria2bot/dashboard"), _("Dashboard"), 1)

  entry({"admin", "services", "aria2bot", "settings"},
    cbi("aria2bot"), _("Settings"), 2)

  -- AJAX endpoints
  entry({"admin", "services", "aria2bot", "action"},
    call("action_service"), nil).leaf = true

  entry({"admin", "services", "aria2bot", "status"},
    call("get_status"), nil).leaf = true
end

function get_status()
  local sys = require "luci.sys"
  local uci = require "luci.model.uci".cursor()
  local json = require "luci.jsonc"

  local bot_running = (sys.call("pgrep -f telegram_download_bot > /dev/null 2>&1") == 0)
  local aria2_running = (sys.call("pgrep -x aria2c > /dev/null 2>&1") == 0)
  local python3_ok = (sys.call("command -v python3 > /dev/null 2>&1") == 0)

  -- Check python packages
  local pylib_ok = (sys.call("python3 -c 'import telegram' > /dev/null 2>&1") == 0)
  local aiohttp_ok = (sys.call("python3 -c 'import aiohttp' > /dev/null 2>&1") == 0)

  local token = uci:get("aria2bot", "main", "bot_token") or ""
  local token_set = (token ~= "" and token ~= "xxxxxxxxxxxxxxxxxxxxxxxxx")

  -- Get download stats from aria2 RPC
  local dl_active = 0
  local dl_waiting = 0
  local dl_stopped = 0
  local rpc_ok = false

  local rpc_result = sys.exec("curl -s -X POST http://localhost:6800/jsonrpc -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"aria2.getGlobalStat\",\"id\":\"luci\",\"params\":[]}' --max-time 2 2>/dev/null")
  if rpc_result and rpc_result ~= "" then
    rpc_ok = true
    local active = rpc_result:match('"numActive":"(%d+)"')
    local waiting = rpc_result:match('"numWaiting":"(%d+)"')
    local stopped = rpc_result:match('"numStopped":"(%d+)"')
    dl_active  = tonumber(active)  or 0
    dl_waiting = tonumber(waiting) or 0
    dl_stopped = tonumber(stopped) or 0
  end

  luci.http.prepare_content("application/json")
  luci.http.write(json.stringify({
    bot_running  = bot_running,
    aria2_running = aria2_running,
    python3_ok   = python3_ok,
    pylib_ok     = pylib_ok,
    aiohttp_ok   = aiohttp_ok,
    token_set    = token_set,
    rpc_ok       = rpc_ok,
    dl_active    = dl_active,
    dl_waiting   = dl_waiting,
    dl_stopped   = dl_stopped,
  }))
end

function action_service()
  local http = require "luci.http"
  local sys  = require "luci.sys"
  local act  = http.formvalue("action") or ""
  local result = { ok = false, msg = "Unknown action" }

  if act == "start" then
    sys.call("/etc/init.d/telegram_bot start")
    result = { ok = true, msg = "Bot started" }
  elseif act == "stop" then
    sys.call("/etc/init.d/telegram_bot stop")
    result = { ok = true, msg = "Bot stopped" }
  elseif act == "restart" then
    sys.call("/etc/init.d/telegram_bot restart")
    result = { ok = true, msg = "Bot restarted" }
  elseif act == "start_aria2" then
    sys.call("/etc/init.d/aria2 start 2>/dev/null || /etc/init.d/aria2rpc start 2>/dev/null")
    result = { ok = true, msg = "Aria2 started" }
  elseif act == "install_deps" then
    sys.call("opkg update && opkg install python3 python3-pip aria2 curl 2>&1 | logger -t aria2bot-deps")
    sys.call("pip3 install python-telegram-bot aiohttp --break-system-packages 2>&1 | logger -t aria2bot-deps")
    result = { ok = true, msg = "Installing dependencies... check logread -e aria2bot-deps" }
  end

  luci.http.prepare_content("application/json")
  luci.http.write(require("luci.jsonc").stringify(result))
end
