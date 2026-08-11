# Bitmap Font Regeneration for Clausewitz Engine Games

HOI4, EU4, CK2, CK3, Stellaris — all use BMFont format (.fnt + .dds) bitmap fonts.
When localizing to Vietnamese, the original fonts lack proper Vietnamese glyph support.

## Diagnosis Pattern

1. **Read .fnt file** — BMFont text format. Check `info face="..."` for original font face.
2. **Check char IDs** — grep `char id=NNN` for Vietnamese char codes:
   - 272=Đ, 273=đ, 258=Ă, 259=ă, 226=â, 234=ê, 244=ô
   - 416=Ơ, 417=ơ, 431=Ư, 432=ư
   - 7841-7929: precomposed diacritics (ạ, ả, ầ, ấ, ế, ệ, ố, ờ, ự, etc.)
3. **Check texture** — .dds is uncompressed BGRA32 (R=0xff0000, G=0xff00, B=0xff, A=0xff000000).
   RGB channels are white (255), alpha channel contains the glyph.
4. **Common failure mode**: Vietnamese chars ARE in .fnt but glyphs are **shrunk** to fit
   bounding box → text appears tiny compared to ASCII. Root cause: original font face
   (e.g. "Ubuntu Light") not available on Windows, previous modder used wrong tool or
   wrong settings, causing auto-scale-down.

## Regeneration Steps

### 1. Map original font faces to available Windows TTFs

| Original face | Windows replacement | Bold? |
|---|---|---|
| Ubuntu Light | arial.ttf | No |
| Ubuntu | arialbd.ttf | Yes |
| Orator Std | arialbd.ttf | Yes |
| Adobe Garamond Pro | timesbd.ttf | Yes |
| Garamond Premr Pro | times.ttf | No |
| Century Gothic | calibri.ttf | No |
| Times New Roman | times.ttf | No |
| Tahoma | tahomabd.ttf | Yes |

Verify TTF has Vietnamese chars: `from fontTools.ttLib import TTFont; cmap = font.getBestCmap(); 417 in cmap`

### 2. Character set

Include these Unicode ranges:
- 0, 8, 9, 10, 13, 29 (control chars used by engine)
- 32-126 (ASCII printable)
- 160-255 (Latin-1 Supplement)
- 0x100-0x17F (Latin Extended-A)
- 0x180-0x24F (Latin Extended-B — contains Ơ, ơ, Ư, ư)
- 0x1E00-0x1EFF (Latin Extended Additional — Vietnamese diacritics)

Total: ~789 chars, ~592 Vietnamese-specific.

### 3. Render + Pack

- Use `Pillow.ImageFont.truetype(ttf_path, size)` to render each char to grayscale (L mode)
- Get bounding box via `font.getbbox(char)`, advance via `font.getlength(char)`
- Shelf-based packing: sort by height desc, place left-to-right, wrap to next shelf
- Start with 256x256, increase to 256x512, 512x512, 512x1024, 1024x1024 until all fit
- Padding=1 between glyphs to prevent texture bleeding

### 4. Write .dds (uncompressed BGRA32)

```
Header (128 bytes):
  magic: b'DDS '
  dwSize: 124
  dwFlags: 0x1007 (CAPS|HEIGHT|WIDTH|PIXELFORMAT|LINEARSIZE)
  dwHeight, dwWidth
  dwPitchOrLinearSize: width * height * 4
  pfSize: 32
  pfFlags: 0x41 (DDPF_RGB | DDPF_ALPHAPIXELS)
  pfBitCount: 32
  R mask: 0x00ff0000, G: 0x0000ff00, B: 0x000000ff, A: 0xff000000
  dwCaps: 0x1000 (DDSCAPS_TEXTURE)

Pixel data: BGRA per pixel, bottom-to-top row order (Pillow handles this)
```

### 5. Write .fnt (BMFont text format)

```
info face="Arial" size=18 bold=1 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 padding=1,1,1,1 spacing=1,1 outline=0
common lineHeight=18 base=14 scaleW=512 scaleH=512 pages=1 packed=0 alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0
page id=0 file="hoi_18.dds"
chars count=789
char id=65   x=0   y=0   width=14   height=13   xoffset=0   yoffset=0   xadvance=12   page=0  chnl=15
...
```

**Critical**: page file must match actual .dds filename (e.g. `hoi_18.dds`, NOT `hoi_18_0.dds`).

### 6. Fonts to regenerate

Main UI fonts (skip _cryllic, _inverted, arrow, map fonts):
hoi_18, hoi_18mbs, hoi_20b, hoi_16mbs, hoi_18b, hoi_20bs, hoi_26mbs,
hoi_24header, hoi_30header, hoi_36header, hoi_33,
standard, standard_18, standard_22,
Arial12, garamond_12, garamond_14, garamond_16,
hoi_16tooltip3, hoi_16typewriter, hoi_22typewriter,
hoi_22tech, newsfeed_body, newsfeed_title,
tahoma_20_bold, hoi4_typewriter16, hoi4_typewriter22

## Verification

1. Check .fnt page ref matches .dds filename
2. Check all Vietnamese char IDs present in .fnt
3. Extract glyphs from .dds at .fnt coordinates, check non-zero alpha
4. Compare glyph sizes: Vietnamese chars should be similar size to ASCII (not tiny)
5. Vision analysis: render comparison sheet, verify glyphs are legible and not cut off

## Pitfalls

- **430 is Ʈ (T with retroflex hook), NOT Ư** — Ư is 431. Don't confuse when checking "missing" chars.
- **Latin Extended-B (0x180-0x24F) contains Ơ/ơ/Ư/ư** — not Latin Extended-A. Must include this range.
- **Page reference mismatch**: BMFont exports with `_0` suffix (e.g. `hoi_18_0.dds`) but Clausewitz engine expects filename matching .fnt basename (e.g. `hoi_18.dds`). Always fix page ref.
- **Texture too small**: 256x256 was original size, insufficient for 789 chars. Increase to 512x512 minimum.
- **Font face not on Windows**: "Ubuntu Light", "Orator Std", "Adobe Garamond Pro" — map to closest Windows equivalent.
- **Always backup before regenerating**: copy all .fnt + .dds to `_backup_before_regen/` first.
