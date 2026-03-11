local m, s, o

m = Map("aria2bot", translate("Aria2 Bot - Settings"),
    translate("Konfigurasi Bot Telegram untuk Aria2 Download Manager.<br>" ..
              "<b>Catatan:</b> Setelah menyimpan, restart bot agar konfigurasi berlaku."))

s = m:section(TypedSection, "aria2bot", translate("Konfigurasi Utama"))
s.anonymous = true
s.addremove  = false

-- Enable / disable
o = s:option(Flag, "enabled", translate("Aktifkan Bot"), 
    translate("Centang untuk mengaktifkan bot Telegram saat sistem boot"))
o.rmempty = false

-- Bot Token
o = s:option(Value, "bot_token", translate("Telegram Bot Token"),
    translate("Token dari @BotFather. Contoh: 123456:ABCdef..."))
o.password  = true
o.rmempty   = false
o.placeholder = "Masukkan token bot Telegram Anda"

-- Allowed Users
o = s:option(DynamicList, "allowed_users", translate("User ID yang Diizinkan"),
    translate("Daftar Telegram User ID yang boleh menggunakan bot (opsional, kosongkan = semua user).<br>" ..
              "Dapatkan User ID dengan chat ke @userinfobot di Telegram."))
o.datatype = "string"
o.placeholder = "Contoh: 123456789"

-- Aria2 RPC URL
o = s:option(Value, "aria2_url", translate("Aria2 RPC URL"),
    translate("URL endpoint JSON-RPC Aria2. Default: http://localhost:6800/jsonrpc"))
o.default     = "http://localhost:6800/jsonrpc"
o.rmempty     = false
o.placeholder = "http://localhost:6800/jsonrpc"

-- Aria2 RPC Secret
o = s:option(Value, "aria2_secret", translate("Aria2 RPC Secret Token"),
    translate("Secret token untuk Aria2 RPC (biarkan kosong jika tidak ada)"))
o.password    = true
o.rmempty     = true
o.placeholder = "Kosongkan jika tidak pakai secret"

-- Max Concurrent
o = s:option(ListValue, "max_concurrent", translate("Max Download Bersamaan"),
    translate("Jumlah maksimal download yang berjalan bersamaan"))
o:value("1", "1 download")
o:value("2", "2 download (default)")
o:value("3", "3 download")
o:value("5", "5 download")
o.default = "2"

-- Max Retry
o = s:option(ListValue, "max_retry", translate("Max Retry Attempts"),
    translate("Jumlah percobaan ulang ketika download gagal"))
o:value("0", "Tidak ada retry")
o:value("1", "1x retry")
o:value("3", "3x retry (default)")
o:value("5", "5x retry")
o.default = "3"

return m
