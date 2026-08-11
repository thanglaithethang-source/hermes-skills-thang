# PowerShell 5.1 Encoding Fix

## Problem

PowerShell 5.1 (Desktop edition, default on Windows 10/11) uses ANSI/Windows-1252
encoding by default. When a `.ps1` script is saved as UTF-8 and contains Unicode
special characters, PS 5.1 mis-parses them.

### Symptoms

| Character | Unicode | PS 5.1 error |
|---|---|---|
| Em dash `—` | U+2014 | `Unexpected token` in string |
| En dash `–` | U+2013 | `Unexpected token` |
| Smart quotes `'` `'` | U+2018/2019 | String terminator errors |
| BOM `\ufeff` | U+FEFF | First token corrupted (`?param` instead of `param`) |

### Why BOM breaks `param`

PS 5.1 reads the BOM (3 bytes: EF BB BF) as part of the first token:
```
param([string]$Root = "...")  →  \ufeffparam([string]$Root = "...")
```
Result: `?param : The term '?param' is not recognized...`

## Fix: Batch Convert All PS1 Scripts to ASCII

```bash
python -c "
import glob
scripts = glob.glob('D:/path/to/scripts/*.ps1')
for f in scripts:
    # Read with BOM stripping (utf-8-sig)
    with open(f, 'r', encoding='utf-8-sig') as fh:
        text = fh.read()
    # Replace Unicode special chars with ASCII equivalents
    text = text.replace('\u2014', '--')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2018', \"'\")
    text = text.replace('\u2019', \"'\")
    text = text.replace('\u201c', '\"')
    text = text.replace('\u201d', '\"')
    # Strip any remaining BOM
    text = text.lstrip('\ufeff')
    # Save as UTF-8 WITHOUT BOM, CRLF line endings
    with open(f, 'w', encoding='utf-8', newline='\r\n') as fh:
        fh.write(text)
"
```

## Verify

```bash
python -c "
with open('D:/path/to/script.ps1', 'r', encoding='utf-8') as f:
    text = f.read()
non_ascii = sum(1 for c in text if ord(c) > 127)
print(f'non-ASCII chars: {non_ascii}')  # must be 0
"
```

## Prevention

When writing PS1 scripts for Windows:
- Use only ASCII characters (em dash → `--`, en dash → `-`, smart quotes → straight quotes)
- Save as UTF-8 WITHOUT BOM
- Use CRLF line endings (`\r\n`)
- If non-ASCII is unavoidable, use `pwsh` (PowerShell Core 7+) which defaults to UTF-8
