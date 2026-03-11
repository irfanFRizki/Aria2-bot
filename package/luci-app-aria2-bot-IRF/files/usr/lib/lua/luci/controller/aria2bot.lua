module("luci.controller.aria2bot", package.seeall)

function index()
    if not nixio.fs.access("/etc/config/aria2bot") then
        return
    end

    local page = entry({"admin", "services", "aria2bot"}, firstchild(), _("Aria2 Bot"), 60)
    page.dependent = false
    page.acl_depends = { "luci-app-aria2-bot-IRF" }

    entry({"admin", "services", "aria2bot", "dashboard"}, 
          template("aria2bot/dashboard"), _("Dashboard"), 10)

    entry({"admin", "services", "aria2bot", "settings"}, 
          cbi("aria2bot"), _("Settings"), 20)

    -- AJAX action endpoints
    entry({"admin", "services", "aria2bot", "action"}, 
          call("action_service"), nil)

    entry({"admin", "services", "aria2bot", "status"}, 
          call("action_status"), nil)

    entry({"admin", "services", "aria2bot", "install_deps"}, 
          call("action_install_deps"), nil)
end

function action_service()
    local http = require "luci.http"
    local sys  = require "luci.sys"
    local cmd  = http.formvalue("cmd") or ""
    local result = { success = false, message = "" }

    if cmd == "start" then
        local code = sys.call("/etc/init.d/telegram_bot start 2>&1")
        if code == 0 then
            result.success = true
            result.message = "Bot berhasil distart"
        else
            result.message = "Gagal start bot. Cek konfigurasi terlebih dahulu."
        end
    elseif cmd == "stop" then
        sys.call("/etc/init.d/telegram_bot stop 2>&1")
        result.success = true
        result.message = "Bot dihentikan"
    elseif cmd == "restart" then
        sys.call("/etc/init.d/telegram_bot restart 2>&1")
        result.success = true
        result.message = "Bot direstart"
    elseif cmd == "enable" then
        sys.call("/etc/init.d/telegram_bot enable")
        result.success = true
        result.message = "Bot diaktifkan (autostart)"
    elseif cmd == "disable" then
        sys.call("/etc/init.d/telegram_bot disable")
        result.success = true
        result.message = "Bot dinonaktifkan (autostart)"
    else
        result.message = "Perintah tidak dikenal"
    end

    http.prepare_content("application/json")
    http.write(require("luci.jsonc").stringify(result))
end

function action_status()
    local http   = require "luci.http"
    local sys    = require "luci.sys"
    local uci    = require "luci.model.uci".cursor()

    local bot_running   = (sys.call("pgrep -f telegram_download_bot > /dev/null 2>&1") == 0)
    local aria2_running = (sys.call("pgrep -x aria2c > /dev/null 2>&1") == 0)
    local python3_ok    = (sys.call("command -v python3 > /dev/null 2>&1") == 0)

    -- Cek python packages
    local pytba_ok = (sys.call("python3 -c 'import telegram' > /dev/null 2>&1") == 0)
    local aiohttp_ok = (sys.call("python3 -c 'import aiohttp' > /dev/null 2>&1") == 0)

    -- Cek autostart
    local autostart = nixio.fs.access("/etc/rc.d/S99telegram_bot")

    -- Ambil token (censor)
    local token = uci:get("aria2bot", "main", "bot_token") or ""
    local token_set = (#token > 10)
    local token_display = token_set and ("***" .. string.sub(token, -6)) or "Belum diisi"

    -- Ambil log terakhir
    local log_lines = {}
    local f = io.popen("logread 2>/dev/null | grep telegram_download_bot | tail -20")
    if f then
        for line in f:lines() do
            table.insert(log_lines, line)
        end
        f:close()
    end

    local status = {
        bot_running   = bot_running,
        aria2_running = aria2_running,
        python3_ok    = python3_ok,
        pytba_ok      = pytba_ok,
        aiohttp_ok    = aiohttp_ok,
        autostart     = autostart and true or false,
        token_display = token_display,
        token_set     = token_set,
        log_lines     = log_lines,
        version       = "1.0.0"
    }

    http.prepare_content("application/json")
    http.write(require("luci.jsonc").stringify(status))
end

function action_install_deps()
    local http = require "luci.http"
    local sys  = require "luci.sys"

    -- Run install script in background
    sys.call("/usr/share/aria2bot/install-deps.sh > /tmp/aria2bot-install.log 2>&1 &")

    local result = {
        success = true,
        message = "Instalasi dependency dimulai. Cek /tmp/aria2bot-install.log untuk progress."
    }

    http.prepare_content("application/json")
    http.write(require("luci.jsonc").stringify(result))
end
