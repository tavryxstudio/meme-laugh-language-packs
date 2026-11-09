#!/usr/bin/env python3
"""Build release ZIPs and rewrite catalog.json with real URLs, hashes and sizes.

Usage:
  python tools/build_release.py --tag lang-v2026.11.1 --repo owner/repo

The script is deterministic: the same source files produce the same ZIP
byte-for-byte, so hashes are stable across CI runs. It never downloads anything
and never commits large model files.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog.json")
PACKS = os.path.join(ROOT, "packs")
DIST = os.path.join(ROOT, "dist")

KIND_FILE = {"ui": "ui.json", "dialogue": "dialogue.json"}


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, value) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def build_zip(payload: bytes, name: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, payload)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", ""),
                        help="release tag, for example lang-v2026.11.1")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "meme-laugh/meme-laugh-language-packs"),
                        help="GitHub repository, owner/name")
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument("--packs", default=PACKS)
    parser.add_argument("--dist", default=DIST)
    args = parser.parse_args()

    tag = args.tag
    if not tag:
        print("ERROR: --tag is required (or set GITHUB_REF_NAME)", file=sys.stderr)
        return 2
    match = re.match(r"^lang-v(\d+\.\d+\.\d+.*)$", tag)
    if not match:
        print(f"ERROR: tag '{tag}' must look like lang-v2026.11.1", file=sys.stderr)
        return 2
    version = match.group(1)

    catalog = load_json(args.catalog)
    catalog["catalogVersion"] = version
    base = f"https://github.com/{args.repo}/releases/download/{tag}"

    os.makedirs(args.dist, exist_ok=True)
    assets: list[dict] = []

    for language in catalog.get("languages", []):
        code = language.get("code", "")
        for component in language.get("components", []):
            if component.get("builtIn"):
                continue
            kind = component.get("kind")
            if kind not in KIND_FILE:
                # stt-model / stt-runtime are hosted externally in this repository.
                continue
            payload_path = os.path.join(args.packs, code, KIND_FILE[kind])
            if not os.path.isfile(payload_path):
                print(f"ERROR: missing {payload_path}", file=sys.stderr)
                return 1
            with open(payload_path, "rb") as f:
                payload = f.read()
            filename = f"{code}-{kind}-v{component.get('version', 1)}.zip"
            data = build_zip(payload, KIND_FILE[kind])
            with open(os.path.join(args.dist, filename), "wb") as f:
                f.write(data)
            component["url"] = f"{base}/{filename}"
            component["sha256"] = hashlib.sha256(data).hexdigest()
            component["sizeBytes"] = len(data)
            assets.append({
                "file": filename,
                "id": component.get("id"),
                "sha256": component["sha256"],
                "sizeBytes": component["sizeBytes"],
            })
            print(f"{filename}: {component['sizeBytes']} bytes {component['sha256']}")

    write_json(args.catalog, catalog)
    write_json(os.path.join(args.dist, "release-manifest.json"), {
        "tag": tag,
        "catalogVersion": version,
        "assets": assets,
    })
    print(f"catalog updated: {args.catalog} (catalogVersion {version}, {len(assets)} assets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
