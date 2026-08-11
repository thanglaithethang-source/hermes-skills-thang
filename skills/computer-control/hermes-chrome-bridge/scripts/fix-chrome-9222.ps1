# fix-chrome-9222.ps1 — Kill Chrome, clean locks, start with debug port, auto-fallback
# =============================================================================
# Chrome 150 ignores --remote-debugging-port when using the main User Data
# directory, even after kill + lock cleanup. This script tries main profile
# first, then auto-falls back to an isolated --user-data-dir.
# =============================================================================
param(
    [int]$Port = 9222,
    [int]$StartupWaitSec = 8,
    [switch]$SkipVerification
)

$ErrorActionPreference = "Stop"
$chromeExe = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
$userDataDir = "${env:LOCALAPPDATA}\Google\Chrome\User Data"
$tempUserData = "${env:TEMP}\chrome-debug-9222"

Write-Host "=== Chrome Remote Debugging Port Fix ===" -ForegroundColor Cyan
Write-Host "Port target: $Port"
Write-Host "Chrome path: $chromeExe"

# ---------------------------------------------------------------------------
# STEP 1: Kill ALL Chrome processes
# ---------------------------------------------------------------------------
Write-Host "[1/5] Killing ALL Chrome processes..." -ForegroundColor Yellow

$chromeProcs = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($chromeProcs) {
    Write-Host "  Found $($chromeProcs.Count) chrome.exe process(es)"
    Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue

    $timeout = 10
    $elapsed = 0
    do {
        Start-Sleep -Milliseconds 500
        $elapsed += 0.5
        $remaining = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
    } while ($remaining -and $elapsed -lt $timeout)

    if ($remaining) {
        Write-Host "  WARNING: $($remaining.Count) chrome.exe still alive after ${timeout}s" -ForegroundColor Red
        Write-Host "  Trying taskkill /F /IM chrome.exe as last resort..."
        & taskkill /F /IM chrome.exe 2>$null
        Start-Sleep -Seconds 2
    }
}
$leftovers = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($leftovers) {
    Write-Host "  ERROR: Cannot kill all Chrome processes. Aborting." -ForegroundColor Red
    exit 1
}
Write-Host "  All Chrome processes terminated." -ForegroundColor Green

# ---------------------------------------------------------------------------
# STEP 2: Clean lock files
# ---------------------------------------------------------------------------
Write-Host "[2/5] Cleaning lock files..." -ForegroundColor Yellow
$lockFiles = @(
    "${userDataDir}\lockfile",
    "${userDataDir}\SingletonLock",
    "${userDataDir}\SingletonSocket",
    "${userDataDir}\SingletonCookie"
)
foreach ($f in $lockFiles) {
    if (Test-Path $f) {
        Remove-Item -Force $f -ErrorAction SilentlyContinue
        Write-Host "  Removed: $f"
    } else {
        Write-Host "  Not found: $(Split-Path $f -Leaf)"
    }
}
Write-Host "  Lock files cleaned." -ForegroundColor Green

# ---------------------------------------------------------------------------
# STEP 3: Start Chrome with remote debugging port (main User Data)
# ---------------------------------------------------------------------------
Write-Host "[3/5] Starting Chrome with --remote-debugging-port=$Port ..." -ForegroundColor Yellow
$chromeArgs = @(
    "--remote-debugging-port=$Port",
    "--remote-allow-origins=*",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-features=MediaRouter",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions-file-access-check",
    "--disable-web-security",
    "$userDataDir"
)
try {
    $chromeProcess = Start-Process -FilePath $chromeExe `
        -ArgumentList $chromeArgs `
        -WindowStyle Hidden `
        -PassThru
    Write-Host "  Chrome started (PID: $($chromeProcess.Id))" -ForegroundColor Green
} catch {
    Write-Host "  ERROR starting Chrome: $_" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# STEP 4: Verify port is listening
# ---------------------------------------------------------------------------
Write-Host "[4/5] Waiting ${StartupWaitSec}s for Chrome to bind port $Port ..." -ForegroundColor Yellow
Start-Sleep -Seconds $StartupWaitSec

$portOpen = $false
$tcpConn = netstat -ano 2>$null | Select-String ":$Port\s+.*LISTENING"

if ($tcpConn) {
    Write-Host "  SUCCESS: Port $Port is LISTENING" -ForegroundColor Green
    $portOpen = $true
} else {
    Write-Host "  FAIL: Port $Port is NOT listening." -ForegroundColor Red
    Write-Host "  Chrome PID $($chromeProcess.Id) is running but port not open."
    Write-Host "  This means Chrome attached to existing session / ignored --remote-debugging-port."
}

# ---------------------------------------------------------------------------
# STEP 5: Fallback — isolated temp user-data-dir
# ---------------------------------------------------------------------------
if (-not $portOpen) {
    Write-Host ""
    Write-Host "[5/5] FALLBACK: Trying with isolated --user-data-dir..." -ForegroundColor Yellow
    Write-Host "  Temp dir: $tempUserData"

    if ($chromeProcess -and !$chromeProcess.HasExited) {
        Stop-Process -Id $chromeProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2

    if (Test-Path $tempUserData) {
        Remove-Item -Recurse -Force $tempUserData -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $tempUserData -Force | Out-Null

    $fallbackArgs = @(
        "--remote-debugging-port=$Port",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-features=MediaRouter",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions-file-access-check",
        "--user-data-dir=$tempUserData"
    )

    try {
        $chromeProcess2 = Start-Process -FilePath $chromeExe `
            -ArgumentList $fallbackArgs `
            -WindowStyle Hidden `
            -PassThru
        Write-Host "  Chrome started (PID: $($chromeProcess2.Id))" -ForegroundColor Green
        Start-Sleep -Seconds $StartupWaitSec

        $tcpConn2 = netstat -ano 2>$null | Select-String ":$Port\s+.*LISTENING"
        if ($tcpConn2) {
            Write-Host "  SUCCESS: Port $Port is LISTENING with isolated profile!" -ForegroundColor Green
            $portOpen = $true
        } else {
            Write-Host "  FAIL: Port $Port STILL not listening. Manual investigation needed." -ForegroundColor Red
            if ($chromeProcess2 -and !$chromeProcess2.HasExited) {
                Write-Host "  Chrome PID $($chromeProcess2.Id) is alive but port not open."
            } else {
                Write-Host "  Chrome exited immediately. Possible crash."
            }
        }
    } catch {
        Write-Host "  ERROR in fallback: $_" -ForegroundColor Red
    }
}

# ---------------------------------------------------------------------------
# FINAL REPORT
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
if ($portOpen) {
    Write-Host "  RESULT: Chrome debug port $Port is OPEN" -ForegroundColor Green
    Write-Host "  CDP endpoint: http://127.0.0.1:${Port}/json"
} else {
    Write-Host "  RESULT: FAILED to open port $Port" -ForegroundColor Red
    Write-Host "  Fallback: use Extension bridge (no --remote-debugging-port needed)"
}
Write-Host "============================================="

exit $(if ($portOpen) { 0 } else { 1 })
