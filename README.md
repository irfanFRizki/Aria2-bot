# 🤖 Aria2 Bot — Telegram Download Bot for OpenWrt

[![Build & Release IPK](https://github.com/irfanFRizki/Aria2-bot/actions/workflows/build-ipk.yml/badge.svg)](https://github.com/irfanFRizki/Aria2-bot/actions/workflows/build-ipk.yml)

Bot Telegram untuk mengontrol Aria2 download manager di router OpenWrt, dilengkapi dengan UI LuCI (Dashboard + Settings).

---

## ✨ Fitur

- **Bot Telegram** — Download file via perintah chat Telegram
- **LuCI Dashboard** — Monitor status bot, aria2, dan statistik download
- **LuCI Settings** — Konfigurasi bot token, allowed users, RPC via web UI
- **Auto-start** — Service procd otomatis berjalan saat boot
- **Queue System** — Antrian download dengan retry otomatis
- **Auto HDD Detection** — Otomatis deteksi lokasi penyimpanan (/mnt/sda1, dst.)

---

## 📦 Cara Install

### Metode 1: Auto-Installer (Termux/SSH)
```bash
wget https://raw.githubusercontent.com/irfanFRizki/Aria2-bot/main/install.sh -O /tmp/install.sh
sh /tmp/install.sh
```

### Metode 2: Manual dari Releases
```bash
# 1. Update opkg
opkg update

# 2. Install dependencies
opkg install python3 python3-pip aria2 curl

# 3. Install Python packages
pip3 install python-telegram-bot aiohttp --break-system-packages

# 4. Download IPK terbaru dari Releases
wget https://github.com/irfanFRizki/Aria2-bot/releases/latest/download/luci-app-aria2-bot-IRF_*.ipk \
  -O /tmp/aria2bot.ipk

# 5. Install
opkg install /tmp/aria2bot.ipk
```

### Metode 3: Build dari Source (OpenWrt SDK)
```bash
# Clone ke dalam feeds atau package dir SDK
git clone https://github.com/irfanFRizki/Aria2-bot.git package/luci-app-aria2-bot-IRF
make package/luci-app-aria2-bot-IRF/compile V=s
```

---

## ⚙️ Konfigurasi

Setelah install, buka LuCI:

1. Pergi ke **Services → Aria2 Bot → Settings**
2. Isi parameter berikut:

| Parameter | Deskripsi |
|-----------|-----------|
| **Bot Token** | Token dari [@BotFather](https://t.me/BotFather) |
| **Allowed User IDs** | ID Telegram yang diizinkan (dari [@userinfobot](https://t.me/userinfobot)) |
| **Aria2 RPC URL** | Default: `http://localhost:6800/jsonrpc` |
| **Aria2 RPC Secret** | Kosongkan jika tidak pakai secret |
| **Max Download Bersamaan** | 1–5 download (default: 2) |
| **Direktori Download** | Path simpan file (default: `/mnt/sda1/downloads`) |
| **Auto Start saat Boot** | Centang agar bot otomatis hidup |

3. Klik **Save & Apply**
4. Pergi ke **Services → Aria2 Bot → Dashboard**
5. Klik **▶ Start Bot**

---

## 📱 Perintah Bot Telegram

| Perintah | Fungsi |
|----------|--------|
| `/start` | Mulai bot & tampilkan menu |
| `/help` | Tampilkan bantuan |
| `/status` | Status download aktif |
| `/queue` | Lihat antrian download |
| Kirim URL | Mulai download file dari URL |

---

## 📋 Dependency

| Package | Instalasi |
|---------|-----------|
| python3 | `opkg install python3` |
| python-telegram-bot | `pip3 install python-telegram-bot` |
| aiohttp | `pip3 install aiohttp` |
| aria2 | `opkg install aria2` |
| curl | `opkg install curl` |

---

## 🚀 Upload ke GitHub via Termux

```bash
# Install git di Termux
pkg install git

# Setup identity
git config --global user.name "irfanFRizki"
git config --global user.email "your@email.com"

# Clone repo baru (buat dulu di github.com)
git clone https://github.com/irfanFRizki/Aria2-bot.git
cd Aria2-bot

# Salin semua file dari ZIP ke sini, lalu:
git add .
git commit -m "Initial release: Aria2 Bot LuCI package"
git push origin main
```

GitHub Actions akan otomatis build .ipk dan buat Release.

---

## 📁 Struktur Project

```
luci-app-aria2-bot-IRF/
├── .github/
│   └── workflows/
│       └── build-ipk.yml       # Auto build & release
├── package/
│   └── luci-app-aria2-bot-IRF/
│       ├── Makefile            # OpenWrt package definition
│       ├── luasrc/
│       │   ├── controller/
│       │   │   └── aria2bot.lua    # LuCI routing & API
│       │   ├── model/cbi/
│       │   │   └── aria2bot.lua    # Settings form
│       │   └── view/aria2bot/
│       │       └── dashboard.htm   # Dashboard UI
│       └── root/
│           ├── usr/bin/
│           │   └── telegram_download_bot.py
│           ├── etc/init.d/
│           │   └── telegram_bot    # procd service
│           ├── etc/config/
│           │   └── aria2bot        # UCI config
│           └── etc/uci-defaults/
│               └── luci-aria2bot
├── install.sh                  # One-liner installer
└── README.md
```

---

## 🛠️ Troubleshooting

**Bot tidak mau start?**
```bash
logread -e telegram_bot
```

**Aria2 RPC tidak tersambung?**
```bash
/etc/init.d/aria2 start
# atau
aria2c --enable-rpc --rpc-listen-all=true --daemon=true
```

**Python packages tidak ada?**
```bash
pip3 install python-telegram-bot aiohttp --break-system-packages
```

**LuCI menu tidak muncul?**
```bash
rm -rf /tmp/luci-*
/etc/init.d/rpcd restart
```

---

## 📄 License

MIT License — [irfanFRizki](https://github.com/irfanFRizki)
