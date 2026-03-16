m = Map("aria2bot", "Aria2 Bot - IRF")
s = m:section(TypedSection, "aria2bot", "Settings")
s.anonymous = true
s:option(Flag, "enabled", "Enable")
s:option(Value, "bot_token", "Bot Token")
s:option(Value, "chat_id", "Chat ID")
return m
