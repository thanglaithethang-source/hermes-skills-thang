# Windows Junk Scan Targets

Complete map of junk locations scanned during disk cleanup. Paths use Windows environment variable notation.

## Temp Directories

| Location | Path | Typical Size | Admin? |
|----------|------|-------------|--------|
| User Temp | `%USERPROFILE%\AppData\Local\Temp` | 300-800 MB | No |
| Windows Temp | `%WINDIR%\Temp` | 0-100 MB | No |
| Prefetch | `%WINDIR%\Prefetch` | variable | No |

## Windows Update

| Location | Path | Typical Size | Admin? |
|----------|------|-------------|--------|
| Update Cache | `%WINDIR%\SoftwareDistribution\Download` | 500 MB - 2 GB | Yes (need stop wuauserv) |
| Update Logs | `%WINDIR%\Logs\WindowsUpdate` | 10-50 MB | Yes |
| WinSxS Temp | `%WINDIR%\WinSxS\Temp` | 500 MB - 1.5 GB | Yes (TrustedInstaller lock) |

## Crash & Error Reports

| Location | Path | Typical Size | Admin? |
|----------|------|-------------|--------|
| WER (User) | `%USERPROFILE%\AppData\Local\CrashDumps` | 100-500 MB | No |
| Minidump | `%WINDIR%\Minidump` | 0-100 MB | Yes |
| Memory Dump | `%WINDIR%\MEMORY.DMP` | 0 - several GB | Yes |

## System Logs

| Location | Path | Typical Size | Admin? |
|----------|------|-------------|--------|
| CBS Logs | `%WINDIR%\Logs\CBS` | 100-500 MB | Yes |
| DISM Logs | `%WINDIR%\Logs\DISM` | 10-50 MB | Yes |

## Browser Caches

| Browser | Path | Typical Size |
|---------|------|-------------|
| Chrome/Edge Cache | `%LOCALAPPDATA%\...\User Data\Default\Cache` | 50-200 MB |
| Chrome/Edge Code Cache | `%LOCALAPPDATA%\...\User Data\Default\Code Cache` | 10-100 MB |
| Chrome/Edge GPUCache | `%LOCALAPPDATA%\...\User Data\Default\GPUCache` | 1-20 MB |
| Chrome/Edge Service Worker | `%LOCALAPPDATA%\...\User Data\Default\Service Worker` | 10-100 MB |
| Firefox cache2 | `%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*\cache2` | 20-100 MB |

Exact paths:
- Edge: `%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\`
- Chrome: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\`

## Miscellaneous

| Location | Path | Typical Size |
|----------|------|-------------|
| Thumbnail Cache | `%USERPROFILE%\AppData\Local\Microsoft\Windows\Explorer\thumbcache_*.db` | 50-150 MB |
| Recycle Bin | `*\$Recycle.Bin` on all drives | variable |
| Delivery Optimization | `%WINDIR%\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache` | variable |

## Wildcard Scans

Surface scan (limited depth, in `%USERPROFILE%\AppData`, Downloads, Documents, Desktop):
- `*.tmp` files
- `*.dmp` files
- `*.log` files > 1 MB
