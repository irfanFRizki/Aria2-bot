-- LuCI CBI Model: Aria2 Bot Settings
-- /usr/lib/lua/luci/model/cbi/aria2bot/settings.lua

local m, s, o

m = Map("aria2bot",
    translate("Aria2 Bot — Settings"),
    translate("Konfigurasi Telegram Bot Token dan Chat ID untuk Aria2 Download Bot.")
)

-- =====================================================
-- Section: Bot Configuration
-- =====================================================
s = m:section(NamedSection, "settings", "aria2bot",
    translate("Konfigurasi Bot Telegram"))
s.anonymous  = false
s.addremove  = false

o = s:option(Value, "bot_token",
    translate("Telegram Bot Token"),
    translate("Token dari @BotFather. Contoh: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"))
o.password    = true
o.rmempty     = false
o.placeholder = "Masukkan Bot Token"

o = s:option(Value, "chat_id",
    translate("Telegram Chat ID"),
    translate("Chat ID Anda. Gunakan @userinfobot atau @getidsbot di Telegram untuk mendapatkan ID."))
o.rmempty     = false
o.placeholder = "Contoh: 123456789 atau -100xxxxxxxxx"

-- =====================================================
-- Section: Aria2 RPC
-- =====================================================
s2 = m:section(NamedSection, "settings", "aria2bot",
    translate("Konfigurasi Aria2 RPC"))
s2.anonymous = false
s2.addremove = false

o = s2:option(Value, "aria2_rpc_url",
    translate("Aria2 RPC URL"))
o.default     = "http://localhost:6800/jsonrpc"
o.placeholder = "http://localhost:6800/jsonrpc"

o = s2:option(Value, "aria2_rpc_secret",
    translate("Aria2 RPC Secret"),
    translate("Kosongkan jika tidak ada secret yang di-set di aria2"))
o.password    = true
o.rmempty     = true
o.placeholder = "(Opsional)"

-- =====================================================
-- Section: Download Options
-- =====================================================
s3 = m:section(NamedSection, "settings", "aria2bot",
    translate("Opsi Download"))
s3.anonymous = false
s3.addremove = false

o = s3:option(Value, "max_concurrent",
    translate("Max Concurrent Downloads"),
    translate("Jumlah maksimum download yang berjalan bersamaan (default: 2)"))
o.default   = "2"
o.datatype  = "uinteger"

o = s3:option(Value, "max_retry",
    translate("Max Retry Attempts"),
    translate("Berapa kali mencoba ulang jika download gagal (default: 3)"))
o.default  = "3"
o.datatype = "uinteger"

-- =====================================================
-- Save hook: restart bot after config change
-- =====================================================
function m.on_commit(self)
    luci.sys.call("/etc/init.d/telegram_bot restart >/dev/null 2>&1 &")
end

return m
