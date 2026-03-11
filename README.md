# Aria2 Bot for OpenWrt 🤖

**Aria2 Telegram Bot** sebagai paket `.ipk` untuk OpenWrt, lengkap dengan:
- 🖥️ **LuCI Web Interface** — Menu `Services > Aria2 Bot`
- 📊 **Dashboard** — Status bot, Aria2, dan download aktif secara realtime
- ⚙️ **Settings Page** — Input Telegram Bot Token langsung dari browser
- 🔄 **Auto-install dependencies** — Otomatis install `aria2`, `python3`, dll.
- 🏗️ **GitHub Actions** — IPK di-build otomatis setiap ada push

---

## 📦 Instalasi di OpenWrt

### Cara 1 — Download dari Releases

```sh
# Di router OpenWrt:
cd /tmp
wget https://github.com/YOUR_USERNAME/aria2bot-openwrt/releases/latest/download/aria2bot_1.0.0_all.ipk
wget https://github.com/YOUR_USERNAME/aria2bot-openwrt/releases/latest/download/luci-app-aria2bot_1.0.0_all.ipk

opkg install aria2bot_*.ipk
opkg install luci-app-aria2bot_*.ipk
```

### Cara 2 — Install Manual via opkg

```sh
opkg update
opkg install aria2 python3

# Copy script ke router, lalu:
opkg install /tmp/aria2bot_*.ipk
```

---

## ⚙️ Konfigurasi

### Via LuCI (Recommended)
1. Buka **LuCI → Services → Aria2 Bot**
2. Klik tab **Settings**
3. Masukkan **Telegram Bot Token** (dapatkan dari [@BotFather](https://t.me/BotFather))
4. Masukkan **Telegram User ID** kamu (gunakan [@userinfobot](https://t.me/userinfobot))
5. Klik **Save & Apply**
6. Kembali ke **Dashboard**, klik **Start Bot** dan **Start Aria2**

### Via UCI (Command Line)
```sh
uci set aria2bot.settings.bot_token='YOUR_BOT_TOKEN_HERE'
uci set aria2bot.settings.allowed_users='YOUR_TELEGRAM_USER_ID'
uci set aria2bot.settings.download_dir='/mnt/usb/downloads'
uci set aria2bot.settings.enabled='1'
uci commit aria2bot

/etc/init.d/aria2rpc start
/etc/init.d/aria2bot start
```

---

## 📱 Perintah Telegram Bot

| Perintah | Fungsi |
|----------|--------|
| `/start` | Mulai / lihat bantuan |
| `/status` | Lihat download aktif |
| `/list` | Semua download (aktif, antrian, selesai) |
| `/add <url>` | Tambah URL download |
| `/stop <gid>` | Pause download |
| `/remove <gid>` | Hapus download |
| `/stats` | Statistik global (speed, jumlah) |
| `/version` | Versi Aria2 |

---

## 🏗️ Build dari Source

### Struktur Repository

```
aria2bot-openwrt/
├── .github/
│   └── workflows/
│       └── build-ipk.yml          # GitHub Actions auto-build
├── package/
│   └── aria2bot/
│       ├── Makefile                # OpenWrt package definition
│       └── files/
│           ├── usr/bin/
│           │   └── telegram_download_bot.py
│           ├── usr/lib/aria2bot/
│           │   └── install_deps.sh
│           ├── etc/
│           │   ├── init.d/
│           │   │   ├── aria2bot    # Bot service
│           │   │   ├── aria2rpc    # Aria2 RPC service
│           │   │   └── aria2       # Aria2 basic service
│           │   ├── config/
│           │   │   └── aria2bot    # UCI config
│           │   └── aria2/
│           │       └── aria2.conf  # Aria2 configuration
└── luci-app-aria2bot/
    ├── Makefile
    └── luasrc/
        ├── controller/
        │   └── aria2bot.lua        # LuCI routing + API
        ├── model/cbi/aria2bot/
        │   └── settings.lua        # Settings form
        └── view/aria2bot/
            └── dashboard.htm       # Dashboard UI
```

### Build Manual dengan OpenWrt SDK

```sh
# Download SDK
wget https://downloads.openwrt.org/releases/23.05.3/targets/x86/64/openwrt-sdk-23.05.3-x86-64_gcc-12.3.0_musl.Linux-x86_64.tar.xz
tar -xf openwrt-sdk-*.tar.xz
cd openwrt-sdk-*/

# Setup feeds
./scripts/feeds update -a
./scripts/feeds install -a

# Copy packages
cp -r ../package/aria2bot package/
cp -r ../luci-app-aria2bot package/

# Build
make package/aria2bot/compile V=s
make package/luci-app-aria2bot/compile V=s

# Cari IPK di:
find bin/ -name "*.ipk"
```

### Auto-build dengan GitHub Actions

Setiap kali ada **push ke `main`** yang mengubah file di `package/aria2bot/` atau `luci-app-aria2bot/`, GitHub Actions akan:
1. ✅ Validasi struktur file
2. 🔨 Build IPK dengan OpenWrt SDK
3. 📦 Upload artifact ke tab **Actions > Artifacts**

Untuk membuat **Release resmi**, buat tag:
```sh
git tag v1.0.1
git push origin v1.0.1
```
IPK akan otomatis di-attach ke GitHub Release.

---

## 🔧 Dependencies yang Di-install Otomatis

Saat package di-install, script `install_deps.sh` akan menjalankan:

```
aria2          — Download manager
python3        — Runtime untuk bot
python3-asyncio — Async support
curl           — HTTP client
ca-certificates — SSL certificates
```

---

## 📝 Lisensi

MIT License — © irfanFRizki
