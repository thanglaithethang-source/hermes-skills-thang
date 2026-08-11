# Windows Junk Scanner — Python Script
# Scans all common junk locations and reports sizes.
# Safe: read-only, no deletions.

import os
import shutil
from pathlib import Path

user = os.environ.get('USERPROFILE', 'C:\\Users\\thang')
windir = os.environ.get('WINDIR', 'C:\\Windows')

def get_size(path):
    try:
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            try:
                for f in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, f))
                    except:
                        pass
            except:
                pass
        return total
    except:
        return 0

def count_files(path):
    try:
        count = 0
        for dirpath, dirnames, filenames in os.walk(path):
            count += len(filenames)
        return count
    except:
        return 0

def fmt(sz):
    if sz >= 1024**3:
        return f"{sz / 1024**3:.2f} GB"
    elif sz >= 1024**2:
        return f"{sz / 1024**2:.2f} MB"
    elif sz >= 1024:
        return f"{sz / 1024:.2f} KB"
    return f"{sz} B"

# ── Scan targets ──
targets = {
    'Windows Temp': os.path.join(windir, 'Temp'),
    'User Temp': os.path.join(user, 'AppData', 'Local', 'Temp'),
    'Prefetch': os.path.join(windir, 'Prefetch'),
}

for drive in ['C:\\', 'D:\\', 'E:\\', 'F:\\']:
    rb = os.path.join(drive, '$Recycle.Bin')
    if os.path.exists(rb):
        targets[f'{drive} Recycle Bin'] = rb

browser_paths = {
    'Chrome Cache': os.path.join(user, 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
    'Edge Cache': os.path.join(user, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
    'Edge GPUCache': os.path.join(user, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'GPUCache'),
    'Firefox Cache': os.path.join(user, 'AppData', 'Local', 'Mozilla', 'Firefox', 'Profiles'),
}

system_junk = {
    'Windows Update DL': os.path.join(windir, 'SoftwareDistribution', 'Download'),
    'WinSxS Temp': os.path.join(windir, 'WinSxS', 'Temp'),
    'WER CrashDumps': os.path.join(user, 'AppData', 'Local', 'CrashDumps'),
    'System Minidump': os.path.join(windir, 'Minidump'),
    'Memory Dump': os.path.join(windir, 'MEMORY.DMP'),
    'CBS Logs': os.path.join(windir, 'Logs', 'CBS'),
    'DISM Logs': os.path.join(windir, 'Logs', 'DISM'),
    'Thumbnail Cache': os.path.join(user, 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer'),
}

all_targets = {**targets, **browser_paths, **system_junk}

total = 0
print(f"{'Location':<30} {'Size':>12} {'Files':>8}")
print("-" * 52)
for name, path in all_targets.items():
    if os.path.exists(path):
        if os.path.isfile(path):
            sz = os.path.getsize(path)
            fc = 1
        else:
            sz = get_size(path)
            fc = count_files(path)
        print(f"{name:<30} {fmt(sz):>12} {fc:>8,}")
        total += sz
    else:
        print(f"{name:<30} {'N/A':>12}")

print("-" * 52)
print(f"{'TOTAL':<30} {fmt(total):>12}")

# Disk usage
for drive in ['C:\\', 'D:\\']:
    try:
        u = shutil.disk_usage(drive)
        pct = u.used / u.total * 100
        print(f"{drive} {fmt(u.free)} free / {fmt(u.total)} ({pct:.1f}% used)")
    except:
        pass
