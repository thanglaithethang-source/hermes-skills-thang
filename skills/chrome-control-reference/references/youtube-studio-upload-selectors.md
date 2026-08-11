# YouTube Studio Upload Selectors — Verified 2026-07-25

Test thực tế trên Chrome của Sếp (channel: UCH8HIGC4PebEFbo98LoX8Eg).

## Upload Flow

1. Navigate to `https://studio.youtube.com/channel/{CHANNEL_ID}/videos/upload`
2. Click upload button → file input appears
3. Set file via CDP DOM.setFileInputFiles
4. Wait for 2 contenteditable textboxes (title + description)
5. Fill title (first textbox) + description (second textbox)
6. Select "Not made for kids" radio
7. Click "Tiếp" (Next) through 4 wizard steps: Details → Video elements → Checks → Visibility
8. At Visibility step: select "Công khai" (Public)
9. Click final publish button

## Verified Selectors

| Element | Selector | Notes |
|---------|----------|-------|
| Upload button | `ytcp-button#upload-button button` | Text: "Tải video lên" (Vietnamese) |
| File input | `input[name="Filedata"]` | Inside `ytcp-uploads-file-picker`, hidden (display:none) |
| Title textbox | `#textbox[contenteditable="true"]` (first) | ariaLabel: "Thêm tiêu đề để mô tả video của bạn" |
| Description textbox | `#textbox[contenteditable="true"]` (second) | ariaLabel: "Giới thiệu về video của bạn cho người xem" |
| Not-made-for-kids | `tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]` | Click to select |
| Age restriction (none) | `tp-yt-paper-radio-button[name="VIDEO_AGE_RESTRICTION_NONE"]` | Default selected |
| AI content (no) | `tp-yt-paper-radio-button[name="VIDEO_HAS_ALTERED_CONTENT_NO"]` | Click if needed |
| Next button | `button` with text "Tiếp" | 4 steps, click 4 times |
| Channel ID | UCH8HIGC4PebEFbo98LoX8Eg | Sếp's channel |
| Video ID | URL param `udvid=xxx` | After upload, in URL |

## Key Technical Details

### File Input is Hidden
`input[name="Filedata"]` has `display: none` — không thể click. Phải dùng CDP `DOM.setFileInputFiles`:
```python
r = cdp(tab_id, 'DOM.getDocument')
root = r.get('root', {}).get('nodeId', 0)
r = cdp(tab_id, 'DOM.querySelector', {'nodeId': root, 'selector': 'input[name="Filedata"]'})
file_node = r.get('nodeId', 0)
cdp(tab_id, 'DOM.setFileInputFiles', {'nodeId': file_node, 'files': ['C:/path/to/video.mp4']})
```

### Upload Button is Custom Element
`ytcp-button#upload-button` is a Polymer custom element. The actual `<button>` is inside it:
```javascript
document.querySelector('ytcp-button#upload-button button').click();
```

### ContentEditable — Use execCommand
YouTube Studio uses contenteditable divs (not textarea/input). Use `document.execCommand('insertText')`:
```javascript
var box = document.querySelectorAll('#textbox[contenteditable="true"]')[0];
box.focus();
document.execCommand('selectAll');
document.execCommand('insertText', false, "Title text");
```

### IIFE Wrapper Required
`Runtime.evaluate` does NOT support `return` at top level. Must wrap in IIFE:
```javascript
// WRONG
var btn = document.querySelector('button');
if (btn) { btn.click(); return 'clicked'; }

// CORRECT
(function(){
    var btn = document.querySelector('button');
    if (btn) { btn.click(); return 'clicked'; }
    return 'not found';
})()
```

### Windows Path — Forward Slash
CDP `DOM.setFileInputFiles` requires forward slash paths:
```python
file_path = video_path.replace('\\', '/')  # C:\Users\... → C:/Users/...
```

### Upload Progress Bar
Progress bar (`tp-yt-paper-progress`) may stay at 0 for small files. Don't wait for 100% — instead wait for textboxes to appear:
```python
wait_for(tab_id, 'document.querySelectorAll("#textbox[contenteditable=true]").length >= 2', timeout=60)
```

### Draft State
After upload, video is saved as draft. To publish:
1. Click "Chỉnh sửa bản nháp" (Edit draft) on the content page
2. Navigate through wizard steps to Visibility
3. Select "Công khai" (Public)
4. Click publish button

### Debugger Detach After 3+ Clicks
Chrome Manifest V3 service worker dies after ~30s. Multi-step wizard (4+ clicks) may fail. Workaround: use `browser_navigate` + `browser_snapshot` + `browser_click` (Hermes built-in) for multi-step flows.
