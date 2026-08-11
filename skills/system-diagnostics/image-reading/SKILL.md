---
name: image-reading
description: "Read text from images (JPG/PNG/screenshots) when native vision is unavailable. Vision tool chain, Tesseract OCR fallback, and the absolute rule: never fabricate image content."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [Vision, OCR, Tesseract, Image, Screenshot, Text-Extraction]
    related_skills: [ocr-and-documents, computer-use]
---

# Image Reading — Vision Fallback Chain

When the user asks you to "read" or "describe" an image file (JPG, PNG, screenshot), follow this chain. **Never skip to fabrication.**

## Tool Chain (try in order)

### 1. vision_analyze (first choice)
```
vision_analyze(image_url="C:\\path\\to\\image.jpg", question="Read all text and describe content")
```
- Works ONLY if the active model has native vision support.
- **glm-5.2 does NOT have native vision** — this will always return "no image attached" on this model.
- If it fails, proceed to step 2. Do NOT present the failure as a result.

### 2. browser_vision (second choice — UNRELIABLE)
```
browser_navigate(url="file:///C:/path/to/image.jpg")
browser_vision(question="Read all text and describe content")
```
- May return a description, but on non-vision models it **HALLUCINATES** — fabricates plausible-sounding content without actually reading the image.
- **WARNING SIGNS of hallucination**: generic layout descriptions, "no image attached" preamble, overly detailed but unverifiable claims, content that sounds like a template.
- If you suspect hallucination, **discard the output** and proceed to step 3.
- **NEVER present browser_vision output as fact without verification** when the model lacks native vision.

### 3. Tesseract OCR (reliable fallback for text extraction)
```python
from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

img = Image.open(r'C:\path\to\image.jpg')
text = pytesseract.image_to_string(img, lang='eng')
print(text)
```

**Windows setup:**
- Tesseract v5.5.0 at `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Language packs: `eng`, `osd` only by default (no `vie`)
- `pip install pytesseract Pillow`
- For Vietnamese: download `vie.traineddata` into `C:\Program Files\Tesseract-OCR\tessdata\` and use `lang='vie+eng'`

**Limitations:**
- Extracts TEXT only — cannot describe images, diagrams, colors, layout
- Quality depends on image resolution and text clarity
- Mixed Vietnamese/English without `vie` pack: Vietnamese words will be garbled but English and numbers will be readable

### 4. Honest failure (final fallback)
If all above fail or the image is non-text (photos, diagrams):
- Tell the user: "em không đọc được ảnh này"
- **DO NOT** fabricate a description
- **DO NOT** present hallucinated content as fact
- Suggest the user describe what they need from the image

## THE ABSOLUTE RULE

**Never fabricate image content.** If you cannot read an image with a tool, say so. Presenting a plausible-sounding but invented description as if you read it is the worst failure mode — it destroys trust instantly. The user WILL catch it.

## When to use this skill

- User says "đọc đi" / "read this" / "what's in this image" with an image path
- User attaches an image and asks about its content
- You need to extract text from a screenshot, photo, or scanned image
- vision_analyze or browser_vision returns suspicious results on a non-vision model

## References

- `references/vision-tool-failures.md` — documented failure modes and hallucination patterns from real sessions
