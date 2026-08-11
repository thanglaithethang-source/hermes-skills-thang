#!/usr/bin/env python3
"""
ChatGPT Reviewer — Gửi code/task cho ChatGPT review qua CDP.

Cách dùng:
  from chatgpt_review import ChatGPTReviewer

  reviewer = ChatGPTReviewer()
  result = reviewer.review("Review this code:\n\ndef foo(x):\n    return x/0")
  print(result)

Yêu cầu:
  - Chrome mở ChatGPT tab (đã login)
  - Bridge server đang chạy (hermes_bridge_server.py)
  - Hermes Bridge extension loaded

Flow:
  1. Tìm ChatGPT tab
  2. Type message vào #prompt-textarea (ProseMirror) qua execCommand
  3. Press Enter (KeyboardEvent dispatch)
  4. Poll DOM cho đến khi response ổn định
  5. Đọc response từ [data-message-author-role="assistant"]
"""
import json
import socket
import time
import uuid


# ============================================================
# Bridge TCP client — mở connection mới mỗi command
# ============================================================
def send_command(cmd):
    """Gửi command qua TCP bridge server, trả về dict."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect(('127.0.0.1', 19979))
    if 'requestId' not in cmd:
        cmd['requestId'] = str(uuid.uuid4())[:8]
    sock.sendall((json.dumps(cmd) + '\n').encode())
    data = b''
    while True:
        try:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            if b'\n' in data:
                break
        except socket.timeout:
            break
    sock.close()
    if data:
        try:
            return json.loads(data.decode().strip().split('\n')[-1])
        except:
            return {'error': 'JSON parse failed', 'raw': data.decode()[:500]}
    return {'error': 'No response'}


# ============================================================
# ChatGPT Reviewer
# ============================================================
class ChatGPTReviewer:
    """Gửi code/task cho ChatGPT review qua CDP."""

    def __init__(self):
        self.tab_id = None

    def _find_tab(self):
        """Tìm ChatGPT tab trong Chrome."""
        r = send_command({'type': 'list_tabs'})
        tabs = r.get('tabs', [])
        chatgpt_tabs = [t for t in tabs if 'chatgpt' in t.get('url', '').lower()]
        if chatgpt_tabs:
            self.tab_id = chatgpt_tabs[0]['id']
            return True
        return False

    def _type_message(self, message):
        """Type message vào ChatGPT ProseMirror editor."""
        escaped = json.dumps(message)
        js = """
        var el = document.querySelector('#prompt-textarea');
        if (el) {
            el.focus();
            el.innerHTML = '';
            document.execCommand('selectAll');
            document.execCommand('insertText', false, %s);
            'typed_ok';
        } else {
            'no_input_found';
        }
        """ % escaped
        r = send_command({'type': 'execute_js', 'tabId': self.tab_id, 'code': js})
        return r.get('result', {}).get('value', '')

    def _press_enter(self):
        """Press Enter để gửi message."""
        js = """
        var el = document.querySelector('#prompt-textarea');
        if (el) {
            el.focus();
            ['keydown','keypress','keyup'].forEach(function(n) {
                el.dispatchEvent(new KeyboardEvent(n, {
                    key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                    bubbles: true, cancelable: true
                }));
            });
            'enter_sent';
        } else {
            'no_input';
        }
        """
        r = send_command({'type': 'execute_js', 'tabId': self.tab_id, 'code': js})
        return r.get('result', {}).get('value', '')

    def _read_response(self, max_chars=8000):
        """Đọc response từ DOM — [data-message-author-role="assistant"]."""
        js = """
        var msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
        if (msgs.length === 0) {
            JSON.stringify({source: 'none', count: 0, text: ''});
        } else {
            var last = msgs[msgs.length - 1];
            JSON.stringify({source: 'assistant', count: msgs.length, text: last.textContent.substring(0, %d)});
        }
        """ % max_chars
        r = send_command({
            'type': 'cdp_command',
            'method': 'Runtime.evaluate',
            'params': {'expression': js, 'returnByValue': True},
            'tabId': self.tab_id
        })
        result = r.get('result', {})
        inner = result.get('result', {}) if isinstance(result, dict) else {}
        val = inner.get('value', '') if isinstance(inner, dict) else str(inner)
        try:
            data = json.loads(val)
            return data.get('text', '')
        except:
            return ''

    def _wait_for_response(self, timeout=60, poll_interval=3, stable_checks=3):
        """Poll DOM cho đến khi response ổn định."""
        start = time.time()
        last_text = ""
        stable_count = 0

        while time.time() - start < timeout:
            time.sleep(poll_interval)
            text = self._read_response()
            if text and text == last_text:
                stable_count += 1
                if stable_count >= stable_checks:
                    break
            else:
                stable_count = 0
            last_text = text
        return last_text

    def review(self, message, timeout=60):
        """
        Gửi code/task cho ChatGPT review, trả về response text.

        Args:
            message: str — code/task cần review
            timeout: int — seconds tối đa đợi response

        Returns:
            str — ChatGPT response text, hoặc error message
        """
        # Find ChatGPT tab
        if not self.tab_id:
            if not self._find_tab():
                return "ERROR: No ChatGPT tab found. Open ChatGPT in Chrome first."

        # Type message
        type_result = self._type_message(message)
        if type_result != 'typed_ok':
            return f"ERROR: Failed to type message: {type_result}"

        time.sleep(1)

        # Press Enter
        enter_result = self._press_enter()
        if enter_result != 'enter_sent':
            return f"ERROR: Failed to press Enter: {enter_result}"

        # Wait for response
        response = self._wait_for_response(timeout=timeout)

        if not response:
            return "ERROR: No response received within timeout."

        return response

    def new_chat(self):
        """Tạo conversation mới (click 'New chat' button)."""
        js = """
        var btn = document.querySelector('a[href="/"]') ||
                  document.querySelector('button[aria-label="New chat"]') ||
                  document.querySelector('[data-testid="new-chat-button"]');
        if (btn) {
            btn.click();
            'new_chat_clicked';
        } else {
            'no_new_chat_button';
        }
        """
        r = send_command({'type': 'execute_js', 'tabId': self.tab_id, 'code': js})
        result = r.get('result', {}).get('value', '')
        if result == 'new_chat_clicked':
            time.sleep(2)
        return result


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chatgpt_review.py 'Review this code: ...'")
        print("       python chatgpt_review.py --file code.py")
        sys.exit(1)

    if sys.argv[1] == '--file':
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            message = f.read()
        message = "Review this code for bugs, security issues, and improvements:\n\n" + message
    else:
        message = sys.argv[1]

    reviewer = ChatGPTReviewer()
    print(f"Sending to ChatGPT ({len(message)} chars)...")
    print(f"{'='*60}")
    result = reviewer.review(message)
    print(result)
    print(f"{'='*60}")
