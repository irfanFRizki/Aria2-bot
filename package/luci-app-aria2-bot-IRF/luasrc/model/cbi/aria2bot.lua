local m, s, o

m = Map("aria2bot", translate("Aria2 Bot Settings"),
  translate("Konfigurasi Telegram Bot untuk Aria2 Download Manager"))

s = m:section(NamedSection, "main", "aria2bot", translate("Konfigurasi Bot"))
s.anonymous = true
s.addremove = false

-- Bot Token
o = s:option(Value, "bot_token", translate("Telegram Bot Token"),
  translate("Dapatkan dari @BotFather di Telegram. Contoh: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"))
o.placeholder = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
o.rmempty = false
o.password = true

-- Allowed Users
o = s:option(Value, "allowed_users", translate("Allowed User IDs"),
  translate("User ID Telegram yang diizinkan (pisahkan dengan koma). Dapatkan ID kamu dari @userinfobot. Kosongkan = semua user boleh."))
o.placeholder = "123456789, 987654321"
o.rmempty = true

-- Aria2 RPC URL
o = s:option(Value, "aria2_rpc_url", translate("Aria2 RPC URL"),
  translate("URL untuk koneksi ke Aria2 RPC. Default: http://localhost:6800/jsonrpc"))
o.placeholder = "http://localhost:6800/jsonrpc"
o.default = "http://localhost:6800/jsonrpc"
o.rmempty = false

-- Aria2 RPC Secret
o = s:option(Value, "aria2_rpc_secret", translate("Aria2 RPC Secret"),
  translate("Token rahasia Aria2 RPC (jika diset). Kosongkan jika tidak ada."))
o.placeholder = "(kosong jika tidak pakai secret)"
o.rmempty = true
o.password = true

-- Max Concurrent Downloads
o = s:option(ListValue, "max_concurrent_downloads", translate("Max Download Bersamaan"),
  translate("Maksimum jumlah download yang berjalan bersamaan"))
o:value("1", "1 download")
o:value("2", "2 download")
o:value("3", "3 download")
o:value("5", "5 download")
o.default = "2"

-- Download Directory
o = s:option(Value, "download_dir", translate("Direktori Download"),
  translate("Path folder untuk menyimpan file download. Contoh: /mnt/sda1/downloads"))
o.placeholder = "/mnt/sda1/downloads"
o.default = "/mnt/sda1/downloads"
o.rmempty = false

-- Auto Start
o = s:option(Flag, "enabled", translate("Auto Start saat Boot"),
  translate("Aktifkan agar Bot otomatis berjalan saat router nyala"))
o.rmempty = false
o.default = "0"

-- Save button callback: enable/disable service
function m.on_after_commit(self)
  local enabled = m.uci:get("aria2bot", "main", "enabled")
  if enabled == "1" then
    os.execute("/etc/init.d/telegram_bot enable 2>/dev/null")
    os.execute("/etc/init.d/telegram_bot restart 2>/dev/null")
  else
    os.execute("/etc/init.d/telegram_bot disable 2>/dev/null")
    os.execute("/etc/init.d/telegram_bot stop 2>/dev/null")
  end
end

return m
