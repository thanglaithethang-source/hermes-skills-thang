# V4 Build Audit Extension

Additional checks beyond the 10 standard criteria when working with V4 blueprints.

## V4-Specific Checks

11. **Motion budget compliance** — artificial motion ratio ≤45% global; per-beat caps (B22-B23 ≤20%, B32 ≤5%, B35-B36 ≤20%)
12. **No artificial-motion runs >2** — never more than 2 consecutive artificial-motion shots
13. **No primitive repeat >2** — same non-STATIC primitive not on 3 consecutive shots
14. **Word anchor resolution** — 60/60 anchors resolved with confidence ≥0.86; ±2 frame accuracy on punchlines
15. **Asset registry locked** — every music/SFX asset has sha256, license, source_url, file_path pointing to existing file
16. **One motion per shot** — every shot has exactly one motion_primitive (including STATIC_HOLD)
17. **Slug validation** — no guessed/placeholder slug; every filter/effect slug verified against registry or native calibration
18. **Shot map coverage** — all 36 story beats mapped to real shot IDs
19. **Cultural safety** — no generic headdress/tipi/fantasy shaman/invented ritual without verified source
20. **Silence gaps** — after "Bro. That is not science", "Trust me, bro", "My period product? Sheep", final line
21. **Audio standards** — voice 12-21dB above music, integrated -14 LUFS, true peak ≤ -1 dBTP
22. **Text callout cap** — exactly 34 events, no 35th added; max 2 lines, 5% safe area
