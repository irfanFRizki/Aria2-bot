-- LuCI Controller for Aria2 Bot
-- /usr/lib/lua/luci/controller/aria2bot.lua

module("luci.controller.aria2bot", package.seeall)

local http   = require "luci.http"
local sys    = require "luci.sys"
local uci    = require "luci.model.uci".cursor()

function index()
    local page = entry(
        {"admin", "services", "aria2bot"},
        firstchild(),
        _("Aria2 Bot"),
        60
    )
    page.dependent = false
    page.acl_depends = { "luci-app-aria2-bot-IRF" }

    entry(
        {"admin", "services", "aria2bot", "dashboard"},
        template("aria2bot/dashboard"),
        _("Dashboard"),
        10
    ).leaf = true

    entry(
        {"admin", "services", "aria2bot", "settings"},
        cbi("aria2bot/settings"),
        _("Settings"),
        20
    ).leaf = true

    -- AJAX endpoints
    entry({"admin", "services", "aria2bot", "api_status"},
          call("action_api_status")).leaf = true

    entry({"admin", "services", "aria2bot", "api_control"},
          call("action_api_control")).leaf = true

    entry({"admin", "services", "aria2bot", "api_log"},
          call("action_api_log")).leaf = true
end

-- =====================================================
-- API: return JSON status of services
-- =====================================================
function action_api_status()
    local bot_running   = (sys.call("pgrep -f telegram_download_bot.py >/dev/null 2>&1") == 0)
    local aria2_running = (sys.call("pgrep -x aria2c >/dev/null 2>&1") == 0)

    -- Read config values for display
    local token   = uci:get("aria2bot", "settings", "bot_token") or ""
    local chat_id = uci:get("aria2bot", "settings", "chat_id") or ""
    local rpc_url = uci:get("aria2bot", "settings", "aria2_rpc_url") or "http://localhost:6800/jsonrpc"

    -- Mask token for display: show first 8 chars + ***
    local token_display = "Not set"
    if #token > 8 then
        token_display = token:sub(1,8) .. "***"
    elseif #token > 0 then
        token_display = "***"
    end

    local configured = (#token > 0 and #chat_id > 0)

    http.prepare_content("application/json")
    http.write_json({
        bot_running   = bot_running,
        aria2_running = aria2_running,
        configured    = configured,
        token_display = token_display,
        chat_id       = chat_id,
        rpc_url       = rpc_url,
    })
end

-- =====================================================
-- API: service control actions
-- =====================================================
function action_api_control()
    local action = http.formvalue("action") or ""
    local result = { success = false, message = "" }

    if action == "start_bot" then
        sys.call("/etc/init.d/telegram_bot start >/dev/null 2>&1")
        result = { success = true, message = "Bot started" }

    elseif action == "stop_bot" then
        sys.call("/etc/init.d/telegram_bot stop >/dev/null 2>&1")
        result = { success = true, message = "Bot stopped" }

    elseif action == "restart_bot" then
        sys.call("/etc/init.d/telegram_bot restart >/dev/null 2>&1")
        result = { success = true, message = "Bot restarted" }

    elseif action == "enable_bot" then
        sys.call("/etc/init.d/telegram_bot enable >/dev/null 2>&1")
        result = { success = true, message = "Bot enabled on boot" }

    elseif action == "disable_bot" then
        sys.call("/etc/init.d/telegram_bot disable >/dev/null 2>&1")
        result = { success = true, message = "Bot disabled from boot" }

    elseif action == "start_aria2" then
        sys.call("/etc/init.d/aria2rpc start >/dev/null 2>&1")
        result = { success = true, message = "Aria2 started" }

    elseif action == "stop_aria2" then
        sys.call("/etc/init.d/aria2rpc stop >/dev/null 2>&1")
        result = { success = true, message = "Aria2 stopped" }

    elseif action == "restart_aria2" then
        sys.call("/etc/init.d/aria2rpc restart >/dev/null 2>&1")
        result = { success = true, message = "Aria2 restarted" }

    elseif action == "install_deps" then
        sys.call("/etc/aria2bot/install-deps.sh >/tmp/aria2bot-install.log 2>&1 &")
        result = { success = true, message = "Installing dependencies in background. Check log at /tmp/aria2bot-install.log" }

    else
        result = { success = false, message = "Unknown action: " .. action }
    end

    http.prepare_content("application/json")
    http.write_json(result)
end

-- =====================================================
-- API: tail log file
-- =====================================================
function action_api_log()
    local lines = http.formvalue("lines") or "50"
    lines = tonumber(lines) or 50
    if lines > 200 then lines = 200 end

    local log_output = sys.exec(
        string.format("logread 2>/dev/null | grep -i 'telegram_download_bot\\|aria2' | tail -n %d", lines)
    ) or ""

    if log_output == "" then
        log_output = sys.exec(
            string.format("tail -n %d /tmp/aria2rpc.log 2>/dev/null", lines)
        ) or "No logs available"
    end

    http.prepare_content("application/json")
    http.write_json({ log = log_output })
end
