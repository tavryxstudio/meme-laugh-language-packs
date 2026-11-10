#!/usr/bin/env python3
"""Validate catalog.json, UI packs and dialogue packs.

Checks:
  * catalog.json against schema/catalog.schema.json (when jsonschema is installed);
  * unique component ids across languages;
  * every declared language code is supported by the game;
  * source files referenced by non-builtIn packs exist;
  * non-builtIn download components have url, sha256 and sizeBytes;
  * dependencies point at known component ids;
  * minGameVersion values are well formed;
  * dialogue.json against schema/dialogue.schema.json, including the optional
    `mature` flag;
  * English and Russian dialogue packs keep the same event set and at least the
    expected number of lines.

Exit code 0 = valid, 1 = invalid. Suitable for CI.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog.json")
SCHEMA = os.path.join(ROOT, "schema", "catalog.schema.json")
DIALOGUE_SCHEMA = os.path.join(ROOT, "schema", "dialogue.schema.json")
PACKS = os.path.join(ROOT, "packs")

SUPPORTED_LANGUAGES = {
    "en", "ru", "uk", "de", "fr", "es", "it", "pt", "pl", "tr", "cs", "nl"
}
COMPONENT_KINDS = {"ui", "dialogue"}
SEMVER = re.compile(r"^\d+\.\d+(\.\d+)?$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
KIND_FILE = {"ui": "ui.json", "dialogue": "dialogue.json"}
EXPECTED_LINES = {"en": 278, "ru": 278}
EXPECTED_EVENTS = 21

errors: list[str] = []
warnings: list[str] = []
dialogue_events: dict[str, set[str]] = {}


def fail(message: str) -> None:
    errors.append(message)


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_schema(catalog: dict) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        warnings.append("jsonschema is not installed; schema validation skipped")
        return
    schema = load_json(SCHEMA)
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(catalog), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in error.path) or "<root>"
        fail(f"schema: {where}: {error.message}")


def check_dialogue(code: str, path: str) -> set[str]:
    try:
        data = load_json(path)
    except Exception as exc:  # noqa: BLE001
        fail(f"packs/{code}/dialogue.json is not valid JSON: {exc}")
        return set()

    try:
        import jsonschema  # type: ignore
        schema = load_json(DIALOGUE_SCHEMA)
        validator = jsonschema.Draft7Validator(schema)
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in error.path) or "<root>"
            fail(f"dialogue {code}: {where}: {error.message}")
    except ImportError:
        pass

    lines = data.get("lines")
    if not isinstance(lines, list):
        fail(f"packs/{code}/dialogue.json: lines must be an array")
        return set()

    events: set[str] = set()
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            fail(f"packs/{code}/dialogue.json: line {index} is not an object")
            continue
        event = line.get("event")
        text = line.get("text")
        if not isinstance(event, str) or not event:
            fail(f"packs/{code}/dialogue.json: line {index} has no event")
        else:
            events.add(event)
        if not isinstance(text, str) or not text:
            fail(f"packs/{code}/dialogue.json: line {index} has no text")
        if "mature" in line and not isinstance(line["mature"], bool):
            fail(f"packs/{code}/dialogue.json: line {index} mature must be boolean")

    expected_lines = EXPECTED_LINES.get(code)
    if expected_lines is not None and len(lines) < expected_lines:
        fail(f"packs/{code}/dialogue.json: expected at least {expected_lines} lines, got {len(lines)}")
    if code in EXPECTED_LINES and len(events) != EXPECTED_EVENTS:
        fail(f"packs/{code}/dialogue.json: expected {EXPECTED_EVENTS} event groups, got {len(events)}")

    dialogue_events[code] = events
    return events


def check_language(lang: dict) -> None:
    code = lang.get("code", "")
    if code not in SUPPORTED_LANGUAGES:
        fail(f"language '{code}': not supported by Loc.Languages")
    status = lang.get("status")
    built_in = bool(lang.get("builtIn"))

    pack_dir = os.path.join(PACKS, code)
    if status != "missing" and not os.path.isdir(pack_dir):
        fail(f"packs/{code}: directory is missing for status '{status}'")

    if status == "complete" and not built_in:
        for name in ("ui.json", "dialogue.json", "pack.json", "licenses.json"):
            if not os.path.isfile(os.path.join(pack_dir, name)):
                fail(f"packs/{code}/{name}: required file is missing")

    dialogue_path = os.path.join(pack_dir, "dialogue.json")
    if os.path.isfile(dialogue_path):
        check_dialogue(code, dialogue_path)

    for component in lang.get("components", []):
        check_component(component, code)


def check_component(component: dict, language_code: str | None = None) -> None:
    cid = component.get("id", "<missing id>")
    kind = component.get("kind")
    if kind not in COMPONENT_KINDS:
        fail(f"{cid}: unsupported kind '{kind}'")
    if component.get("version", 0) < 1:
        fail(f"{cid}: version must be >= 1")
    version = component.get("minGameVersion", "")
    if not SEMVER.match(str(version)):
        fail(f"{cid}: minGameVersion '{version}' is not X.Y or X.Y.Z")

    built_in = bool(component.get("builtIn"))
    if not built_in:
        url = component.get("url") or ""
        sha = component.get("sha256") or ""
        size = component.get("sizeBytes") or 0
        if not url:
            fail(f"{cid}: url is required for a downloadable component")
        if not SHA256.match(sha):
            fail(f"{cid}: sha256 must be 64 hex characters")
        if not isinstance(size, int) or size <= 0:
            fail(f"{cid}: sizeBytes must be > 0")

    if language_code and kind in KIND_FILE and not built_in:
        payload = os.path.join(PACKS, language_code, KIND_FILE[kind])
        if not os.path.isfile(payload):
            fail(f"{cid}: source file packs/{language_code}/{KIND_FILE[kind]} is missing")


def main() -> int:
    if not os.path.isfile(CATALOG):
        fail("catalog.json is missing")
        return report()

    try:
        catalog = load_json(CATALOG)
    except Exception as exc:  # noqa: BLE001
        fail(f"catalog.json is not valid JSON: {exc}")
        return report()

    check_schema(catalog)

    if catalog.get("schemaVersion") != 1:
        fail("schemaVersion must be 1")
    if not SEMVER.match(str(catalog.get("minGameVersion", ""))):
        fail("catalog.minGameVersion must be X.Y or X.Y.Z")

    ids: dict[str, str] = {}

    def register(component: dict) -> None:
        cid = component.get("id")
        if not cid:
            return
        if cid in ids:
            fail(f"duplicate component id '{cid}'")
        ids[cid] = component.get("kind", "")

    languages = catalog.get("languages", [])
    codes = [lang.get("code") for lang in languages]
    if len(codes) != len(set(codes)):
        fail("duplicate language codes")

    for lang in languages:
        check_language(lang)
        for component in lang.get("components", []):
            register(component)

    if "en" in dialogue_events and "ru" in dialogue_events:
        only_en = sorted(dialogue_events["en"] - dialogue_events["ru"])
        only_ru = sorted(dialogue_events["ru"] - dialogue_events["en"])
        if only_en or only_ru:
            fail("en/ru dialogue event sets differ: only en=" +
                 repr(only_en) + ", only ru=" + repr(only_ru))

    engines = catalog.get("engines", [])
    for engine in engines:
        check_component(engine)
        register(engine)

    for lang in languages:
        for component in lang.get("components", []):
            for dep in component.get("dependencies", []):
                if dep not in ids:
                    fail(f"{component.get('id')}: unknown dependency '{dep}'")
    for engine in engines:
        for dep in engine.get("dependencies", []):
            if dep not in ids:
                fail(f"{engine.get('id')}: unknown dependency '{dep}'")

    return report()


def report() -> int:
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"\n{len(errors)} error(s).")
        return 1
    print("catalog.json is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
