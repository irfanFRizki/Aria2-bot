#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aria2 Telegram Download Bot for OpenWrt
Reads config from /etc/config/aria2bot (UCI format)
"""

import os
import sys
import logging
import subprocess
import asyncio
import json
import urllib.request
import urllib.parse

# ─── Config Reader (UCI) ────────────────────────────────────────────────────

def uci_get(key, default=""):
    try:
        result = subprocess.run(
            ["uci", "get", key],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else default
    except Exception:
        return default

def load_config():
    config = {
        "bot_token":     uci_get("aria2bot.settings.bot_token", ""),
        "aria2_rpc_url": uci_get("aria2bot.settings.aria2_rpc_url", "http://localhost:6800/jsonrpc"),
        "aria2_secret":  uci_get("aria2bot.settings.aria2_secret", ""),
        "download_dir":  uci_get("aria2bot.settings.download_dir", "/tmp/downloads"),
        "allowed_users": uci_get("aria2bot.settings.allowed_users", ""),
        "enabled":       uci_get("aria2bot.settings.enabled", "1"),
    }
    return config

# ─── Aria2 RPC ──────────────────────────────────────────────────────────────

class Aria2RPC:
    def __init__(self, url, secret=""):
        self.url = url
        self.secret = secret
        self._id = 0

    def _call(self, method, params=None):
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": str(self._id),
            "method": method,
            "params": params or []
        }
        if self.secret:
            payload["params"].insert(0, f"token:{self.secret}")

        data = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def add_uri(self, url):
        return self._call("aria2.addUri", [[url]])

    def get_active(self):
        return self._call("aria2.tellActive")

    def get_waiting(self):
        return self._call("aria2.tellWaiting", [0, 100])

    def get_stopped(self):
        return self._call("aria2.tellStopped", [0, 10])

    def get_global_stat(self):
        return self._call("aria2.getGlobalStat")

    def pause(self, gid):
        return self._call("aria2.pause", [gid])

    def remove(self, gid):
        return self._call("aria2.remove", [gid])

    def get_version(self):
        return self._call("aria2.getVersion")

# ─── Telegram Bot ──────────────────────────────────────────────────────────

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api = f"https://api.telegram.org/bot{token}"
        self.offset = 0

    def send_message(self, chat_id, text, parse_mode="HTML"):
        params = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        try:
            data = urllib.parse.urlencode(params).encode("utf-8")
            req = urllib.request.Request(f"{self.api}/sendMessage", data=data)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"send_message error: {e}")
            return None

    def get_updates(self, timeout=30):
        try:
            url = f"{self.api}/getUpdates?offset={self.offset}&timeout={timeout}&allowed_updates=message"
            with urllib.request.urlopen(url, timeout=timeout + 5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("result", [])
        except Exception as e:
            logger.warning(f"get_updates error: {e}")
            return []

# ─── Helper Formatters ─────────────────────────────────────────────────────

def format_size(bytes_val):
    try:
        b = int(bytes_val)
    except Exception:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"

def format_speed(bytes_per_sec):
    return format_size(bytes_per_sec) + "/s"

def format_task(task):
    name = task.get("bittorrent", {}).get("info", {}).get("name", "") or \
           os.path.basename(task.get("files", [{}])[0].get("path", "Unknown"))
    total = int(task.get("totalLength", 0))
    completed = int(task.get("completedLength", 0))
    speed = int(task.get("downloadSpeed", 0))
    pct = (completed / total * 100) if total > 0 else 0
    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
    return (
        f"📁 <b>{name[:40]}</b>\n"
        f"[{bar}] {pct:.1f}%\n"
        f"⬇️ {format_size(completed)} / {format_size(total)}\n"
        f"🚀 {format_speed(speed)}\n"
        f"🆔 GID: <code>{task.get('gid','')}</code>"
    )

# ─── Command Handlers ──────────────────────────────────────────────────────

def handle_start(bot, chat_id):
    msg = (
        "🤖 <b>Aria2 Download Bot</b>\n\n"
        "Perintah yang tersedia:\n"
        "/status — Status download aktif\n"
        "/list — Semua download\n"
        "/add &lt;url&gt; — Tambah download\n"
        "/stop &lt;gid&gt; — Pause download\n"
        "/remove &lt;gid&gt; — Hapus download\n"
        "/stats — Statistik global\n"
        "/version — Versi Aria2\n"
        "/help — Bantuan"
    )
    bot.send_message(chat_id, msg)

def handle_status(bot, chat_id, aria2):
    result = aria2.get_active()
    tasks = result.get("result", [])
    if not tasks:
        bot.send_message(chat_id, "✅ Tidak ada download yang sedang berjalan.")
        return
    msg = f"⬇️ <b>Download Aktif ({len(tasks)})</b>\n\n"
    for t in tasks[:5]:
        msg += format_task(t) + "\n\n"
    bot.send_message(chat_id, msg)

def handle_list(bot, chat_id, aria2):
    active = aria2.get_active().get("result", [])
    waiting = aria2.get_waiting().get("result", [])
    stopped = aria2.get_stopped().get("result", [])

    msg = f"📋 <b>Daftar Download</b>\n\n"
    if active:
        msg += f"🟢 <b>Aktif ({len(active)})</b>\n"
        for t in active[:3]:
            name = os.path.basename(t.get("files", [{}])[0].get("path", "Unknown"))
            msg += f"  • {name[:35]} — {t.get('gid')}\n"
        msg += "\n"
    if waiting:
        msg += f"🟡 <b>Antrian ({len(waiting)})</b>\n"
        for t in waiting[:3]:
            name = os.path.basename(t.get("files", [{}])[0].get("path", "Unknown"))
            msg += f"  • {name[:35]} — {t.get('gid')}\n"
        msg += "\n"
    if stopped:
        msg += f"🔴 <b>Selesai/Stop ({len(stopped)})</b>\n"
        for t in stopped[:3]:
            name = os.path.basename(t.get("files", [{}])[0].get("path", "Unknown"))
            msg += f"  • {name[:35]} — {t.get('gid')}\n"

    if not active and not waiting and not stopped:
        msg += "Tidak ada download."

    bot.send_message(chat_id, msg)

def handle_add(bot, chat_id, aria2, url):
    if not url:
        bot.send_message(chat_id, "⚠️ Gunakan: /add &lt;url&gt;")
        return
    result = aria2.add_uri(url)
    if "result" in result:
        bot.send_message(chat_id, f"✅ Download ditambahkan!\n🆔 GID: <code>{result['result']}</code>")
    else:
        bot.send_message(chat_id, f"❌ Gagal: {result.get('error', {})}")

def handle_stats(bot, chat_id, aria2):
    result = aria2.get_global_stat()
    stat = result.get("result", {})
    msg = (
        f"📊 <b>Statistik Global</b>\n\n"
        f"⬇️ Download Speed: {format_speed(stat.get('downloadSpeed', 0))}\n"
        f"⬆️ Upload Speed:   {format_speed(stat.get('uploadSpeed', 0))}\n"
        f"🟢 Aktif:    {stat.get('numActive', 0)}\n"
        f"🟡 Antrian:  {stat.get('numWaiting', 0)}\n"
        f"🔴 Berhenti: {stat.get('numStopped', 0)}\n"
    )
    bot.send_message(chat_id, msg)

def handle_version(bot, chat_id, aria2):
    result = aria2.get_version()
    ver = result.get("result", {})
    msg = f"ℹ️ Aria2 <b>{ver.get('version', 'Unknown')}</b>"
    bot.send_message(chat_id, msg)

# ─── Main Loop ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("aria2bot")


def main():
    cfg = load_config()

    if not cfg["bot_token"]:
        logger.error("Bot token belum dikonfigurasi! Set di /etc/config/aria2bot")
        sys.exit(1)

    logger.info(f"Aria2 Bot starting... RPC: {cfg['aria2_rpc_url']}")

    bot = TelegramBot(cfg["bot_token"])
    aria2 = Aria2RPC(cfg["aria2_rpc_url"], cfg["aria2_secret"])

    allowed = [u.strip() for u in cfg["allowed_users"].split(",") if u.strip()]

    logger.info("Bot is running. Waiting for messages...")

    while True:
        try:
            updates = bot.get_updates(timeout=30)
            for update in updates:
                bot.offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg:
                    continue

                chat_id = str(msg["chat"]["id"])
                text = msg.get("text", "").strip()
                user_id = str(msg["from"]["id"])

                # Auth check
                if allowed and user_id not in allowed:
                    bot.send_message(chat_id, "⛔ Akses ditolak.")
                    continue

                if not text.startswith("/"):
                    continue

                parts = text.split(maxsplit=1)
                cmd = parts[0].lower().split("@")[0]
                arg = parts[1] if len(parts) > 1 else ""

                logger.info(f"CMD: {cmd} from {user_id}")

                if cmd == "/start" or cmd == "/help":
                    handle_start(bot, chat_id)
                elif cmd == "/status":
                    handle_status(bot, chat_id, aria2)
                elif cmd == "/list":
                    handle_list(bot, chat_id, aria2)
                elif cmd == "/add":
                    handle_add(bot, chat_id, aria2, arg)
                elif cmd == "/stop":
                    r = aria2.pause(arg)
                    bot.send_message(chat_id, f"⏸ Paused: {r.get('result', r.get('error', 'Unknown'))}")
                elif cmd == "/remove":
                    r = aria2.remove(arg)
                    bot.send_message(chat_id, f"🗑 Removed: {r.get('result', r.get('error', 'Unknown'))}")
                elif cmd == "/stats":
                    handle_stats(bot, chat_id, aria2)
                elif cmd == "/version":
                    handle_version(bot, chat_id, aria2)
                else:
                    bot.send_message(chat_id, f"❓ Perintah tidak dikenal: {cmd}")

        except KeyboardInterrupt:
            logger.info("Bot stopped.")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            import time
            time.sleep(5)


if __name__ == "__main__":
    main()
