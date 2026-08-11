# Windows Junk Cleaner — Python Script
# Deletes junk from all safe + medium-risk locations.
# Run AFTER scan-junk.py to know what you're deleting.
# DISM and locked logs require admin — those are NOT handled here.

import os
import sys
import shutil
import subprocess

user = os.environ.get('USERPROFILE', 'C:\\Users\\thang')
windir = os.environ.get('WINDIR', 'C:\\Windows')
total_freed = 0

def fmt(sz):
    if sz >= 1024**3:
        return f"{sz / 1024**3:.2f} GB"
    elif sz >= 1024**2:
        return f"{sz / 1024**2:.2f} MB"
    elif sz >= 1024:
        return f"{sz / 1024:.2f} KB"
    return f"{sz} B"

def del_dir(path):
    """Delete all contents of a directory, return (size, count)"""
    if not os.path.exists(path):
        return 0, 0
    size, count = 0, 0
    try:
        for item in os.listdir(path):
            ip = os.path.join(path, item)
            try:
                if os.path.isfile(ip) or os.path.islink(ip):
                    sz = os.path.getsize(ip)
                    os.unlink(ip)
                    size += sz
                    count += 1
                elif os.path.isdir(ip):
                    dirsz = 0
                    for dp, dn, fn in os.walk(ip):
                        for f in fn:
                            try:
                                dirsz += os.path.getsize(os.path.join(dp, f))
                            except:
                                pass
                    try:
                        shutil.rmtree(ip, ignore_errors=True)
                        size += dirsz
                        count += 1
                    except:
                        pass
            except:
                pass
    except:
        pass
    return size, count

# ── 1. User Temp ──
sz, cnt = del_dir(os.path.join(user, 'AppData', 'Local', 'Temp'))
print(f"User Temp: {fmt(sz)} ({cnt} items)")
total_freed += sz

# ── 2. Crash Dumps ──
wer = os.path.join(user, 'AppData', 'Local', 'CrashDumps')
if os.path.exists(wer):
    sz, cnt = 0, 0
    for f in os.listdir(wer):
        if f.lower().endswith('.dmp'):
            try:
                fp = os.path.join(wer, f)
                sz += os.path.getsize(fp)
                os.remove(fp)
                cnt += 1
            except:
                pass
    print(f"WER CrashDumps: {fmt(sz)} ({cnt} files)")
    total_freed += sz

mem_dump = os.path.join(windir, 'MEMORY.DMP')
if os.path.exists(mem_dump):
    try:
        sz = os.path.getsize(mem_dump)
        os.remove(mem_dump)
        print(f"MEMORY.DMP: {fmt(sz)}")
        total_freed += sz
    except:
        pass

# ── 3. Recycle Bin ──
subprocess.run(['powershell', '-Command', 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'],
               capture_output=True, text=True)
print("Recycle Bin: emptied")

# ── 4. Browser Caches ──
edge_base = os.path.join(user, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default')
for cache_name in ['Cache', 'Code Cache', 'GPUCache', 'Service Worker']:
    cp = os.path.join(edge_base, cache_name)
    if os.path.exists(cp):
        sz, cnt = del_dir(cp)
        print(f"Edge {cache_name}: {fmt(sz)}")
        total_freed += sz

ff_profiles = os.path.join(user, 'AppData', 'Local', 'Mozilla', 'Firefox', 'Profiles')
if os.path.exists(ff_profiles):
    try:
        for profile in os.listdir(ff_profiles):
            for cd_name in ['cache2', 'startupCache']:
                cd = os.path.join(ff_profiles, profile, cd_name)
                if os.path.exists(cd):
                    sz, cnt = del_dir(cd)
                    print(f"Firefox {cd_name}: {fmt(sz)}")
                    total_freed += sz
    except:
        pass

# ── 5. Thumbnail Cache ──
explorer_dir = os.path.join(user, 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer')
if os.path.exists(explorer_dir):
    tsz, tcnt = 0, 0
    try:
        for f in os.listdir(explorer_dir):
            fl = f.lower()
            if 'thumbcache' in fl or (fl.endswith('.db') and 'thumb' in fl):
                fp = os.path.join(explorer_dir, f)
                try:
                    tsz += os.path.getsize(fp)
                    os.remove(fp)
                    tcnt += 1
                except:
                    pass
    except:
        pass
    print(f"Thumbnail Cache: {fmt(tsz)} ({tcnt} files)")
    total_freed += tsz

# ── 6. Windows Update Cache (must stop wuauserv) ──
update_dl = os.path.join(windir, 'SoftwareDistribution', 'Download')
if os.path.exists(update_dl):
    subprocess.run(['net', 'stop', 'wuauserv'], capture_output=True, timeout=15)
    sz, cnt = del_dir(update_dl)
    subprocess.run(['net', 'start', 'wuauserv'], capture_output=True, timeout=15)
    print(f"Windows Update DL: {fmt(sz)} ({cnt} items)")
    total_freed += sz

# ── 7. WinSxS Temp ──
winsxs_temp = os.path.join(windir, 'WinSxS', 'Temp')
if os.path.exists(winsxs_temp):
    sz, cnt = del_dir(winsxs_temp)
    print(f"WinSxS Temp: {fmt(sz)} ({cnt} items)")
    total_freed += sz

# ── 8. DISM (requires admin — will fail without) ──
print("\nDISM cleanup (may fail without admin):")
result = subprocess.run(
    ['dism', '/online', '/cleanup-image', '/startcomponentcleanup'],
    capture_output=True, text=True, timeout=300
)
if result.returncode == 0:
    print("  OK")
elif result.returncode == 740:
    print("  BLOCKED: Error 740 — Elevated permissions required. Run as admin.")
else:
    print(f"  Exit {result.returncode}: {(result.stdout + result.stderr)[:300]}")

# ── Summary ──
print(f"\nTOTAL FREED: {fmt(total_freed)}")
