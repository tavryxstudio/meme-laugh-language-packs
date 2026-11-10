# Meme Laugh — Language Packs

Public language-content repository for **Meme Laugh**. It hosts the UI strings and NPC
dialogue packs that the game downloads when a player picks a language.

The base game always ships with **English** built in. Nothing is required to play in English,
and the game works offline. Speech recognition is not part of this repository: the game uses a
single multilingual **Whisper small** model (~487 MB), which is installed separately in the
player's user folder by the game itself. Vosk remains only as an emergency fallback inside the
game and is never offered through this catalogue.

## Contents

```
catalog.json                  The catalogue the game reads
schema/catalog.schema.json    JSON Schema for catalog.json
schema/dialogue.schema.json   JSON Schema for packs/<code>/dialogue.json
packs/en/                     English source pack (also embedded in the game)
packs/ru/                     Russian source pack
  ui.json                     UI strings: { formatVersion, language, strings[] }
  dialogue.json               NPC dialogue: 278 lines, 21 event groups
  pack.json                   Human-readable pack metadata
  licenses.json               Licence information for every component
tools/validate_catalog.py     Schema + consistency checks (CI)
tools/build_release.py        Builds versioned ZIPs, hashes, and updates catalog.json
.github/workflows/            validate.yml and release.yml
```

Only release ZIPs are large files. They are **never committed**: the release workflow attaches
them to GitHub Releases and `catalog.json` references them by URL + SHA-256 + size. No speech
models (Whisper or Vosk) are stored or downloaded through this repository.

## Catalogue format

`catalog.json` uses `schemaVersion: 1`. Every language has:

```json
{
  "code": "ru",
  "name": "Русский",
  "status": "complete | partial | missing",
  "builtIn": false,
  "components": [ ... ]
}
```

Every component has `id`, `kind`, `language`, `version`, `url`, `sha256`, `sizeBytes`,
`minGameVersion`, `license`, `licenseUrl`, `dependencies`, `installSubfolder`, and optionally
`builtIn` / `optional`.

Supported component kinds:

| kind       | Purpose               |
|------------|-----------------------|
| `ui`       | Interface strings     |
| `dialogue` | NPC dialogue lines    |

Supported language codes follow `Loc.Languages` in the game:

`en, ru, uk, de, fr, es, it, pt, pl, tr, cs, nl`.

Only English and Russian are complete today. Other languages are listed with
`"status": "missing"` and no components; adding one does **not** require a game update.
When a language pack is missing, the game falls back to English.

## Dialogue format

`dialogue.json` is a versioned, self-contained pack:

```json
{
  "code": "ru",
  "name": "Русский",
  "formatVersion": 1,
  "strings": [ { "key": "...", "value": "..." } ],
  "names": [ { "id": "vasya", "name": "Вася", "title": "..." } ],
  "lines": [
    { "event": "round_start", "tone": "sarcastic", "text": "...", "weight": 1 },
    { "event": "joke", "tone": "absurd", "speaker": "gosha", "text": "...", "mature": true }
  ]
}
```

Line fields:

| field     | required | meaning |
|-----------|----------|---------|
| `event`   | yes      | Event group key, for example `round_start`, `win`, `banter` |
| `text`    | yes      | The spoken line; keep placeholders such as `{situation}` |
| `tone`    | no       | Personality tone filter (`sarcastic`, `dry`, `kind`, ...) |
| `speaker` | no       | Restrict the line to one NPC profile id |
| `weight`  | no       | Positive selection weight, default `1` |
| `mature`  | no       | Adult-only line; see below |

`mature: true` marks strong language. The game shows such lines only when
**Settings → NPC → Profanity** is enabled. Older game versions ignore the field entirely and
may display the line. Omit `mature` for normal lines.

English and Russian must keep the same event groups and line counts. The validator enforces
278 lines and 21 event groups for both, and checks that the event sets match.

## Publishing a new pack version

1. Edit the files under `packs/<code>/`.
2. Run validation locally:

   ```bash
   python tools/validate_catalog.py
   ```

3. Commit and push to `main`.
4. Tag the release with a new `lang-vX.Y.Z` tag. Never reuse an existing tag: players already
   have the old hashes.

   ```bash
   git tag lang-v2026.11.2
   git push origin lang-v2026.11.2
   ```

`.github/workflows/release.yml` then:

- builds one ZIP per component (`<code>-<kind>-v<version>.zip`);
- computes SHA-256 and size;
- uploads the ZIPs to the GitHub Release;
- rewrites `catalog.json` with the new release URLs and hashes;
- commits the updated `catalog.json` back to `main`.

Players receive updated components on the next launch: the game compares versions and
re-downloads only changed components. Existing user settings are never touched.

## Adding a new language

1. Copy `packs/en/` to `packs/<code>/` and translate `ui.json` and `dialogue.json`.
   Do **not** machine-translate without review; a partial pack is better than a wrong one.
2. Update `pack.json` and `licenses.json`.
3. Add (or update) the language entry in `catalog.json`:

   ```json
   {
     "code": "de",
     "name": "Deutsch",
     "status": "partial",
     "builtIn": false,
     "components": [
       { "id": "de.ui", "kind": "ui", "language": "de", "version": 1, ... },
       { "id": "de.dialogue", "kind": "dialogue", "language": "de", "version": 1, ... }
     ]
   }
   ```

   `url`, `sha256` and `sizeBytes` are filled automatically by `tools/build_release.py` during
   the release workflow. For local testing, run it manually (see below).
4. Tag a release. No game build is needed for the new language.

If only the UI is translated, set `"status": "partial"` and omit the dialogue component; the
untouched parts fall back to English.

## Local release build

```bash
python tools/build_release.py --tag lang-v2026.11.2 \
  --repo tavryxstudio/meme-laugh-language-packs
```

The script writes ZIPs to `dist/` and updates `catalog.json` in place. Upload `dist/*` to the
GitHub Release manually if you are not using the workflow. The builder normalizes line endings
and ZIP metadata, so hashes are identical on Windows and Linux.

## How the game consumes this repository

The game reads `catalog.json` through an `ILanguageContentSource`. The default source is HTTP
(GitHub Releases / raw.githubusercontent.com), configured in
`StreamingAssets/LanguagePacks/source.json`. Alternative implementations exist for local
folders and Steam depots, so the source can be replaced without touching game logic.

Installed files live in:

```
%USERPROFILE%\AppData\LocalLow\Meme & Co.\Meme Laugh\LanguagePacks\
  <language>/ui/...
  <language>/dialogue/...
  installed.json
```

Speech models are stored separately and are not managed by the language catalogue.

## Publishing options

### 1. GitHub Releases (development and standalone builds)

- Simple, free, works for public builds.
- **No SLA.** GitHub Releases can be slow or unavailable in some regions.
- Not recommended as the only distribution channel for a commercial Steam release.
- `catalog.json` currently points at the
  [tavryxstudio/meme-laugh-language-packs](https://github.com/tavryxstudio/meme-laugh-language-packs)
  release assets; the release workflow rewrites the URLs and hashes on every tag.

### 2. Steam depots / free DLC / own CDN (recommended for Steam)

- Put language packs into optional free DLC or a depot. Steam handles delivery, updates,
  retries, regions and integrity checks.
- Set the game's content source to `steam` (or a custom `local` root) in
  `StreamingAssets/LanguagePacks/source.json`. Installed depot files are detected without
  downloading anything.
- The base English content stays embedded in the build, so a missing depot never prevents
  play.
- A custom CDN with signed URLs and a stable SLA is also supported by the same HTTP source;
  only `catalogUrl` changes.

The game never hard-codes a GitHub URL in a gameplay class, so switching sources later is a
configuration change, not a rewrite.

## Licences

The language packs in this repository are released under **CC0-1.0** unless a file states
otherwise. See `packs/<code>/licenses.json` and `LICENSE`.
