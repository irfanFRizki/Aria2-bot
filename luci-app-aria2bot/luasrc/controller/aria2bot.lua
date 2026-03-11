-- LuCI Controller: Aria2 Bot
-- Menu: Services > Aria2 Bot

module("luci.controller.aria2bot", package.seeall)

function index()
    if not nixio.fs.access("/etc/config/aria2bot") then
        return
    end

    local page

    -- Parent menu entry
    entry({"admin", "services", "aria2bot"},
        firstchild(),
        _("Aria2 Bot"),
        60
    ).dependent = false

    -- Dashboard
    entry({"admin", "services", "aria2bot", "dashboard"},
        template("aria2bot/dashboard"),
        _("Dashboard"),
        1
    )

    -- Settings
    entry({"admin", "services", "aria2bot", "settings"},
        cbi("aria2bot/settings"),
        _("Settings"),
        2
    )

    -- API endpoints (JSON)
    entry({"admin", "services", "aria2bot", "api", "status"},
        call("api_status")
    ).leaf = true

    entry({"admin", "services", "aria2bot", "api", "service"},
        call("api_service")
    ).leaf = true

    entry({"admin", "services", "aria2bot", "api", "aria2"},
        call("api_aria2")
    ).leaf = true
end

-- ── API: Service status ──────────────────────────────────────────────────

function api_status()
    local sys = require("luci.sys")
    local uci = require("luci.model.uci").cursor()

    local enabled   = uci:get("aria2bot", "settings", "enabled") or "0"
    local bot_token = uci:get("aria2bot", "settings", "bot_token") or ""
    local rpc_url   = uci:get("aria2bot", "settings", "aria2_rpc_url") or "http://localhost:6800/jsonrpc"

    local bot_running   = (sys.call("pgrep -f telegram_download_bot.py > /dev/null 2>&1") == 0)
    local aria2_running = (sys.call("pgrep -x aria2c > /dev/null 2>&1") == 0)

    luci.http.prepare_content("application/json")
    luci.http.write(require("luci.jsonc").stringify({
        enabled       = (enabled == "1"),
        bot_token_set = (bot_token ~= "" and #bot_token > 10),
        bot_running   = bot_running,
        aria2_running = aria2_running,
        rpc_url       = rpc_url,
    }))
end

-- ── API: Service control ─────────────────────────────────────────────────

function api_service()
    local action = luci.http.formvalue("action") or ""
    local sys = require("luci.sys")
    local result = { ok = false, msg = "" }

    if action == "start_bot" then
        sys.call("/etc/init.d/aria2bot start")
        result = { ok = true, msg = "Bot started" }
    elseif action == "stop_bot" then
        sys.call("/etc/init.d/aria2bot stop")
        result = { ok = true, msg = "Bot stopped" }
    elseif action == "restart_bot" then
        sys.call("/etc/init.d/aria2bot restart")
        result = { ok = true, msg = "Bot restarted" }
    elseif action == "start_aria2" then
        sys.call("/etc/init.d/aria2rpc start")
        result = { ok = true, msg = "Aria2 started" }
    elseif action == "stop_aria2" then
        sys.call("/etc/init.d/aria2rpc stop")
        result = { ok = true, msg = "Aria2 stopped" }
    elseif action == "restart_aria2" then
        sys.call("/etc/init.d/aria2rpc restart")
        result = { ok = true, msg = "Aria2 restarted" }
    else
        result = { ok = false, msg = "Unknown action" }
    end

    luci.http.prepare_content("application/json")
    luci.http.write(require("luci.jsonc").stringify(result))
end

-- ── API: Aria2 RPC proxy ─────────────────────────────────────────────────

function api_aria2()
    local uci    = require("luci.model.uci").cursor()
    local jsonc  = require("luci.jsonc")
    local rpc_url = uci:get("aria2bot", "settings", "aria2_rpc_url") or "http://localhost:6800/jsonrpc"
    local secret  = uci:get("aria2bot", "settings", "aria2_secret") or ""
    local method  = luci.http.formvalue("method") or "aria2.getGlobalStat"

    -- Build payload
    local params = {}
    if secret ~= "" then
        table.insert(params, "token:" .. secret)
    end

    local payload = jsonc.stringify({
        jsonrpc = "2.0",
        id      = "luci",
        method  = method,
        params  = params
    })

    -- Call aria2 RPC using wget (available on OpenWrt)
    local tmpfile = "/tmp/aria2_rpc_resp.json"
    local cmd = string.format(
        "wget -q -O %s --post-data '%s' --header 'Content-Type: application/json' '%s' 2>/dev/null",
        tmpfile, payload, rpc_url
    )
    os.execute(cmd)

    local f = io.open(tmpfile, "r")
    local resp = f and f:read("*a") or "{}"
    if f then f:close() end
    os.remove(tmpfile)

    luci.http.prepare_content("application/json")
    luci.http.write(resp)
end
