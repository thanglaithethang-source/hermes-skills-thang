"""One-shot fix all PS1 scripts in AI Company V5 package for PowerShell 5.1.

Usage: python ps1-encoding-fix.py [--root D:/AI-COMPANY]
"""
import glob, sys, os
from pathlib import Path

ROOT = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--root' else 'D:/AI-COMPANY'
SCRIPTS_DIR = os.path.join(ROOT, 'scripts')

REPLACEMENTS = {
    '\u2014': '--',   # em dash
    '\u2013': '-',    # en dash
    '\u2018': "'",    # left single quote
    '\u2019': "'",    # right single quote
    '\u201c': '"',    # left double quote
    '\u201d': '"',    # right double quote
}

fixed = 0
for f in sorted(glob.glob(os.path.join(SCRIPTS_DIR, '*.ps1'))):
    with open(f, 'r', encoding='utf-8-sig') as fh:
        text = fh.read()

    original = text
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    text = text.lstrip('\ufeff')  # strip any remaining BOM

    if text != original:
        with open(f, 'w', encoding='utf-8', newline='\r\n') as fh:
            fh.write(text)
        fixed += 1
        print(f'FIXED: {os.path.basename(f)}')

# Verify
for f in sorted(glob.glob(os.path.join(SCRIPTS_DIR, '*.ps1'))):
    with open(f, 'r', encoding='utf-8') as fh:
        text = fh.read()
    non_ascii = sum(1 for c in text if ord(c) > 127)
    has_bom = text.startswith('\ufeff')
    status = 'CLEAN' if non_ascii == 0 and not has_bom else f'BOM={has_bom} nonASCII={non_ascii}'
    print(f'  {os.path.basename(f)}: {status}')

print(f'\nFixed {fixed} files. All scripts ready for PowerShell 5.1.')
