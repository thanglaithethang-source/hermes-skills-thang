# Windows & Office License Check + KMS Reactivation

## Windows Activation Status

```bash
# Check license status, edition, channel, partial product key
cscript /nologo "C:/Windows/System32/slmgr.vbs" /dli

# Check if permanently activated or expiring
cscript /nologo "C:/Windows/System32/slmgr.vbs" /xpr

# Full license details
cscript /nologo "C:/Windows/System32/slmgr.vbs" /dlv
```

| Field | Meaning |
|-------|---------|
| `OEM_DM` channel | OEM Digital Marketplace — legitimate OEM license came with machine |
| `RETAIL` channel | Retail license (bought separately) |
| `VOLUME_KMSCLIENT` | Volume license via KMS (may be legitimate or crack) |
| `Licensed` | Activated OK |
| `Initial grace period` | Not yet activated — needs key or KMS |

## Office Activation Status

```bash
# Find OSPP.VBS (Office Software Protection Platform)
# Common locations:
#   C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS   (Office 2016 32-bit)
#   C:/Program Files/Microsoft Office/Office16/OSPP.VBS         (Office 2016 64-bit)
#   C:/Program Files/Microsoft Office/Office16/OSPP.VBS         (Office 2019/2021)

# Check all installed Office licenses
cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /dstatusall
```

### Interpreting Office License Output

| Signal | Meaning |
|--------|---------|
| `LICENSE STATUS: ---LICENSED---` | Activated OK |
| `LICENSE STATUS: ---UNLICENSED---` | Not activated |
| `REMAINING GRACE: N days` | KMS activation countdown — needs refresh |
| `ERROR CODE: 0xC004F014` | Product key not available (MAK key expired/blocked) |
| `KMS machine name: kms8.MSGuides.com:1688` | **Public KMS crack server** — non-legitimate activation |
| `VOLUME_KMSCLIENT` channel | Volume license — checked periodically against a KMS server |

## KMS Reactivation (for Office on KMS crack)

When `REMAINING GRACE` is low (e.g. 94 days), simply run:

```bash
cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /act
```

This contacts the configured KMS server and renews the license.

### Set / Change KMS Server (if needed)

```bash
cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /sethst:kms8.MSGuides.com
cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /setprt:1688
cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /act
```

### Install Product Key (if missing)

```bash
cscript /nologo "C:/Program Files (x86)/Microsoft Office/Office16/OSPP.VBS" /inpkey:XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
```

## Auto-Renewal Check

After activation, KMS auto-renews every ~90 days (configurable via `/setprt` interval on the KMS server side). The local schedule is visible in `REMAINING GRACE` field after `/dstatusall`.

## Pitfalls

- **MSYS/bash cannot run `slmgr.vbs` or `OSPP.VBS` directly** — always wrap in `cscript /nologo "C:/path/to/script.vbs"`. Do NOT use relative paths or `%windir%` env vars in MSYS (they won't expand).
- **OSPP.VBS path depends on bitness**: Office 2016 32-bit on 64-bit Windows → `C:\Program Files (x86)\Microsoft Office\Office16\`. Office 64-bit → `C:\Program Files\Microsoft Office\Office16\`. Check both.
- **KMS crack vs legitimate KMS**: Legitimate KMS = internal corporate server (e.g. `kms.company.com`). Public servers like `kms8.MSGuides.com` = cracked/pirated activation.
- **/act may fail silently** if KMS server is down. Run `/dstatusall` after to verify.
