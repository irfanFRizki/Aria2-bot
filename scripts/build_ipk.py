#!/usr/bin/env python3
"""
scripts/build_ipk.py
FORMAT KRITIS OpenWrt IPK:
  - Outer: gzip tar (BUKAN ar/deb!)
  - Entry names: bare filename TANPA ./ prefix
  - Urutan: debian-binary -> data.tar.gz -> control.tar.gz
  - debian-binary: b'2.0\n' (4 bytes)
"""

import argparse, io, json, os, sys, tarfile, time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()

FILE_MAP = [
    ("usr/bin/PL.py",                      "usr/bin/PL.py",                                  True),
    ("etc/init.d/pl-bot",                  "etc/init.d/pl-bot",                              True),
    ("etc/config/pl-bot",                  "etc/config/pl-bot",                              False),
    ("luci/controller/pl-bot.lua",         "usr/lib/lua/luci/controller/pl-bot.lua",         False),
    ("luci/model/cbi/pl-bot/settings.lua", "usr/lib/lua/luci/model/cbi/pl-bot/settings.lua", False),
    ("luci/view/pl-bot/dashboard.htm",     "usr/lib/lua/luci/view/pl-bot/dashboard.htm",     False),
]

def make_control(version, build):
    return f"""Package: luci-app-pl-bot
Version: {version}-{build}
Depends: python3, python3-pip, luci-base, curl
Architecture: all
Maintainer: PL Bot
Section: luci
Priority: optional
Description: Inventory Management Bot v{version} (Telegram + Google Sheets + LuCI)
"""

def make_postinst(version):
    return f"""#!/bin/sh
set -e
chmod 755 /usr/bin/PL.py
chmod 755 /etc/init.d/pl-bot
if ! uci -q get pl-bot.settings > /dev/null 2>&1; then
    uci set pl-bot.settings=pl-bot
    uci set pl-bot.settings.telegram_token=''
    uci set pl-bot.settings.admin_chat_ids=''
    uci set pl-bot.settings.sheets_url=''
    uci set pl-bot.settings.spreadsheet_id=''
    uci set pl-bot.settings.credentials_file='/root/credentials.json'
    uci set pl-bot.settings.update_interval='60'
    uci set pl-bot.settings.backup_dir='/root/pl-bot-backups'
    uci set pl-bot.settings.daily_report_hour='8'
    uci set pl-bot.settings.daily_report_min='0'
    uci set pl-bot.settings.enabled='0'
    uci commit pl-bot
fi
mkdir -p /root/pl-bot-backups
touch /var/log/pl-bot.log
chmod 644 /var/log/pl-bot.log
opkg update > /dev/null 2>&1 || true
opkg install python3 python3-pip > /dev/null 2>&1 || true
pip3 install --upgrade python-telegram-bot gspread oauth2client requests > /dev/null 2>&1 || true
/etc/init.d/pl-bot enable 2>/dev/null || true
/etc/init.d/rpcd restart > /dev/null 2>&1 || true
exit 0
"""

def make_prerm():
    return """#!/bin/sh
/etc/init.d/pl-bot stop    > /dev/null 2>&1 || true
/etc/init.d/pl-bot disable > /dev/null 2>&1 || true
rm -f /var/run/pl-bot.pid /var/run/pl-bot-stats.json /var/run/pl-bot-state.json
rm -f /var/run/pl-bot-notif.json /var/run/pl-bot-calendar.json
exit 0
"""

def make_conffiles():
    return "/etc/config/pl-bot\n"

def build_ipk_outer(debian_binary, data_tar_gz, control_tar_gz):
    """OpenWrt IPK = plain gzip tar, BUKAN ar format."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in [
            ("debian-binary",  debian_binary),
            ("data.tar.gz",    data_tar_gz),
            ("control.tar.gz", control_tar_gz),
        ]:
            if isinstance(data, str): data = data.encode()
            info = tarfile.TarInfo(name=name)  # bare name, NO ./
            info.size = len(data); info.mtime = int(time.time()); info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()

def build_data_tar_gz(file_map, repo_root, version, build, commit):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for src_rel, dst, executable in file_map:
            src_path = repo_root / src_rel
            if not src_path.exists():
                print(f"  WARNING: {src_rel} not found, skipping."); continue
            content = open(src_path, "rb").read()
            info = tarfile.TarInfo(name="./" + dst)
            info.size = len(content); info.mtime = int(time.time())
            info.mode = 0o755 if executable else 0o644
            tar.addfile(info, io.BytesIO(content))
            print(f"  {dst:<65} {len(content)/1024:6.1f} KB")
    return buf.getvalue()

def build_control_tar_gz(version, build):
    buf = io.BytesIO()
    files = {
        "./control"  : (make_control(version, build), 0o644),
        "./postinst" : (make_postinst(version),        0o755),
        "./prerm"    : (make_prerm(),                  0o755),
        "./conffiles": (make_conffiles(),              0o644),
    }
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for arcname, (content_str, mode) in files.items():
            content = content_str.encode()
            info = tarfile.TarInfo(name=arcname)
            info.size = len(content); info.mtime = int(time.time()); info.mode = mode
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()

def build(version, build_num, commit, output_path, dry_run=False):
    print(f"\n{'='*56}\n  luci-app-pl-bot v{version} build {build_num}\n{'='*56}")
    if dry_run:
        for src, dst, _ in FILE_MAP:
            ok = "OK" if (REPO_ROOT/src).exists() else "MISSING"
            print(f"  [{ok}] {src} -> /{dst}")
        return
    missing = [s for s,_,_ in FILE_MAP if not (REPO_ROOT/s).exists()]
    if missing:
        print("MISSING files:", missing); sys.exit(1)
    print("\n[1/4] control.tar.gz ...")
    ctrl = build_control_tar_gz(version, build_num)
    print("\n[2/4] data.tar.gz ...")
    data = build_data_tar_gz(FILE_MAP, REPO_ROOT, version, build_num, commit)
    print("\n[3/4] IPK outer gzip tar ...")
    ipk = build_ipk_outer(b"2.0\n", data, ctrl)
    print("\n[4/4] Writing ...")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(ipk)
    print(f"\nDone: {out}  ({len(ipk)/1024:.1f} KB)")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", default=None)
    p.add_argument("--build",   default="1")
    p.add_argument("--commit",  default="unknown")
    p.add_argument("--output",  default=None)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not a.version:
        pj = REPO_ROOT / "package.json"
        a.version = json.load(open(pj))["version"] if pj.exists() else "2.0.0"
    if not a.output:
        a.output = str(REPO_ROOT / "dist" / f"luci-app-pl-bot_{a.version}-{a.build}_all.ipk")
    build(a.version, a.build, a.commit, a.output, a.dry_run)

if __name__ == "__main__":
    main()
