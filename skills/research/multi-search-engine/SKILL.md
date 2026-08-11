---
name: multi-search-engine
description: "Tìm kiếm đa nguồn — 16 search engines, zero API key. Google, GitHub, Reddit, arXiv, StackOverflow, Wikipedia, WolframAlpha và nhiều nguồn khác. Dùng khi cần research nhanh, verify claims, hoặc tìm documentation. Source: CocoLoop Multi Search Engine (132k stars)."
version: 1.0.0
---

# Multi Search Engine

## Activation
Khi: research thông tin mới, verify claims, tìm documentation, so sánh công nghệ, tìm solution cho vấn đề kỹ thuật, cross-reference nhiều nguồn.

## Not for
- Đọc nội dung trang đã biết URL (dùng `browser_navigate` trực tiếp)
- Gọi API có sẵn (dùng `terminal curl` thẳng)
- Tìm trong codebase local (dùng `search_files`)
- Tìm session cũ (dùng `session_search`)

## Chiến lược tìm kiếm

| Loại câu hỏi | Nguồn chính | Nguồn phụ |
|---|---|---|
| Code/Technical | GitHub, StackOverflow | Reddit, Dev.to |
| Research/Academic | arXiv, Google Scholar | Wikipedia |
| Documentation | Official docs, MDN | Google |
| News/Current | Google News, Reddit | X/Twitter |
| Data/Facts | Wikipedia, WolframAlpha | Google |

## Cách thực hiện

1. Xác định loại câu hỏi → chọn 2-3 nguồn
2. Tìm kiếm song song:
   - `browser_navigate` tới search engine (DuckDuckGo ưu tiên vì ít block)
   - `terminal curl` cho API (GitHub: `api.github.com/search`, arXiv: `export.arxiv.org/api`)
3. `browser_snapshot` → parse kết quả
4. `browser_navigate` vào trang tốt nhất → `browser_snapshot` lấy nội dung
5. Cross-reference: ít nhất 2 nguồn đồng thuận mới kết luận
6. Đánh dấu: `VERIFIED` (2+ nguồn) / `LIKELY` (1 nguồn uy tín) / `UNVERIFIED` (speculation)
7. Luôn kèm URL nguồn trong câu trả lời

## Key Pitfalls

1. **Google/Bing block bot traffic**: Luôn thử DuckDuckGo trước. Nếu bị block, dùng `terminal curl` với API endpoints.

2. **SPA không render trong snapshot**: Trang React/Vue/Angular có thể trả về empty snapshot. Fallback: `browser_vision` để xem screenshot, hoặc tìm API của trang đó.

3. **Thông tin quá hạn**: Luôn check date. Thông tin >1 năm → phải verify lại từ nguồn khác.

4. **1 nguồn không đủ kết luận**: Tuyệt đối không dùng 1 nguồn duy nhất (kể cả official docs cũng có thể lỗi thời).

5. **Đừng research quá sâu**: Nếu sau 3 lượt search không tìm thấy → báo Sếp "không tìm thấy" + danh sách nguồn đã thử.

## Completion Criteria
- Câu trả lời có ≥2 nguồn cross-reference (verify: đếm số URL trong response)
- Mỗi claim được đánh dấu VERIFIED/LIKELY/UNVERIFIED (verify: grep 3 từ này trong response)
- URL nguồn kèm theo (verify: response chứa "http")
- Ngày tháng của thông tin được ghi nhận (verify: có đề cập năm/tháng trong kết luận)
