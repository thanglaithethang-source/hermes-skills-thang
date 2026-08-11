# PowerShell Admin Elevation

## Running Admin Scripts from Non-Elevated Terminal

Spawn an elevated PowerShell process that runs a script and waits for completion:

```bash
powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File C:\Users\thang\script.ps1' -Verb RunAs -Wait"
```

- `-NoProfile`: faster startup, no profile pollution
- `-ExecutionPolicy Bypass`: allow unsigned scripts
- `-Verb RunAs`: triggers UAC elevation
- `-Wait`: blocks until the elevated script completes

## Pitfalls

1. **No stdout capture**: Output from the elevated process goes to its own console window, not back to the parent terminal. Use `-Wait` and then verify results via separate read commands.

2. **UAC popup**: The user MUST click Yes on the UAC dialog. Tell them explicitly: "Sếp bấm Yes khi UAC pop-up".

3. **File path**: Use absolute paths. The elevated process runs as a different user context and may not share the same working directory.

4. **DISM within elevated script**: Even with elevation, DISM may need the script to be in a truly elevated context (not just the process, but the console session). Using `Start-Process -Verb RunAs` satisfies this.

## Admin Script Template

```powershell
$windir = $env:WINDIR

Write-Host "=== Task Description ==="

# Phase 1: Stop services if needed
# net stop wuauserv

# Phase 2: Take ownership (if TrustedInstaller lock)
# takeown /F "$path" /R /D Y
# icacls "$path" /grant "Administrators:(OI)(CI)F" /T /Q

# Phase 3: Delete
# Remove-Item -Path "$path\*" -Recurse -Force -ErrorAction SilentlyContinue

# Phase 4: Restart services
# net start wuauserv

Write-Host "=== Complete ==="
```

## WinSxS Temp Specific Pattern

```powershell
$winsxsTemp = "$env:WINDIR\WinSxS\Temp"

# Count before
$items = Get-ChildItem -Path $winsxsTemp -Recurse -File -ErrorAction SilentlyContinue
$totalSize = ($items | Measure-Object -Property Length -Sum).Sum

# Take ownership
takeown /F "$winsxsTemp" /R /D Y

# Grant permissions
icacls "$winsxsTemp" /grant "Administrators:(OI)(CI)F" /T /Q

# Delete one-by-one (rmtree may fail on locked dirs)
$deleted = 0; $failed = 0
foreach ($item in $items) {
    try {
        Remove-Item -Path $item.FullName -Force -ErrorAction Stop
        $deleted++
    } catch { $failed++ }
}

# Clean empty dirs
Get-ChildItem -Path $winsxsTemp -Directory | ForEach-Object {
    try { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction Stop } catch {}
}

Write-Host "Deleted: $deleted, Failed: $failed"
```
