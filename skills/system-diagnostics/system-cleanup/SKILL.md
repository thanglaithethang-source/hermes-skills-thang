---
name: system-cleanup
description: Disk space reclamation & junk removal — scan and clean temp files, caches, logs, crash dumps, update leftovers on Windows/macOS/Linux.
version: 1.0.0
---

# System Cleanup

## Activation
When task involves: scanning for junk files, freeing disk space, cleaning system temp/cache/logs, "dọn rác máy tính", disk almost full.

## Not for
Uninstalling apps, defragmenting, registry cleaning (use specialized tools).

## Workflow
1. **Scan first** — never delete blind. Use scripts/references for known junk paths.
2. **Sort by safety**: user-safe (temp, browser cache, recycle bin, thumbnails) → system-safe (update cache, crash dumps) → system-risky (WinSxS, logs).
3. **Clean in order** — safe items first. Each category: delete → verify → next.
4. **Stop services if needed** — e.g. `wuauserv` before touching SoftwareDistribution\Download. ALWAYS restart after.
5. **Verify disk space** — compare `shutil.disk_usage()` before and after.
6. **Report**: what was deleted (size + file count), what couldn't be deleted (reason), remaining issues.

## Windows Junk Paths (verified paths)

### High-yield, safe to delete:
| Path | Description |
|------|-------------|
| `%USERPROFILE%\AppData\Local\Temp` | User temp files |
| `%WINDIR%\Temp` | System temp |
| `%USERPROFILE%\AppData\Local\CrashDumps` | App crash dumps (.dmp) |
| `%WINDIR%\Minidump` | System minidumps |
| `%WINDIR%\MEMORY.DMP` | Full memory dump |
| `$Recycle.Bin` on each drive | Recycle Bin |
| `%USERPROFILE%\AppData\Local\Microsoft\Edge\User Data\Default\Cache` | Edge cache |
| `%USERPROFILE%\AppData\Local\Microsoft\Edge\User Data\Default\GPUCache` | Edge GPU cache |
| `%USERPROFILE%\AppData\Local\Microsoft\Edge\User Data\Default\Code Cache` | Edge code cache |
| `%USERPROFILE%\AppData\Local\Microsoft\Edge\User Data\Default\Service Worker` | Edge SW cache |
| `%USERPROFILE%\AppData\Local\Mozilla\Firefox\Profiles\*\cache2` | Firefox cache |
| `%USERPROFILE%\AppData\Local\Microsoft\Windows\Explorer\thumbcache_*` | Thumbnail cache |

### Medium risk (stop services first):
| Path | Prerequisite |
|------|-------------|
| `%WINDIR%\SoftwareDistribution\Download` | `net stop wuauserv` → delete → `net start wuauserv` |
| `%WINDIR%\WinSxS\Temp` | Can delete directly |

### Requires admin / special tools:
| Target | Method |
|--------|--------|
| WinSxS component store | `dism /online /cleanup-image /startcomponentcleanup` (admin required) |
| Windows Logs (CBS, DISM, WindowsUpdate) | Often locked; requires admin |
| Delivery Optimization cache | Settings > Storage or admin |

## Pitfalls

- **DISM error 740** = "Elevated permissions are required." The agent session is NOT running as admin. Instead of giving up, use admin elevation: write a `.ps1` script, then run `powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File <script>' -Verb RunAs -Wait"`. This spawns an elevated window — tell user to click Yes on UAC. For the full multi-phase Windows cleanup workflow see the `windows-disk-cleanup` skill.
- **Windows Logs locked** — CBS/DISM/WindowsUpdate logs under `%WINDIR%\Logs\` are often held by system processes. Clean them from an admin-elevated script (see pattern above), not from the non-elevated session.
- **WinSxS\Temp stubborn files** — locked by TrustedInstaller. In the elevated script: (1) `takeown /F "..." /R /D Y`, (2) `icacls "..." /grant "Administrators:(OI)(CI)F" /T /Q`, (3) delete files individually. Pending rename/delete operations survive until reboot.
- **wuauserv must restart** — if you stop it to clean SoftwareDistribution, ALWAYS restart it. Check with `sc query wuauserv`.
- **Files in use** — `shutil.rmtree` with `ignore_errors=True` handles most cases. Individual `os.unlink` calls wrapped in try/except for locked files.
- **Recycle Bin** — use PowerShell `Clear-RecycleBin -Force` instead of raw `rd` which can fail on permissions.

## Verification
- Run `shutil.disk_usage('C:\\')` before and after.
- Track `total_freed` accumulator across all delete operations.
- Cross-check: expected freed vs actual disk change — mismatch means files were on a different drive or system-reserved space.

## Scripts
- `references/scan-junk.py` — scan-only (safe, no deletions). Run first to size up the junk.
- `references/clean-junk.py` — deletes everything safe + medium-risk. Stops/restarts wuauserv. DISM attempted but may fail without admin.

## Completion Criteria
- All safe targets cleaned
- Admin-required targets either completed OR reported as blocked with exact error
- Disk usage before/after confirmed
- Blocked items listed with resolution path (e.g. "run as admin and execute: dism /online /cleanup-image /startcomponentcleanup")
