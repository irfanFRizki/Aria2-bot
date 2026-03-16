m = Map("aria2bot", translate("Aria2 Bot - IRF"), translate("Pengaturan Telegram Bot"))

s = m:section(TypedSection, "aria2bot", translate("Settings"))
s.anonymous = true

s:option(Flag, "enabled", translate("Enable"))
s:option(Value, "bot_token", translate("Bot Token"))
s:option(Value, "chat_id", translate("Chat ID"))

return m
