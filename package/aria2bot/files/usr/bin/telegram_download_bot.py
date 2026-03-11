#!/usr/bin/env python3
"""
Bot Telegram untuk download file dengan aria2
Versi Enhanced dengan Queue System, Auto-retry & Auto HDD Detection
Adapted for OpenWrt - reads config from /etc/config/aria2bot (UCI)
"""

import os
import asyncio
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
from collections import deque

# ─── Read config from UCI (OpenWrt) ────────────────────────────────────────

def uci_get(key, default=""):
    try:
        result = subprocess.run(
            ["uci", "get", key],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else default
    except Exception:
        return default

# Konfigurasi dari UCI
TELEGRAM_BOT_TOKEN  = uci_get("aria2bot.settings.bot_token",     "")
ARIA2_RPC_URL       = uci_get("aria2bot.settings.aria2_rpc_url",  "http://localhost:6800/jsonrpc")
ARIA2_RPC_SECRET    = uci_get("aria2bot.settings.aria2_secret",   "")
ALLOWED_USERS_RAW   = uci_get("aria2bot.settings.allowed_users",  "")
DOWNLOAD_DIR_UCI    = uci_get("aria2bot.settings.download_dir",   "")

ALLOWED_USERS = [u.strip() for u in ALLOWED_USERS_RAW.split(",") if u.strip()]

if not TELEGRAM_BOT_TOKEN:
    print("❌ ERROR: bot_token belum dikonfigurasi di /etc/config/aria2bot")
    print("   Jalankan: uci set aria2bot.settings.bot_token='TOKEN_KAMU'")
    print("             uci commit aria2bot")
    import sys; sys.exit(1)

# Queue Configuration
MAX_CONCURRENT_DOWNLOADS = 2
MAX_RETRY_ATTEMPTS = 3

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
        ConversationHandler,
    )
except ImportError:
    print("❌ python-telegram-bot tidak terinstall!")
    print("   Jalankan: pip3 install python-telegram-bot --break-system-packages")
    import sys; sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("❌ aiohttp tidak terinstall!")
    print("   Jalankan: pip3 install aiohttp --break-system-packages")
    import sys; sys.exit(1)

# States untuk conversation
WAITING_FOLDER, WAITING_FILENAME, WAITING_CONFIRMATION = range(3)

# Global variables
BASE_DOWNLOAD_PATH = None
HDD_INFO = {}
user_data = {}
active_downloads = {}
download_queue = deque()
active_download_count = 0
queue_lock = asyncio.Lock()


# ─── HDD Detection ──────────────────────────────────────────────────────────

def detect_hdd_path():
    """
    Auto-detect HDD path berdasarkan mount point yang memiliki data terbanyak
    Mencari di /mnt/sda1, /mnt/sdb1, dst
    Jika download_dir sudah diset di UCI, gunakan itu langsung.
    """
    global BASE_DOWNLOAD_PATH, HDD_INFO

    # Jika sudah diset via UCI, gunakan langsung
    if DOWNLOAD_DIR_UCI:
        BASE_DOWNLOAD_PATH = DOWNLOAD_DIR_UCI
        HDD_INFO = {
            'path': DOWNLOAD_DIR_UCI,
            'device': 'uci_config',
            'total_size': 0,
            'media_size': 0,
            'has_media': False,
            'status': 'uci_config'
        }
        print(f"✅ Download path dari UCI: {BASE_DOWNLOAD_PATH}")
        return BASE_DOWNLOAD_PATH

    detected_hdds = []

    # Scan semua possible mount points
    for device in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
        for partition in range(1, 10):  # Check sda1-sda9, sdb1-sdb9, dst
            mount_path = f"/mnt/{device}{partition}"

            if not os.path.exists(mount_path):
                continue

            # Cek apakah mount point accessible
            if not os.path.ismount(mount_path):
                if not os.path.isdir(mount_path):
                    continue

            try:
                media_path = os.path.join(mount_path, 'media')
                total_size = 0
                media_size = 0

                # Gunakan du command (lebih cepat untuk OpenWrt)
                try:
                    result = subprocess.run(
                        ['du', '-s', mount_path],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        total_size = int(result.stdout.split()[0]) * 1024
                except Exception:
                    for root, dirs, files in os.walk(mount_path):
                        for file in files:
                            try:
                                total_size += os.path.getsize(os.path.join(root, file))
                            except Exception:
                                pass

                if os.path.exists(media_path):
                    try:
                        result = subprocess.run(
                            ['du', '-s', media_path],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            media_size = int(result.stdout.split()[0]) * 1024
                    except Exception:
                        pass

                detected_hdds.append({
                    'path': mount_path,
                    'device': f"{device}{partition}",
                    'total_size': total_size,
                    'media_size': media_size,
                    'has_media': os.path.exists(media_path)
                })

            except Exception as e:
                print(f"Error checking {mount_path}: {e}")
                continue

    if not detected_hdds:
        print("⚠️ No HDD detected, using default /mnt/sda1")
        BASE_DOWNLOAD_PATH = "/mnt/sda1"
        HDD_INFO = {
            'path': BASE_DOWNLOAD_PATH,
            'device': 'sda1',
            'total_size': 0,
            'media_size': 0,
            'has_media': False,
            'status': 'default_fallback'
        }
        return BASE_DOWNLOAD_PATH

    # Prioritas 1: HDD dengan folder media terbesar
    hdds_with_media = [h for h in detected_hdds if h['has_media'] and h['media_size'] > 0]
    if hdds_with_media:
        selected = max(hdds_with_media, key=lambda x: x['media_size'])
        HDD_INFO = {**selected, 'status': 'media_priority'}
    else:
        # Prioritas 2: Total size terbesar
        selected = max(detected_hdds, key=lambda x: x['total_size'])
        HDD_INFO = {**selected, 'status': 'total_size_priority'}

    BASE_DOWNLOAD_PATH = selected['path']

    print(f"✅ HDD Auto-detected: {BASE_DOWNLOAD_PATH}")
    print(f"   Device: {HDD_INFO['device']}")
    print(f"   Total Size: {format_bytes(HDD_INFO['total_size'])}")
    print(f"   Media Size: {format_bytes(HDD_INFO['media_size'])}")
    print(f"   Selection: {HDD_INFO['status']}")

    return BASE_DOWNLOAD_PATH


def get_hdd_info_text():
    """Generate informasi HDD yang sedang digunakan"""
    if not HDD_INFO:
        return "📦 Base Path: `Not detected`"

    status_emoji = {
        'media_priority':      '✅',
        'total_size_priority': '🟡',
        'default_fallback':    '⚠️',
        'uci_config':          '🔧',
    }

    return (
        f"📦 *HDD Information:*\n"
        f"├ Path: `{HDD_INFO['path']}`\n"
        f"├ Device: `{HDD_INFO['device']}`\n"
        f"├ Total: `{format_bytes(HDD_INFO['total_size'])}`\n"
        f"├ Media: `{format_bytes(HDD_INFO['media_size'])}`\n"
        f"└ {status_emoji.get(HDD_INFO['status'], '❓')} Status: {HDD_INFO['status'].replace('_', ' ').title()}"
    )


# ─── Helpers ────────────────────────────────────────────────────────────────

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📊 Status Download"), KeyboardButton("📁 Lihat Folder")],
        [KeyboardButton("📋 Lihat Antrian"),   KeyboardButton("🔄 Refresh Status")],
        [KeyboardButton("💾 Info HDD"),         KeyboardButton("ℹ️ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def categorize_speed(speed_bps: float) -> dict:
    speed_mbps = speed_bps / (1024 * 1024)
    if speed_mbps < 0.5:
        return {'category': 'Sangat Lambat', 'emoji': '🐌', 'color': '🔴', 'comment': 'Koneksi sangat lambat. Cek jaringan Anda.'}
    elif speed_mbps < 2:
        return {'category': 'Lambat',        'emoji': '🚶', 'color': '🟠', 'comment': 'Kecepatan di bawah rata-rata.'}
    elif speed_mbps < 5:
        return {'category': 'Sedang',        'emoji': '🚴', 'color': '🟡', 'comment': 'Kecepatan normal untuk file berukuran sedang.'}
    elif speed_mbps < 10:
        return {'category': 'Cepat',         'emoji': '🚗', 'color': '🟢', 'comment': 'Kecepatan bagus! Download akan cepat selesai.'}
    else:
        return {'category': 'Sangat Cepat',  'emoji': '🚀', 'color': '🔵', 'comment': 'Kecepatan luar biasa! Koneksi premium.'}


def calculate_eta(remaining_bytes: int, speed_bps: float) -> str:
    if speed_bps <= 0:
        return "Menghitung..."
    eta_seconds = remaining_bytes / speed_bps
    if eta_seconds < 60:
        return f"~{int(eta_seconds)} detik"
    elif eta_seconds < 3600:
        return f"~{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
    else:
        return f"~{int(eta_seconds/3600)}h {int((eta_seconds%3600)/60)}m"


def sanitize_filename(filename: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip()
    filename = re.sub(r'\s+', ' ', filename)
    return filename.replace('_ ', ' ').replace(' _', ' ')


def get_filename_from_url(url: str) -> str:
    from urllib.parse import urlparse, unquote
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = os.path.basename(path)
    if not filename or '.' not in filename:
        filename = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return sanitize_filename(filename)


def create_progress_bar(progress: float, length: int = 20) -> str:
    filled = int(length * progress / 100)
    return f"[{'█' * filled}{'░' * (length - filled)}]"


def format_bytes(bytes_size) -> str:
    bytes_size = int(bytes_size) if bytes_size else 0
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m {int(seconds%60)}s"
    else:
        return f"{int(seconds/3600)}h {int((seconds%3600)/60)}m"


def is_valid_url(url: str) -> bool:
    return url.startswith(('http://', 'https://', 'ftp://', 'magnet:'))


def check_allowed(user_id: str) -> bool:
    if not ALLOWED_USERS:
        return True
    return str(user_id) in ALLOWED_USERS


# ─── Aria2 RPC ──────────────────────────────────────────────────────────────

async def aria2_rpc_call(method: str, params: list = None):
    if params is None:
        params = []
    if ARIA2_RPC_SECRET:
        params.insert(0, f"token:{ARIA2_RPC_SECRET}")
    payload = {"jsonrpc": "2.0", "method": method, "id": "telegram_bot", "params": params}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ARIA2_RPC_URL, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('result')
    except Exception as e:
        print(f"Aria2 RPC Error: {e}")
    return None


async def check_aria2_connection():
    return await aria2_rpc_call("aria2.getVersion") is not None


# ─── Bot Handlers ────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    aria2_status = "✅ Connected" if await check_aria2_connection() else "❌ Not Connected"

    await update.message.reply_text(
        "🤖 *Selamat datang di Bot Download Manager!*\n\n"
        "📥 Kirim link untuk download file\n"
        "📊 Gunakan menu di bawah untuk navigasi\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*Fitur Utama:*\n"
        "✅ Download dengan Aria2 engine\n"
        "✅ Queue system (Max 2 concurrent)\n"
        "✅ Auto-retry 3x on error\n"
        "✅ Auto HDD detection\n"
        "✅ Pause/Resume/Stop control\n"
        "✅ Progress tracking real-time\n"
        "✅ Speed monitoring & ETA\n"
        "✅ Notifikasi download selesai\n"
        "✅ Auto-resume pada error\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{get_hdd_info_text()}\n\n"
        f"🔌 Aria2 Status: {aria2_status}\n"
        f"📦 Max Concurrent: {MAX_CONCURRENT_DOWNLOADS}\n"
        f"🔄 Max Retry: {MAX_RETRY_ATTEMPTS}x",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *PANDUAN PENGGUNAAN*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*🎯 Cara Download:*\n\n"
        "1️⃣ Kirim URL file yang ingin didownload\n"
        "2️⃣ Pilih folder dari inline keyboard:\n"
        "   • media/movies\n"
        "   • media/tvshows\n"
        "   • media/drakor\n"
        "3️⃣ Bot akan menampilkan nama file default\n"
        "4️⃣ Pilih: Gunakan nama default atau ubah nama\n"
        "5️⃣ Klik tombol *✅ Iya* untuk konfirmasi\n"
        "6️⃣ Download dimulai otomatis!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*🎛 Control Download:*\n\n"
        "⏸ *Pause* - Jeda download sementara\n"
        "▶️ *Resume* - Lanjutkan download\n"
        "⏹ *Stop* - Hentikan & hapus download\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*📊 Menu Keyboard:*\n\n"
        "• *Status Download* - Cek progress\n"
        "• *Lihat Antrian* - Cek queue\n"
        "• *Lihat Folder* - List folder\n"
        "• *Refresh Status* - Update progress\n"
        "• *Info HDD* - Detail HDD yang digunakan\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Max concurrent: {MAX_CONCURRENT_DOWNLOADS} download\n"
        f"🔄 Auto-retry: {MAX_RETRY_ATTEMPTS}x on error\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


async def show_hdd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    detect_hdd_path()

    all_hdds = []
    for device in ['sda', 'sdb', 'sdc', 'sdd']:
        for partition in range(1, 5):
            mount_path = f"/mnt/{device}{partition}"
            if os.path.exists(mount_path):
                try:
                    result = subprocess.run(['du', '-s', mount_path], capture_output=True, text=True, timeout=3)
                    if result.returncode == 0:
                        size = int(result.stdout.split()[0]) * 1024
                        all_hdds.append({
                            'device': f"{device}{partition}",
                            'path': mount_path,
                            'size': size,
                            'active': mount_path == BASE_DOWNLOAD_PATH
                        })
                except Exception:
                    pass

    info_text = "💾 *INFORMASI HDD SYSTEM*\n\n━━━━━━━━━━━━━━━━━━━━━\n"
    info_text += "*HDD Yang Sedang Digunakan:*\n\n"
    info_text += f"{get_hdd_info_text()}\n\n"
    info_text += "━━━━━━━━━━━━━━━━━━━━━\n"

    if all_hdds:
        info_text += "*Semua HDD Terdeteksi:*\n\n"
        for hdd in sorted(all_hdds, key=lambda x: x['size'], reverse=True):
            status = "✅ ACTIVE" if hdd['active'] else "⚪ Available"
            info_text += f"{status}\n"
            info_text += f"├ Device: `{hdd['device']}`\n"
            info_text += f"├ Path: `{hdd['path']}`\n"
            info_text += f"└ Size: `{format_bytes(hdd['size'])}`\n\n"
    else:
        info_text += "⚠️ Tidak ada HDD tambahan terdeteksi\n"

    info_text += (
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "*📌 Info:*\n"
        "Bot otomatis memilih HDD dengan\n"
        "folder 'media' yang memiliki data terbanyak.\n"
        "Restart bot untuk re-scan HDD."
    )

    await update.message.reply_text(info_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    text = update.message.text
    if text in ("📊 Status Download", "🔄 Refresh Status"):
        await download_status(update, context)
    elif text == "📁 Lihat Folder":
        await show_folders(update, context)
    elif text == "📋 Lihat Antrian":
        await show_queue(update, context)
    elif text == "💾 Info HDD":
        await show_hdd_info(update, context)
    elif text == "ℹ️ Help":
        await help_command(update, context)


async def show_folders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        base_path = Path(BASE_DOWNLOAD_PATH)
        if not base_path.exists():
            await update.message.reply_text(
                f"⚠️ Base path belum ada: `{BASE_DOWNLOAD_PATH}`\n\n"
                "Folder akan dibuat otomatis saat download pertama.",
                parse_mode="Markdown", reply_markup=get_main_keyboard()
            )
            return

        folders = [f for f in base_path.iterdir() if f.is_dir()]
        if not folders:
            await update.message.reply_text(
                f"📂 *Folder tersedia:*\n\nBelum ada folder.\n\n{get_hdd_info_text()}",
                parse_mode="Markdown", reply_markup=get_main_keyboard()
            )
            return

        folder_list = "📂 *DAFTAR FOLDER*\n\n━━━━━━━━━━━━━━━━━━━━━\n"
        for folder in sorted(folders):
            file_count = len([f for f in folder.iterdir() if f.is_file()])
            total_size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
            folder_list += f"\n📁 *{folder.name}*\n"
            folder_list += f"├ Path: `{folder}`\n"
            folder_list += f"├ Files: `{file_count}` file(s)\n"
            folder_list += f"└ Size: `{format_bytes(total_size)}`\n"

        folder_list += f"\n━━━━━━━━━━━━━━━━━━━━━\n{get_hdd_info_text()}"
        await update.message.reply_text(folder_list, parse_mode="Markdown", reply_markup=get_main_keyboard())

    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown", reply_markup=get_main_keyboard())


async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_active = sum(1 for d in active_downloads.values() if d['user_id'] == user_id and d['status'] == 'downloading')
    user_queued = sum(1 for q in download_queue if q['user_id'] == user_id)

    queue_text = (
        f"📋 *STATUS ANTRIAN DOWNLOAD*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Active: {active_download_count}/{MAX_CONCURRENT_DOWNLOADS}\n"
        f"📦 Queue: {len(download_queue)} waiting\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Your Downloads:*\n"
        f"▶️ Active: {user_active}\n"
        f"⏳ Queued: {user_queued}\n\n"
    )

    if download_queue:
        queue_text += "━━━━━━━━━━━━━━━━━━━━━\n*Dalam Antrian:*\n\n"
        for idx, item in enumerate(list(download_queue)[:5], 1):
            queue_text += f"{idx}. `{item['filename'][:30]}...`\n"
            queue_text += f"   📁 {item['folder_name']}\n\n"
        if len(download_queue) > 5:
            queue_text += f"... dan {len(download_queue) - 5} lainnya\n"
    else:
        queue_text += "✅ Tidak ada antrian"

    await update.message.reply_text(queue_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


# ─── Conversation: URL → Folder → Filename → Confirm ────────────────────────

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return ConversationHandler.END

    url = update.message.text.strip()
    user_id = update.effective_user.id

    if not is_valid_url(url):
        await update.message.reply_text(
            "❌ URL tidak valid! Pastikan dimulai dengan http://, https://, ftp://, atau magnet:",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    if not await check_aria2_connection():
        await update.message.reply_text(
            "❌ *Aria2 tidak terhubung!*\n\n"
            "Pastikan Aria2 RPC sedang berjalan:\n"
            "`/etc/init.d/aria2rpc start`",
            parse_mode="Markdown", reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    user_data[user_id] = {'url': url}

    keyboard = [
        [InlineKeyboardButton("🎬 media/movies",  callback_data="folder_media/movies")],
        [InlineKeyboardButton("📺 media/tvshows", callback_data="folder_media/tvshows")],
        [InlineKeyboardButton("🎭 media/drakor",  callback_data="folder_media/drakor")],
        [InlineKeyboardButton("❌ Batal",          callback_data="folder_cancel")]
    ]

    await update.message.reply_text(
        f"🔗 *Link Diterima!*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"`{url[:100]}{'...' if len(url) > 100 else ''}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📂 *Pilih folder untuk menyimpan file:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_FOLDER


async def handle_folder_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if user_id not in user_data:
        await query.edit_message_text("❌ Sesi expired! Silakan kirim URL lagi.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Gunakan menu:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if query.data == "folder_cancel":
        await query.edit_message_text("❌ *Download dibatalkan!*", parse_mode="Markdown")
        del user_data[user_id]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Gunakan menu:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    folder_name = query.data.replace("folder_", "")
    folder_path = os.path.join(BASE_DOWNLOAD_PATH, folder_name)
    user_data[user_id]['folder_name'] = folder_name
    user_data[user_id]['folder_path'] = folder_path

    folder_exists = os.path.exists(folder_path)
    suggested_filename = get_filename_from_url(user_data[user_id]['url'])
    user_data[user_id]['suggested_filename'] = suggested_filename

    keyboard = [
        [InlineKeyboardButton("✅ Gunakan Nama Ini", callback_data="filename_default")],
        [InlineKeyboardButton("✏️ Ubah Nama File",  callback_data="filename_custom")],
        [InlineKeyboardButton("❌ Batal",             callback_data="filename_cancel")]
    ]

    await query.edit_message_text(
        f"📋 *KONFIRMASI FOLDER & NAMA FILE*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 Folder: `{folder_name}`\n"
        f"📂 Full: `{folder_path}`\n"
        f"{'✅' if folder_exists else '🆕'} Status: {'Folder sudah ada' if folder_exists else 'Folder akan dibuat'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📄 *Nama File (terdeteksi):*\n"
        f"`{suggested_filename}`\n\n"
        f"❓ *Gunakan nama file ini?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAITING_FILENAME


async def handle_filename_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if user_id not in user_data:
        await query.edit_message_text("❌ Sesi expired!")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Gunakan menu:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if query.data == "filename_cancel":
        await query.edit_message_text("❌ *Download dibatalkan!*", parse_mode="Markdown")
        del user_data[user_id]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Gunakan menu:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if query.data == "filename_default":
        user_data[user_id]['filename'] = user_data[user_id]['suggested_filename']
        return await show_final_confirmation(query, context, user_id)

    elif query.data == "filename_custom":
        await query.edit_message_text(
            f"✏️ *UBAH NAMA FILE*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 Nama saat ini: `{user_data[user_id]['suggested_filename']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 Ketik nama file baru (sertakan ekstensi):\n"
            "Contoh: `My-Video.mp4`\n\n"
            "❌ Ketik /cancel untuk membatalkan",
            parse_mode="Markdown"
        )
        return WAITING_FILENAME


async def handle_custom_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    custom_filename = sanitize_filename(update.message.text.strip())

    if not custom_filename:
        await update.message.reply_text("❌ *Nama file tidak valid!*\n\nSilakan ketik ulang:", parse_mode="Markdown")
        return WAITING_FILENAME

    user_data[user_id]['filename'] = custom_filename
    return await show_final_confirmation_message(update, context, user_id)


async def show_final_confirmation(query, context, user_id):
    d = user_data[user_id]
    keyboard = [[
        InlineKeyboardButton("✅ Iya, Download!", callback_data="final_yes"),
        InlineKeyboardButton("❌ Batal",          callback_data="final_no")
    ]]
    await query.edit_message_text(
        f"🎯 *KONFIRMASI AKHIR*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 Folder: `{d['folder_name']}`\n"
        f"📄 Nama File: `{d['filename']}`\n"
        f"📂 Path:\n`{os.path.join(d['folder_path'], d['filename'])}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ *Lanjutkan download?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAITING_CONFIRMATION


async def show_final_confirmation_message(update, context, user_id):
    d = user_data[user_id]
    keyboard = [[
        InlineKeyboardButton("✅ Iya, Download!", callback_data="final_yes"),
        InlineKeyboardButton("❌ Batal",          callback_data="final_no")
    ]]
    await update.message.reply_text(
        f"🎯 *KONFIRMASI AKHIR*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 Folder: `{d['folder_name']}`\n"
        f"📄 Nama File: `{d['filename']}`\n"
        f"📂 Path:\n`{os.path.join(d['folder_path'], d['filename'])}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ *Lanjutkan download?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAITING_CONFIRMATION


async def handle_final_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if user_id not in user_data:
        await query.edit_message_text("❌ Sesi expired!")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Gunakan menu:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if query.data == "final_no":
        await query.edit_message_text("❌ *Download dibatalkan!*", parse_mode="Markdown")
        del user_data[user_id]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Gunakan menu:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    d = user_data.pop(user_id)
    await query.edit_message_text(
        f"✅ *Konfirmasi Diterima!*\n\n"
        f"📦 Menambahkan ke queue...\n"
        f"📁 Folder: `{d['folder_name']}`\n"
        f"📄 File: `{d['filename']}`",
        parse_mode="Markdown"
    )

    await add_to_queue(context.bot, update.effective_chat.id,
                       d['url'], d['folder_path'], d['folder_name'], d['filename'], user_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🎛 Gunakan menu:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


# ─── Queue & Download ─────────────────────────────────────────────────────────

async def add_to_queue(bot, chat_id, url, folder_path, folder_name, filename, user_id):
    global active_download_count
    info = dict(bot=bot, chat_id=chat_id, url=url, folder_path=folder_path,
                folder_name=folder_name, filename=filename, user_id=user_id)
    async with queue_lock:
        if active_download_count < MAX_CONCURRENT_DOWNLOADS:
            active_download_count += 1
            await bot.send_message(
                chat_id=chat_id,
                text=f"▶️ *Download dimulai!*\n\n📄 {filename}\n📊 Slot: {active_download_count}/{MAX_CONCURRENT_DOWNLOADS}",
                parse_mode="Markdown"
            )
            asyncio.create_task(download_with_aria2(**info))
        else:
            download_queue.append(info)
            position = len(download_queue)
            await bot.send_message(
                chat_id=chat_id,
                text=f"⏳ *Masuk antrian*\n\n📄 {filename}\n📋 Posisi: #{position}",
                parse_mode="Markdown", reply_markup=get_main_keyboard()
            )


async def process_queue():
    global active_download_count
    async with queue_lock:
        if download_queue and active_download_count < MAX_CONCURRENT_DOWNLOADS:
            info = download_queue.popleft()
            active_download_count += 1
            await info['bot'].send_message(
                chat_id=info['chat_id'],
                text=f"▶️ *Download dimulai dari antrian!*\n\n📄 {info['filename']}\n📊 Slot: {active_download_count}/{MAX_CONCURRENT_DOWNLOADS}",
                parse_mode="Markdown"
            )
            asyncio.create_task(download_with_aria2(**info))


def get_download_control_keyboard(download_id, status):
    if status == 'downloading':
        keyboard = [[
            InlineKeyboardButton("⏸ Pause", callback_data=f"ctrl_pause_{download_id}"),
            InlineKeyboardButton("⏹ Stop",  callback_data=f"ctrl_stop_{download_id}")
        ]]
    elif status == 'paused':
        keyboard = [[
            InlineKeyboardButton("▶️ Resume", callback_data=f"ctrl_resume_{download_id}"),
            InlineKeyboardButton("⏹ Stop",   callback_data=f"ctrl_stop_{download_id}")
        ]]
    else:
        return None
    return InlineKeyboardMarkup(keyboard)


async def handle_download_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    action = parts[1]
    download_id = '_'.join(parts[2:])

    if download_id not in active_downloads:
        await query.edit_message_text("❌ Download tidak ditemukan atau sudah selesai.")
        return

    download = active_downloads[download_id]
    gid = download.get('gid')

    if action == 'pause':
        result = await aria2_rpc_call("aria2.pause", [gid])
        if result:
            download['status'] = 'paused'
            await query.edit_message_text(
                f"⏸ *Download dijeda*\n\n📄 {download['filename']}\n📊 Progress: {download['progress']:.1f}%",
                parse_mode="Markdown",
                reply_markup=get_download_control_keyboard(download_id, 'paused')
            )
        else:
            await query.answer("❌ Gagal menjeda download", show_alert=True)

    elif action == 'resume':
        result = await aria2_rpc_call("aria2.unpause", [gid])
        if result:
            download['status'] = 'downloading'
            await query.edit_message_text(
                f"▶️ *Download dilanjutkan*\n\n📄 {download['filename']}\n📊 Progress: {download['progress']:.1f}%",
                parse_mode="Markdown",
                reply_markup=get_download_control_keyboard(download_id, 'downloading')
            )
        else:
            await query.answer("❌ Gagal melanjutkan download", show_alert=True)

    elif action == 'stop':
        result = await aria2_rpc_call("aria2.remove", [gid])
        if result:
            download['status'] = 'stopped'
            await query.edit_message_text(
                f"⏹ *Download dihentikan*\n\n📄 {download['filename']}\n📊 {download['progress']:.1f}%",
                parse_mode="Markdown"
            )
            global active_download_count
            active_download_count -= 1
            del active_downloads[download_id]
            await process_queue()
        else:
            await query.answer("❌ Gagal menghentikan download", show_alert=True)


async def download_with_aria2(bot, chat_id, url, folder_path, folder_name, filename, user_id):
    global active_download_count
    download_id = f"{user_id}_{int(datetime.now().timestamp() * 1000)}"
    retry_count = 0
    gid = None

    try:
        Path(folder_path).mkdir(parents=True, exist_ok=True)

        while retry_count <= MAX_RETRY_ATTEMPTS:
            try:
                options = {
                    "dir": folder_path,
                    "out": filename,
                    "max-connection-per-server": "16",
                    "split": "16",
                    "min-split-size": "1M",
                    "continue": "true",
                    "always-resume": "true",
                    "auto-file-renaming": "false",
                    "allow-overwrite": "false"
                }
                gid = await aria2_rpc_call("aria2.addUri", [[url], options])
                if not gid:
                    raise Exception("Gagal menambahkan download ke Aria2")

                active_downloads[download_id] = {
                    'gid': gid, 'filename': filename, 'folder': folder_name,
                    'size': 0, 'downloaded': 0, 'progress': 0,
                    'status': 'downloading', 'start_time': datetime.now(),
                    'user_id': user_id, 'speed': 0, 'eta': 'Menghitung...',
                    'retry_count': retry_count, 'url': url, 'folder_path': folder_path
                }

                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🚀 *Download dimulai!*\n\n"
                         f"━━━━━━━━━━━━━━━━━━━━━\n"
                         f"📄 File: `{filename}`\n"
                         f"📁 Folder: `{folder_name}`\n"
                         f"🔗 URL: `{url[:50]}...`\n"
                         f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                         f"⏳ Menginisialisasi download...",
                    parse_mode="Markdown"
                )

                last_update = 0
                stalled_count = 0
                last_completed = 0
                no_status_count = 0

                while True:
                    await asyncio.sleep(3)
                    status = await aria2_rpc_call("aria2.tellStatus", [gid])

                    if not status:
                        no_status_count += 1
                        if no_status_count > 5:
                            raise Exception("Gagal mendapatkan status dari Aria2")
                        continue

                    no_status_count = 0
                    aria_status    = status.get('status')
                    total_length   = int(status.get('totalLength', 0))
                    completed_length = int(status.get('completedLength', 0))
                    download_speed = int(status.get('downloadSpeed', 0))

                    if completed_length == last_completed and download_speed == 0 and aria_status == 'active':
                        stalled_count += 1
                        if stalled_count > 20:
                            raise Exception("Download timeout (tidak ada progress)")
                    else:
                        stalled_count = 0
                    last_completed = completed_length

                    if total_length > 0:
                        progress = (completed_length / total_length) * 100
                        remaining = total_length - completed_length
                        eta = calculate_eta(remaining, download_speed)
                        active_downloads[download_id].update({
                            'size': total_length, 'downloaded': completed_length,
                            'progress': progress, 'speed': download_speed, 'eta': eta
                        })

                        if progress - last_update >= 15 or (last_update == 0 and progress > 0):
                            last_update = progress
                            speed_info = categorize_speed(download_speed)
                            try:
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=f"⬇ *DOWNLOADING*\n\n"
                                         f"━━━━━━━━━━━━━━━━━━━━━\n"
                                         f"📄 `{filename[:40]}{'...' if len(filename)>40 else ''}`\n"
                                         f"📁 `{folder_name}`\n"
                                         f"📊 Total: `{format_bytes(total_length)}`\n"
                                         f"🔄 Retry: {retry_count}/{MAX_RETRY_ATTEMPTS}\n"
                                         f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                                         f"{create_progress_bar(progress)}\n"
                                         f"📈 Progress: `{progress:.1f}%`\n"
                                         f"💾 Downloaded: `{format_bytes(completed_length)}`\n\n"
                                         f"⚡ Speed: `{format_bytes(download_speed)}/s`\n"
                                         f"{speed_info['color']} {speed_info['emoji']} *{speed_info['category']}*\n"
                                         f"💬 {speed_info['comment']}\n\n"
                                         f"⏱ ETA: *{eta}*",
                                    parse_mode="Markdown",
                                    reply_markup=get_download_control_keyboard(download_id, 'downloading')
                                )
                            except Exception as e:
                                print(f"Error sending progress: {e}")

                    if aria_status == 'complete':
                        active_downloads[download_id]['status'] = 'completed'
                        elapsed = (datetime.now() - active_downloads[download_id]['start_time']).total_seconds()
                        avg_speed = total_length / elapsed if elapsed > 0 else 0
                        speed_info = categorize_speed(avg_speed)

                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"🎉 *DOWNLOAD SELESAI!*\n\n"
                                 f"━━━━━━━━━━━━━━━━━━━━━\n"
                                 f"✅ Status: *Berhasil*\n"
                                 f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                                 f"📄 *File Info:*\n"
                                 f"├ Name: `{filename}`\n"
                                 f"├ Size: `{format_bytes(total_length)}`\n"
                                 f"├ Folder: `{folder_name}`\n"
                                 f"└ Path: `{os.path.join(folder_path, filename)}`\n\n"
                                 f"📊 *Download Stats:*\n"
                                 f"├ Avg Speed: `{format_bytes(avg_speed)}/s`\n"
                                 f"├ {speed_info['color']} {speed_info['emoji']} *{speed_info['category']}*\n"
                                 f"├ Duration: `{format_time(elapsed)}`\n"
                                 f"├ Retries: {retry_count}/{MAX_RETRY_ATTEMPTS}\n"
                                 f"└ {speed_info['comment']}\n\n"
                                 f"━━━━━━━━━━━━━━━━━━━━━\n"
                                 f"💡 File tersimpan dan siap digunakan!\n"
                                 f"🚀 Powered by Aria2",
                            parse_mode="Markdown", reply_markup=get_main_keyboard()
                        )

                        active_download_count -= 1
                        try:
                            await aria2_rpc_call("aria2.removeDownloadResult", [gid])
                        except Exception:
                            pass
                        await asyncio.sleep(300)
                        if download_id in active_downloads:
                            del active_downloads[download_id]
                        await process_queue()
                        return

                    elif aria_status == 'error':
                        error_message = status.get('errorMessage', 'Unknown error')
                        completed = int(status.get('completedLength', 0))
                        if completed > 0 and retry_count < MAX_RETRY_ATTEMPTS:
                            try:
                                await bot.send_message(chat_id=chat_id,
                                    text="⚠️ *Download Error!*\n🔄 Mencoba auto-resume...", parse_mode="Markdown")
                                await aria2_rpc_call("aria2.forceResume", [gid])
                                await asyncio.sleep(3)
                                new_status = await aria2_rpc_call("aria2.tellStatus", [gid])
                                if new_status and new_status.get("status") == "active":
                                    await bot.send_message(chat_id=chat_id,
                                        text=f"🟢 *Auto-resume berhasil!*\nMelanjutkan dari `{format_bytes(completed)}`",
                                        parse_mode="Markdown")
                                    continue
                            except Exception as e:
                                print(f"ForceResume failed: {e}")
                        raise Exception(f"Download error: {error_message}")

                    elif aria_status == 'paused':
                        active_downloads[download_id]['status'] = 'paused'
                        await asyncio.sleep(3)
                        continue

                    elif aria_status == 'removed':
                        raise Exception("Download dihentikan oleh user")

            except Exception as e:
                retry_count += 1
                try:
                    if gid:
                        await aria2_rpc_call("aria2.forceRemove", [gid])
                        await aria2_rpc_call("aria2.removeDownloadResult", [gid])
                except Exception:
                    pass

                if retry_count <= MAX_RETRY_ATTEMPTS:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ *Download Error!*\n\n❌ Error: `{str(e)[:100]}`\n"
                             f"🔄 Retry {retry_count}/{MAX_RETRY_ATTEMPTS}\n\n⏳ Mencoba lagi dalam 5 detik...",
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(5)
                    continue
                else:
                    raise e

    except Exception as e:
        if download_id in active_downloads:
            active_downloads[download_id]['status'] = 'failed'

        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ *DOWNLOAD GAGAL!*\n\n"
                 f"━━━━━━━━━━━━━━━━━━━━━\n"
                 f"📄 `{filename[:40]}...`\n"
                 f"🔄 Retry: {retry_count}/{MAX_RETRY_ATTEMPTS}\n"
                 f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                 f"❌ Error: `{str(e)[:150]}`\n\n"
                 f"💡 Semua retry telah habis. Coba download ulang.",
            parse_mode="Markdown", reply_markup=get_main_keyboard()
        )
        active_download_count -= 1
        try:
            if gid:
                await aria2_rpc_call("aria2.forceRemove", [gid])
                await aria2_rpc_call("aria2.removeDownloadResult", [gid])
        except Exception:
            pass
        if download_id in active_downloads:
            del active_downloads[download_id]
        await process_queue()


async def download_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_downloads = {k: v for k, v in active_downloads.items() if v['user_id'] == user_id}

    if not user_downloads:
        await update.message.reply_text(
            "🔭 *TIDAK ADA DOWNLOAD AKTIF*\n\n"
            "Belum ada download yang sedang berjalan.\n\n"
            "💡 Kirim URL untuk memulai download baru!",
            parse_mode="Markdown", reply_markup=get_main_keyboard()
        )
        return

    status_text = "📊 *STATUS DOWNLOAD AKTIF*\n\n━━━━━━━━━━━━━━━━━━━━━\n"
    status_icons = {'downloading': '⬇', 'completed': '✅', 'failed': '❌', 'paused': '⏸', 'stopped': '⏹'}

    for download_id, info in user_downloads.items():
        elapsed = (datetime.now() - info['start_time']).total_seconds()
        status_text += f"\n{status_icons.get(info['status'], '❓')} *{info['filename'][:30]}...*\n"
        status_text += f"📁 Folder: `{info['folder']}`\n"
        if info['size'] > 0:
            status_text += f"📊 Size: `{format_bytes(info['size'])}`\n"
            status_text += f"{create_progress_bar(info['progress'])}\n"
            status_text += f"📈 Progress: `{info['progress']:.1f}%`\n"
            status_text += f"💾 Downloaded: `{format_bytes(info['downloaded'])}`\n"
            if info['status'] == 'downloading':
                speed_info = categorize_speed(info.get('speed', 0))
                status_text += f"⚡ Speed: `{format_bytes(info.get('speed', 0))}/s`\n"
                status_text += f"{speed_info['color']} {speed_info['emoji']} {speed_info['category']}\n"
                status_text += f"⏱ ETA: {info.get('eta', 'Menghitung...')}\n"
            status_text += f"🔄 Retry: {info.get('retry_count', 0)}/{MAX_RETRY_ATTEMPTS}\n"
        status_text += f"⏲ Elapsed: `{format_time(elapsed)}`\n"
        status_text += f"Status: `{info['status']}`\n"
        status_text += "━━━━━━━━━━━━━━━━━━━━━\n"

    await update.message.reply_text(status_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text(
        "❌ *Proses dibatalkan!*\n\nKirim URL lagi jika ingin memulai download baru.",
        parse_mode="Markdown", reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("🔍 Detecting HDD path...")
    detect_hdd_path()
    Path(BASE_DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(r'^(https?://|ftp://|magnet:)'),
                handle_url
            )
        ],
        states={
            WAITING_FOLDER: [
                CallbackQueryHandler(handle_folder_choice, pattern="^folder_")
            ],
            WAITING_FILENAME: [
                CallbackQueryHandler(handle_filename_choice, pattern="^filename_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_filename)
            ],
            WAITING_CONFIRMATION: [
                CallbackQueryHandler(handle_final_confirmation, pattern="^final_")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help",  help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_download_control, pattern="^ctrl_"))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^(https?://|ftp://|magnet:)'),
        handle_keyboard_buttons
    ))

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🤖 Bot started with Auto HDD Detection!")
    print(f"📦 HDD Path:    {BASE_DOWNLOAD_PATH}")
    print(f"💾 Device:      {HDD_INFO.get('device', 'N/A')}")
    print(f"📊 Total Size:  {format_bytes(HDD_INFO.get('total_size', 0))}")
    print(f"📁 Media Size:  {format_bytes(HDD_INFO.get('media_size', 0))}")
    print(f"✅ Selection:   {HDD_INFO.get('status', 'N/A')}")
    print(f"🔌 Aria2 RPC:   {ARIA2_RPC_URL}")
    print(f"📦 Max Concurrent: {MAX_CONCURRENT_DOWNLOADS}")
    print(f"🔄 Max Retry:   {MAX_RETRY_ATTEMPTS}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
