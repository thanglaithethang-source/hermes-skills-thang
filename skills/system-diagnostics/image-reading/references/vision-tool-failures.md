# Vision Tool Failure Modes — Documented from Real Sessions

## Session 2026-07-26: glm-5.2 + image reading

### Setup
- Model: glm-5.2 (custom provider, api.ai-box.vn)
- Image: JPG screenshot (904x1044, 118KB)
- User asked: "đọc đi" (read it)

### Failure 1: vision_analyze
```
vision_analyze(image_url="C:\\Users\\thang\\Downloads\\Whisk Downloads\\57f2315438d8b986e0c9.jpg", question="...")
→ success: true, analysis: "Rất tiếc, hiện tại tôi không nhận được bất kỳ hình ảnh nào..."
```
**Root cause**: glm-5.2 has no native vision capability. The tool returns a generic "no image" message.

### Failure 2: browser_vision (HALLUCINATION — most dangerous)
```
browser_navigate(url="file:///C:/Users/thang/Downloads/Whisk Downloads/view.html")
browser_vision(question="...")
→ success: true, analysis: [detailed, plausible description of Google weather search for "thời tiết cần thơ"]
```
**Root cause**: browser_vision on a non-vision model routes to an auxiliary vision model that **fabricated** a complete, plausible-sounding description. The description included specific temperatures (34°C), humidity (54%), wind speed (10 km/h), search results, URLs — all invented.

**Why it's dangerous**: The output is structured, detailed, and sounds authoritative. A less careful agent would present it as fact. The user asked "đọc đi" and the fabricated output looked like a real reading.

**Detection signals**:
- The output was preceded by "Xin chào! Rất tiếc, hiện tại tôi không nhận được hình ảnh nào" — a preamble that the auxiliary model couldn't actually see the image
- The description was overly generic and template-like
- Content matched what a "typical" screenshot might contain, not what was actually there

### Failure 3: computer_use capture (vision mode)
```
computer_use(action='capture', mode='vision')
→ vision_analysis: "I am unable to see the actual screenshot image..."
```
**Root cause**: Same as above — auxiliary vision model cannot actually see the captured screen on a non-vision model.

### Success: Tesseract OCR
```python
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
img = Image.open(r'C:\Users\thang\Downloads\Whisk Downloads\57f2315438d8b986e0c9.jpg')
text = pytesseract.image_to_string(img, lang='eng')
```
**Result**: Successfully extracted text. Output was garbled for Vietnamese (no `vie` traineddata installed) but readable for English and numbers. Actual content was a guide about upgrading Claude Pro Max using SEPA Direct Debit — completely different from the hallucinated weather widget.

### Key Lesson
The hallucinated browser_vision output (weather widget, 34°C, Cần Thơ) had **zero overlap** with the actual image content (Claude Pro Max upgrade guide). This proves the output was entirely fabricated, not a misreading. **Never trust browser_vision output on non-vision models.**

### Verified Fix
Tesseract OCR path: `C:\Program Files\Tesseract-OCR\tesseract.exe` (v5.5.0, eng+osd only).
Install pytesseract: `pip install pytesseract Pillow`
Set path: `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`
