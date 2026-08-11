---
name: windows-disk-cleanup
description: "Scan and clean Windows disk junk: temp files, caches, crash dumps, Windows Update leftovers, WinSxS. Multi-phase approach with non-admin then admin elevation."
version: 1.0.0
---

# Windows Disk Cleanup

## Activation
When task involves: cleaning disk space, removing junk files, temp files, Windows Update cache, crash dumps, browser caches, freeing up space on C: drive.

## Not for
- User file organization (see file-management skill)
- Uninstalling applications
- Deep WinSxS component store cleanup (use DISM directly)

## 3-Phase Approach

### Phase 1: Non-Admin Cleanup (safe, no UAC)
Run a Python scan+clean script that targets:
- User Temp (`%USERPROFILE%\AppData\Local\Temp`)
- Crash dumps (`%USERPROFILE%\AppData\Local\CrashDumps`, `%WINDIR%\Minidump`, `%WINDIR%\MEMORY.DMP`)
- Recycle Bin (via `Clear-RecycleBin -Force`)
- Browser caches: Edge (`Cache`, `Code Cache`, `GPUCache`, `Service Worker`), Firefox (`cache2`, `startupCache`)
- Thumbnail cache (`thumbcache_*.db`)
- `*.tmp` files (surface scan in AppData, Downloads, Desktop)

### Phase 2: Admin Cleanup (requires UAC approval)
Write a `.ps1` script to `%USERPROFILE%\`, then run via:
```
powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File <script>' -Verb RunAs -Wait"
```
This triggers UAC — tell Sếp to click Yes.

Admin-only targets:
- Windows Update cache (`%WINDIR%\SoftwareDistribution\Download`) — stop `wuauserv` first, clean, then restart
- Windows Logs (`%WINDIR%\Logs\CBS`, `DISM`, `WindowsUpdate`)
- Delivery Optimization cache
- `%WINDIR%\Temp`
- DISM: `dism /online /cleanup-image /startcomponentcleanup`

### Phase 3: WinSxS Temp (stubborn)
WinSxS\Temp files are locked by TrustedInstaller. Need escalation sequence in the admin script:
1. `takeown /F "%WINDIR%\WinSxS\Temp" /R /D Y`
2. `icacls "%WINDIR%\WinSxS\Temp" /grant "Administrators:(OI)(CI)F" /T /Q`
3. Delete files one-by-one (not rmtree)

Even after this, **pending rename/delete operations survive until reboot**. Expect ~30-40% to remain.

## Key Pitfalls

1. **DISM error 740**: DISM MUST run from a truly elevated process. Running from a non-elevated terminal with `Start-Process -Verb RunAs` works because it spawns a new elevated window.

2. **wuauserv must be stopped** before cleaning `SoftwareDistribution\Download`, then restarted. If you skip the restart, Windows Update breaks until next reboot.

3. **WinSxS\Temp is NOT fully cleanable while Windows is running** — pending file operations (renames/deletes scheduled for next boot) live here. The remainder (~30-40%) clears after reboot.

4. **Scan before clean**: Always run a scan pass first to report what exists and how much space it's taking. Don't delete blindly.

5. **Browser caches**: Chrome/Edge may hold file locks while running. Clean only directories, not the browser profile itself.

## Completion Criteria
- Scan report delivered with before/after disk usage
- All Phase 1 targets cleaned
- Phase 2 targets cleaned (with UAC cooperation)
- Phase 3 attempted (partial success expected)
- Cleanup scripts removed from user directory
- Remaining items documented (e.g., "604 MB WinSxS pending — clears after reboot")

## Reference
- `references/scan-targets.md` — complete map of junk locations with paths and typical sizes
- `references/admin-elevation.md` — PowerShell admin elevation patterns and script templates
