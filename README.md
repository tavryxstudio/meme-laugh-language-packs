# Meme Laugh — Language Packs

Public language-content repository for **Meme Laugh**. It hosts the UI strings, NPC dialogue
packs, and (optionally) Vosk speech-recognition models that the game downloads when a player
picks a language.

The base game always ships with **English** built in. Nothing is required to play in English,
and the game works offline.

## Contents

```
catalog.json                 The catalogue the game reads
schema/catalog.schema.json   JSON Schema for catalog.json
packs/en/                    English source pack (also embedded in the game)
packs/ru/                    Russian source pack
  ui.json                    UI strings: { formatVersion, language, strings[] }
  dialogue.json              NPC dialogue, unchanged from StreamingAssets/Npc/Lang
  pack.json                  Human-readable pack metadata
  licenses.json              Licence information for every component
tools/validate_catalog.py    Schema + consistency checks (CI)
tools/build_release.py       Builds versioned ZIPs, hashes, and updates catalog.json
.github/workflows/           validate.yml and release.yml
```

Large files (release ZIPs, Vosk models) are **never committed**. They are attached to GitHub
Releases and referenced from `catalog.json` by URL + SHA-256 + size.

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

| kind            | Purpose                                            |
|-----------------|----------------------------------------------------|
| `ui`            | Interface strings                                  |
| `dialogue`      | NPC dialogue lines                                 |
| `stt-model`     | Vosk recognition model for one language            |
| `stt-runtime`   | Shared Vosk native runtime (one per platform)      |
| `tts-voice`     | Reserved for a future TTS provider                 |

Supported language codes follow `Loc.Languages` in the game:

`en, ru, uk, de, fr, es, it, pt, pl, tr, cs, nl`.

Only English and Russian are complete today. Other languages are listed with
`"status": "missing"` and no components; adding one does **not** require a game update.
When a language pack is missing, the game falls back to English.

## Publishing a new pack version

1. Edit the files under `packs/<code>/`.
2. Run validation locally:

   ```bash
   python tools/validate_catalog.py
   ```

3. Commit and push to `main`.
4. Tag the release with a `lang-vX.Y.Z` tag, for example:

   ```bash
   git tag lang-v2026.11.1
   git push origin lang-v2026.11.1
   ```

`.github/workflows/release.yml` then:

- builds one ZIP per download component (`<code>-<kind>-v<version>.zip`);
- computes SHA-256 and size;
- uploads the ZIPs to the GitHub Release;
- rewrites `catalog.json` with the release URLs and hashes;
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
python tools/build_release.py --tag lang-v2026.11.1 \
  --repo your-org/meme-laugh-language-packs
```

The script writes ZIPs to `dist/` and updates `catalog.json` in place. Upload `dist/*` to the
GitHub Release manually if you are not using the workflow.

## How the game consumes this repository

The game reads `catalog.json` through an `ILanguageContentSource`. The default source is HTTP
(GitHub Releases / raw.githubusercontent.com), configured in
`StreamingAssets/LanguagePacks/source.json`. Alternative implementations exist for local
folders and Steam depots, so the source can be replaced without touching game logic.

Installed files live in:

```
%USERPROFILE%\AppData\LocalLow\Meme & Co.\Meme Laugh\LanguagePacks\
  <language>/<kind>/...
  _engines/stt-runtime/...
  installed.json
```

## Publishing options

### 1. GitHub Releases (development and standalone builds)

- Simple, free, works for public builds.
- **No SLA.** GitHub Releases can be slow or unavailable in some regions.
- Not recommended as the only distribution channel for a commercial Steam release.
- URLs used by the current `catalog.json` are placeholders until the repository owner is set;
  the release workflow rewrites them using the actual GitHub repository.

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
otherwise. Vosk and its models are **Apache-2.0**. See `packs/<code>/licenses.json` and
`LICENSE`.
