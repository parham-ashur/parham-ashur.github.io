#!/usr/bin/env python3
"""
publish.py - add new photos to the photography gallery on parham-ashur.github.io

WORKFLOW
  1. Drop new photos into your source folder (default: ~/Documents/photography),
     named so the filename carries the info for the caption:

         [NNN_]<month><year>_<location>.<ext>
         e.g.  064_dec2025_paris.heic   or   dec2025_eiffel tower_paris.jpg

     - The leading NNN_ sequence number is OPTIONAL; it just keeps originals tidy.
     - <month> may be full or short: june/jun, august/aug, sept, etc.
     - <location> is free text (spaces ok). It becomes the caption via the
       LOCATIONS map below; anything not in the map is just Title-Cased, and you
       can always hand-edit the caption afterwards in web/photos.json.

  2. Run it:
         python3 publish.py             # preview -> convert -> update manifest -> ask to push
         python3 publish.py --dry-run   # show what WOULD happen, touch nothing
         python3 publish.py --push      # also commit + push without the y/N prompt

  3. photography.html loads web/photos.json at page load, so the new photos appear
     as soon as the push lands on GitHub Pages (~1 min).

MANIFEST (web/photos.json) - one object per photo:
      { "src": "web/photo48.webp", "caption": "Paris (December 2025)",
        "original": "064_dec2025_paris", "show": true }
  - "original" is the source filename stem. It's how this script knows what's
    already published, so re-running is idempotent (never creates duplicates).
  - "show": false hides a photo from the gallery without deleting it.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
WEB = REPO / "web"
MANIFEST = WEB / "photos.json"
SOURCE_DIR = Path(os.environ.get("PHOTO_SRC", Path.home() / "Documents" / "photography"))
EXTS = {".heic", ".jpg", ".jpeg", ".png"}
MAX_SIDE = 2000          # longest edge in px (matches existing gallery images)
QUALITY = 80             # webp quality

MONTHS = {
    "jan": "January", "january": "January", "feb": "February", "february": "February",
    "mar": "March", "march": "March", "apr": "April", "april": "April", "may": "May",
    "jun": "June", "june": "June", "jul": "July", "july": "July",
    "aug": "August", "august": "August", "sep": "September", "sept": "September",
    "september": "September", "oct": "October", "october": "October",
    "nov": "November", "november": "November", "dec": "December", "december": "December",
}

# Curated, nicer captions for known locations. Keys are the lowercased <location>
# part of the filename. Unknown locations fall back to Title Case.
LOCATIONS = {
    "bocconi": "Bocconi University, Milan",
    "bocconi_milan": "Bocconi University, Milan",
    "street_milan": "Street in Milan",
    "museo del novecento": "Museo del Novecento",
    "pinacoteca di brera": "Pinacoteca di Brera",
    "villa necchi campiglio": "Villa Necchi Campiglio",
    "milan conservatory": "Milan Conservatory",
    "como lake": "Lake Como",
    "museo pinacoteca civica": "Museo Pinacoteca Civica",
    "milan": "Cityscapes of Milan",
    "prada foundation": "Fondazione Prada, Milan",
    "prada foundation_milan": "Fondazione Prada, Milan",
    "lugano": "Lugano",
    "train to lugano": "Train to Lugano",
    "home": "Home",
    "athens": "Athens",
    "archopolis": "Acropolis",
    "archopolis museum": "Acropolis Museum",
    "paros island": "Paros",
    "antiparos island": "Antiparos",
    "allos": "Allos",
    "venice": "Venice",
    "burano": "Burano",
    "antibes": "Antibes",
}

STEM_RE = re.compile(r"^(?:\d+[_-])?([A-Za-z]+)(\d{4})[_-](.+)$")


def caption_from_stem(stem: str) -> str:
    """Derive a human caption from a filename stem, e.g.
    '064_dec2025_paris' -> 'Paris (December 2025)'."""
    m = STEM_RE.match(stem)
    if not m:
        return stem.replace("_", " ").replace("-", " ").strip().title()
    month_raw, year, location = m.group(1).lower(), m.group(2), m.group(3)
    month = MONTHS.get(month_raw, month_raw.title())
    loc = LOCATIONS.get(location.lower().strip()) or location.replace("_", " ").strip().title()
    return f"{loc} ({month} {year})"


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return []


def next_photo_number(manifest) -> int:
    nums = []
    for e in manifest:
        m = re.search(r"photo(\d+)\.webp", e.get("src", ""))
        if m:
            nums.append(int(m.group(1)))
    for f in WEB.glob("photo*.webp"):
        m = re.fullmatch(r"photo(\d+)\.webp", f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


def convert(src: Path, out: Path) -> None:
    subprocess.run(
        ["magick", str(src), "-auto-orient",
         "-resize", f"{MAX_SIDE}x{MAX_SIDE}>", "-quality", str(QUALITY), str(out)],
        check=True,
    )


def git(*args) -> None:
    subprocess.run(["git", *args], cwd=REPO, check=True)


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    push = "--push" in sys.argv

    if not SOURCE_DIR.is_dir():
        print(f"Source folder not found: {SOURCE_DIR}", file=sys.stderr)
        return 1

    manifest = load_manifest()
    published = {e.get("original") for e in manifest if e.get("original")}

    candidates = sorted(
        p for p in SOURCE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in EXTS and p.stem not in published
    )
    if not candidates:
        print("Nothing new to publish - the manifest is already up to date.")
        return 0

    n = next_photo_number(manifest)
    planned = []
    print(f"{len(candidates)} new photo(s) found in {SOURCE_DIR}:\n")
    for src in candidates:
        out_name = f"photo{n}.webp"
        cap = caption_from_stem(src.stem)
        print(f"  {src.name}")
        print(f"      -> web/{out_name}   “{cap}”")
        planned.append((src, out_name, cap))
        n += 1

    if dry_run:
        print("\n(dry run - nothing written)")
        return 0

    print()
    for src, out_name, cap in planned:
        convert(src, WEB / out_name)
        manifest.append({"src": f"web/{out_name}", "caption": cap,
                         "original": src.stem, "show": True})
        print(f"converted {out_name}")
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"\nUpdated {MANIFEST.relative_to(REPO)} ({len(planned)} added).")

    if not push:
        try:
            push = input("\nCommit and push to the live site now? [y/N] ").strip().lower() in ("y", "yes")
        except EOFError:
            push = False
    if push:
        captions = ", ".join(dict.fromkeys(c for _, _, c in planned))
        git("add", "web")
        git("commit", "-m", f"Add {len(planned)} photo(s): {captions}")
        git("push")
        print("Pushed. Live via GitHub Pages in ~1 minute.")
    else:
        print(f"\nNot pushed. Review with:  git -C {REPO} diff --staged")
        print(f"Then publish with:        git -C {REPO} add web && git -C {REPO} commit -m '...' && git -C {REPO} push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
