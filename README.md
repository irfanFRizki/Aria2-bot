# 🤖 luci-app-aria2-bot-IRF

**Aria2 Download Bot** — Telegram bot untuk download file via Aria2, lengkap dengan antarmuka LuCI di OpenWrt.

[![Build IPK](https://github.com/irfanFRizki/Aria2-bot/actions/workflows/build-ipk.yml/badge.svg)](https://github.com/irfanFRizki/Aria2-bot/actions/workflows/build-ipk.yml)

---

## ✨ Fitur

- 📲 Kontrol download via Telegram (HTTP/FTP/Magnet link)
- 🎛 Antarmuka LuCI di **Services → Aria2 Bot**
- ⚙️ Input Token & Chat ID langsung dari browser (tidak perlu SSH)
- 📊 Dashboard: status service, kontrol start/stop/restart, live log
- 🔄 Auto-install Python dependency (`python-telegram-bot`, `aiohttp`)
- 📦 Queue system: max 2 concurrent download
- 🔁 Auto-retry 3x jika download gagal
- 💾 Auto-deteksi HDD (`/mnt/sda1`, dll)
- 🚀 Auto-start saat router boot (via procd)

---

## 📦 Download IPK

Download file `.ipk` terbaru dari halaman **[Releases](https://github.com/irfanFRizki/Aria2-bot/releases)**.

---

## 🛠 Cara Install di OpenWrt

### Via SCP (dari PC/laptop)
```bash
# Upload
scp luci-app-aria2-bot-IRF_*.ipk root@192.168.1.1:/tmp/

# Install
ssh root@192.168.1.1 "opkg install /tmp/luci-app-aria2-bot-IRF_*.ipk"
```

### Via Termux (dari HP Android)
```bash
# Install SSH client di Termux
pkg install openssh

# Upload file ke router
scp /sdcard/Download/luci-app-aria2-bot-IRF_*.ipk root@192.168.1.1:/tmp/

# Install
ssh root@192.168.1.1 "opkg install /tmp/luci-app-aria2-bot-IRF_*.ipk"
```

---

## ⚙️ Konfigurasi

1. Buka browser → `http://192.168.1.1`
2. Login ke LuCI
3. Pergi ke **Services → Aria2 Bot → Settings**
4. Masukkan:
   - **Telegram Bot Token** — dari [@BotFather](https://t.me/BotFather)
   - **Chat ID** — dari [@userinfobot](https://t.me/userinfobot)
5. Klik **Save & Apply**
6. Bot akan restart otomatis

### Atau via SSH:
```bash
uci set aria2bot.settings.bot_token='YOUR_TOKEN_HERE'
uci set aria2bot.settings.chat_id='YOUR_CHAT_ID'
uci commit aria2bot
/etc/init.d/telegram_bot restart
```

---

## 🚀 Upload ke GitHub via Termux

### Setup pertama kali
```bash
# Di Termux
pkg update && pkg install git openssh

# Konfigurasi git
git config --global user.name "irfanFRizki"
git config --global user.email "email@kamu.com"

# Generate SSH key (untuk GitHub)
ssh-keygen -t ed25519 -C "email@kamu.com"
cat ~/.ssh/id_ed25519.pub
# Salin output di atas → tambahkan ke GitHub Settings > SSH Keys
```

### Upload project
```bash
# Clone repo (pertama kali)
git clone git@github.com:irfanFRizki/Aria2-bot.git
cd Aria2-bot

# Salin file proyek ke sini
cp -r /sdcard/Download/luci-app-aria2-bot-IRF/* .

# Commit & push
git add .
git commit -m "feat: initial release"
git push origin main
```

### Buat release baru (trigger GitHub Actions build)
```bash
# Buat tag versi → GitHub Actions otomatis build dan buat Release
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions akan otomatis:
1. Build file `.ipk`
2. Upload ke halaman **Releases**
3. Bisa langsung didownload dan diinstall ke router

---

## 🗂 Struktur File

```
luci-app-aria2-bot-IRF/
├── .github/
│   └── workflows/
│       └── build-ipk.yml          # GitHub Actions: auto-build IPK
├── scripts/
│   └── build-ipk.sh               # Script build IPK lokal
├── Makefile                        # OpenWrt package Makefile
├── luasrc/
│   ├── controller/
│   │   └── aria2bot.lua           # LuCI controller (menu & API)
│   ├── model/cbi/aria2bot/
│   │   └── settings.lua           # Form konfigurasi
│   └── view/aria2bot/
│       └── dashboard.htm          # Halaman dashboard
└── root/
    ├── etc/
    │   ├── init.d/
    │   │   ├── aria2rpc           # Aria2 RPC service
    │   │   └── telegram_bot       # Telegram bot service
    │   ├── config/
    │   │   └── aria2bot           # UCI config default
    │   ├── uci-defaults/
    │   │   └── luci-aria2bot      # Runs once after install
    │   └── aria2bot/
    │       └── install-deps.sh    # Auto-install Python deps
    └── usr/bin/
        └── telegram_download_bot.py  # Bot script (baca UCI config)
```

---

## 🔧 Build IPK Lokal

```bash
# Clone repo
git clone https://github.com/irfanFRizki/Aria2-bot.git
cd Aria2-bot

# Build
chmod +x scripts/build-ipk.sh
./scripts/build-ipk.sh 1.0.0

# IPK ada di:
ls dist/
```

---

## 📝 Log & Troubleshoot

```bash
# Lihat log bot
logread | grep telegram_download_bot

# Lihat log aria2
tail -f /tmp/aria2rpc.log

# Lihat log instalasi dependency
tail -f /tmp/aria2bot-install.log

# Cek status service
/etc/init.d/telegram_bot status
/etc/init.d/aria2rpc status

# Restart semua
/etc/init.d/aria2rpc restart
/etc/init.d/telegram_bot restart
```

---

## 👤 Maintainer

**irfanFRizki** — [github.com/irfanFRizki](https://github.com/irfanFRizki)

Lisensi: MIT
