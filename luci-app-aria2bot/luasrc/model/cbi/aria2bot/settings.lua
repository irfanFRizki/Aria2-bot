-- LuCI CBI Model: Aria2 Bot Settings

local m, s, o

m = Map("aria2bot",
    translate("Aria2 Bot — Settings"),
    translate("Configure your Telegram Bot and Aria2 download settings.")
)

-- ── Section: General ─────────────────────────────────────────────────────

s = m:section(NamedSection, "settings", "aria2bot",
    translate("General Settings"))
s.anonymous = false
s.addremove = false

o = s:option(Flag, "enabled",
    translate("Enable"),
    translate("Enable the Aria2 Telegram Bot service"))
o.rmempty = false
o.default = "0"

-- ── Section: Telegram ─────────────────────────────────────────────────────

s = m:section(NamedSection, "settings", "aria2bot",
    translate("Telegram Bot Configuration"))
s.anonymous = false
s.addremove = false

o = s:option(Value, "bot_token",
    translate("Bot Token"),
    translate("Telegram Bot Token from @BotFather (e.g. 123456789:ABCdef...)"))
o.password   = true
o.rmempty    = false
o.placeholder = "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"

function o.validate(self, value)
    if not value or #value < 20 then
        return nil, translate("Bot token too short. Get it from @BotFather on Telegram.")
    end
    return value
end

o = s:option(Value, "allowed_users",
    translate("Allowed User IDs"),
    translate("Comma-separated Telegram user IDs allowed to use the bot. Leave empty to allow everyone."))
o.placeholder = "123456789,987654321"
o.rmempty     = true

-- ── Section: Aria2 ────────────────────────────────────────────────────────

s = m:section(NamedSection, "settings", "aria2bot",
    translate("Aria2 RPC Settings"))
s.anonymous = false
s.addremove = false

o = s:option(Value, "aria2_rpc_url",
    translate("Aria2 RPC URL"),
    translate("Aria2 JSON-RPC endpoint"))
o.default     = "http://localhost:6800/jsonrpc"
o.placeholder = "http://localhost:6800/jsonrpc"
o.rmempty     = false

o = s:option(Value, "aria2_secret",
    translate("RPC Secret"),
    translate("Aria2 RPC secret token (optional but recommended)"))
o.password    = true
o.placeholder = translate("Leave empty if no secret")
o.rmempty     = true

o = s:option(Value, "download_dir",
    translate("Download Directory"),
    translate("Directory where files will be downloaded"))
o.default     = "/tmp/downloads"
o.placeholder = "/tmp/downloads"
o.rmempty     = false

-- ── Return ────────────────────────────────────────────────────────────────

return m
