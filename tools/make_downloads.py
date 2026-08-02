"""Build one ZIP per project/template so the site can offer direct downloads.

The site is static, so a "Download ZIP" button needs a real file sitting next
to the HTML. This script builds those files into downloads/ and writes a
manifest the page reads to show each size.

Archives are built from the COMMITTED tree (HEAD), never from the working
directory - uncommitted edits and untracked files cannot leak into a
published zip. Commit first, then run from anywhere:

    python tools/make_downloads.py

Entries come from data.js, so this never needs editing when a project is added
-- add it there and re-run. Nothing is deleted that the script did not create.
"""

import json
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "data.js")
OUT_DIR = os.path.join(ROOT, "downloads")

# Build artefacts, editor droppings, local state and Rhino's automatic backup
# copies. Tracked or not, none of these belong in a download - the .3dmbak
# files in particular are as large as the models they shadow.
SKIP_DIRS = {".git", "__pycache__", ".omc", ".vscode", ".idea", "node_modules"}
SKIP_EXTS = {".pyc", ".pyo", ".3dmbak"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def git(*args):
    """Run git in the repo root, return stdout bytes, raise on failure."""
    return subprocess.run(
        ["git", *args], capture_output=True, cwd=ROOT, check=True
    ).stdout


def entries():
    """(id, path) for every template and project defined in data.js."""
    with open(DATA_JS, encoding="utf-8") as handle:
        source = handle.read()

    # Objects in data.js always carry id before path; capture the pair.
    found = re.findall(
        r'id:\s*"([^"]+)"(?:.*?)\n\s*path:\s*"([^"]+)"', source, re.DOTALL
    )

    # The regex above is greedy across objects if an entry lacks a path, so
    # keep only the first path seen for each id and drop unknown directories.
    seen, result = set(), []
    for entry_id, rel in found:
        if entry_id in seen:
            continue
        seen.add(entry_id)
        rel = rel.strip("/")
        if os.path.isdir(os.path.join(ROOT, rel.replace("/", os.sep))):
            result.append((entry_id, rel))
    return result


def should_skip(path):
    parts = path.split("/")
    if any(part in SKIP_DIRS for part in parts[:-1]):
        return True
    name = parts[-1]
    return name in SKIP_NAMES or os.path.splitext(name)[1].lower() in SKIP_EXTS


def tracked_files(rel):
    """Repo-relative paths under rel/ as committed at HEAD."""
    out = git("ls-tree", "-r", "--name-only", "-z", "HEAD", "--", rel)
    return sorted(p.decode("utf-8") for p in out.split(b"\0") if p)


def build(entry_id, rel):
    """Zip one folder from the HEAD tree. Returns (bytes, file count)."""
    top = os.path.basename(rel)          # extracts into a named folder, not loose files
    target = os.path.join(OUT_DIR, entry_id + ".zip")
    count = 0

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in tracked_files(rel):
            if should_skip(path):
                continue
            inner = top + "/" + path[len(rel) + 1:]
            archive.writestr(inner, git("show", "HEAD:" + path))
            count += 1

    return os.path.getsize(target), count


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return "%.0f %s" % (size, unit) if unit in ("B", "KB") else "%.1f %s" % (size, unit)
        size /= 1024.0


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    items = entries()
    if not items:
        print("No entries found in data.js -- has its format changed?")
        return 1

    manifest, total = {}, 0
    print("%-22s %10s %7s  %s" % ("ARCHIVE", "SIZE", "FILES", "SOURCE"))
    for entry_id, rel in items:
        size, count = build(entry_id, rel)
        if count == 0:
            print("%-22s %10s %7s  %s  <- nothing committed here!" % (entry_id + ".zip", "-", 0, rel))
            continue
        manifest[entry_id] = {"bytes": size, "files": count, "path": rel}
        total += size
        print("%-22s %10s %7d  %s" % (entry_id + ".zip", human(size), count, rel))

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("\n%d archives, %s total, written to downloads/" % (len(manifest), human(total)))
    print("Built from HEAD: commit content changes BEFORE running this script,")
    print("then commit downloads/ so the buttons work on the deployed site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
