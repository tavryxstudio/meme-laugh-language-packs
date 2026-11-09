# Packs

Each directory is one language. `ui.json` and `dialogue.json` are source files; release ZIPs are
built from them and never committed.

- `en/` — embedded in the game as the mandatory fallback.
- `ru/` — complete Russian pack.
- Add `packs/<code>/` for another language and register it in `catalog.json`.

Translation rules:

1. Do not machine-translate a whole language without review. A `partial` pack with an
   English fallback is better than a confidently wrong one.
2. Keep every `key` in `ui.json` identical to `packs/en/ui.json`. Extra keys are ignored;
   missing keys fall back to English.
3. Keep the dialogue format (`event`, `tone`, `speaker`, `text`, `weight`) unchanged,
   including `{situation}` and other placeholders.
4. Update `pack.json`, `licenses.json`, and the language entry in `catalog.json`.
