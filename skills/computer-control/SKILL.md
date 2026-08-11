---
name: computer-control
description: Desktop automation — app control, GUI navigation, input, screen reading.
version: 1.1.0
---

# Computer Control

## Activation
When task involves: desktop interaction, app opening, GUI navigation, text input, screen state reading, mouse/keyboard automation.

## Not for
Tasks solvable via API, CLI, or script.

## Prerequisites
- cua-driver installed and running
- Target app identified
- Safe, reversible actions only

## Workflow
1. Identify target application
2. **Safe observation first:** capture with `action='capture', mode='ax'` to read state without taking any action. Use `app='Chrome'` (or specific app name) to limit scope.
3. For visual identification: capture with `mode='som'` to get numbered element overlays + AX tree.
4. Identify target element by SOM index (1-based) — strongly preferred over raw coordinates.
5. Verify API/CLI alternative not available
6. Execute action (click by `element=<index>`, type by `text=`, key by `keys=`, scroll)
7. Use `capture_after=true` to get follow-up screenshot in one round-trip
8. If wrong state: restore before continuing
9. Deliver with screenshot/state evidence

## Priority Tools
computer_use (preferred), vision (fallback)

## Capture Modes
| Mode | When | Returns |
|------|------|---------|
| `ax` | Safe observation, no side effects | Accessibility tree with element indices, labels, bounds |
| `som` | Visual identification needed | Screenshot with numbered overlays + AX tree |
| `vision` | Plain screenshot needed | Screenshot only, no element data |

## Completion Criteria
- Action verified by screenshot or state capture
- App state matches expected
- Errors documented

## Common Failures
- Clicking wrong element via coordinates → use SOM element index
- App not in focus → capture target app specifically (`app='Chrome'`)
- Typing into wrong field → verify focus before typing

## Pitfalls
- **Negative/virtual coordinates:** AX elements may have negative bounds (e.g. `(-32163, -31999, 57, 49)`). These are normal for virtual desktop coordinates. Always click by `element` index, never infer coordinates from bounds.
- **App scope:** Capture the target app instead of whole screen — less noisy, fewer elements to parse.

## Recovery
- If click misses: re-capture, identify correct element, retry
- If app state wrong: undo/revert, then re-plan
