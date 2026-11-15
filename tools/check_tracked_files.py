#!/usr/bin/env python3
"""Fail if anything that must stay out of the public repository is tracked or committed.

Modes (stdlib only, run from anywhere inside the repository):
  check_tracked_files.py                 every tracked file in the working tree's index
  check_tracked_files.py --staged        the files staged for the next commit (pre-commit hook)
  check_tracked_files.py --range A..B    every file added or changed by the commits in A..B,
                                         even if a later commit deleted it (pre-push hook, CI)
  check_tracked_files.py --all-history REV   the same for every commit reachable from REV

What it refuses (see docs/CI.md):
  - paths in the scratch and reference areas (refs/, scratch/, tmp/, voice and recording folders);
  - audio recordings (.wav .mp3 .flac .ogg .m4a ...) and video (.mp4 .webm .mov ...), also when
    renamed: file contents are recognised by their header;
  - soundfonts and reference names (FluidR3, .sf2, .sf3);
  - binaries over 5 MB that are not one of the known baked assets in KNOWN_LARGE below;
  - (range and staged modes) added lines that copy from the scratch and reference areas, such as
    a path under ~/dev/tmp/aegean-skies/refs or a recordings folder.
"""
import argparse
import re
import subprocess
import sys

MAX_BYTES = 5 * 1024 * 1024

# Known baked or checked-in binaries; the value is the largest size allowed for it.
KNOWN_LARGE = {
    "assets/terrain.bin": 32 * 1024 * 1024,        # baked by tools/bake.jo (git-ignored)
    "assets/world.bin": 32 * 1024 * 1024,          # baked by tools/bake.jo (git-ignored)
    "assets/terrain_lod.bin": 16 * 1024 * 1024,    # baked render tiles, checked in
    "assets/living-routes.bin": 16 * 1024 * 1024,  # baked by tools/bake_living_routes.jo
    "assets/lake-basins.bin": 16 * 1024 * 1024,    # baked by tools/bake_lake_basins.py
}

AUDIO_VIDEO_EXT = {
    ".wav", ".wave", ".mp3", ".flac", ".ogg", ".oga", ".opus", ".m4a", ".aac", ".aif", ".aiff",
    ".wma", ".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv", ".flv",
}
SOUNDFONT_EXT = {".sf2", ".sf3", ".sfz", ".dls"}
SOUNDFONT_NAME = re.compile(r"fluidr3|fluid_?r3|generaluser|\.sf[23]$", re.I)

# a directory component that marks scratch, reference, voice or recording material
BANNED_DIR = re.compile(
    r"(^|/)(refs?|references?|scratch|tmp|voice|voices|voice[-_]?data|recordings?|"
    r"recorded|captures?[-_]video|stills)(/|$)",
    re.I,
)
# file names that look like recordings of voices or reference takes, outside source folders
BANNED_NAME = re.compile(r"(^|/)(recording|rec|take|voice)[-_ ]?\d*\.[a-z0-9]+$", re.I)

# headers of audio, video and soundfont files, whatever the name says
MAGICS = [
    (b"RIFF", 0, "RIFF container (wav/avi/webp-like)"),
    (b"ID3", 0, "MP3 with an ID3 tag"),
    (b"OggS", 0, "Ogg"),
    (b"fLaC", 0, "FLAC"),
    (b"FORM", 0, "AIFF/IFF"),
    (b"\x1a\x45\xdf\xa3", 0, "Matroska/WebM"),
    (b"ftyp", 4, "MP4/MOV/M4A"),
    (b"sfbk", 8, "SoundFont"),
]
# RIFF is also WebP and other images: only audio/video/soundfont subtypes count
RIFF_BAD = (b"WAVE", b"AVI ", b"sfbk")

# a copy from the scratch and reference areas, in an added line
COPY_FROM = re.compile(
    r"(~|\$HOME|/home/[a-z0-9_.-]+|/var/home/[a-z0-9_.-]+)/dev/tmp/[^\s'\"`)]*"
    r"(refs?|voice|voices|recordings?|stills|fluidr3)\b",
    re.I,
)
COPY_FROM_OK_SUFFIXES = (".md",)  # documentation may name the areas; code and data may not


def git(*args, check=True, text=False):
    r = subprocess.run(["git", *args], capture_output=True, check=False)
    if check and r.returncode != 0:
        sys.exit("git %s failed: %s" % (" ".join(args), r.stderr.decode(errors="replace")))
    return r.stdout.decode(errors="replace") if text else r.stdout


def ext_of(path):
    base = path.rsplit("/", 1)[-1]
    return ("." + base.rsplit(".", 1)[-1].lower()) if "." in base else ""


def blob_info(blobs):
    """size and first 64 bytes of each blob (a list of object ids)."""
    out = {}
    if not blobs:
        return out
    uniq = sorted(set(blobs))
    p = subprocess.run(["git", "cat-file", "--batch"], input="".join(b + "\n" for b in uniq).encode(),
                       capture_output=True, check=True)
    data, i = p.stdout, 0
    for _ in uniq:
        j = data.index(b"\n", i)
        header = data[i:j].decode().split()
        if len(header) < 3:  # "<id> missing"
            i = j + 1
            continue
        oid, _typ, size = header[0], header[1], int(header[2])
        body = data[j + 1 : j + 1 + size]
        out[oid] = (size, body)
        i = j + 1 + size + 1
    return out


def entries_index(staged):
    """[(path, blob)] for the index (all tracked files) or only what differs from HEAD."""
    if staged:
        raw = git("diff", "--cached", "--raw", "--no-abbrev", "--no-renames", "--diff-filter=AMC", "-z")
        return parse_raw(raw)
    raw = git("ls-files", "--stage", "-z").decode(errors="replace")
    res = []
    for rec in raw.split("\0"):
        if not rec:
            continue
        meta, path = rec.split("\t", 1)
        mode, oid, _stage = meta.split()
        if mode != "160000":  # not a submodule
            res.append((path, oid))
    return res


def parse_raw(raw):
    parts = raw.decode(errors="replace").split("\0")
    res, i = [], 0
    while i < len(parts):
        if parts[i].startswith(":"):
            meta = parts[i].split()
            path = parts[i + 1]
            res.append((path, meta[3]))
            i += 2
        else:
            i += 1
    return res


def entries_range(rng):
    raw = git("log", "--raw", "--no-abbrev", "--no-renames", "--diff-filter=AMC", "-z", "--format=", rng)
    return parse_raw(raw)


def entries_history(rev):
    return entries_range(rev)


def added_lines(rng, staged):
    """(path, line) for lines added by the range or the staged change."""
    if staged:
        text = git("diff", "--cached", "--no-renames", "-U0", "--no-color", text=True)
    else:
        text = git("log", "-p", "--no-renames", "-U0", "--no-color", "--format=", rng, text=True)
    path = None
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and path:
            yield path, line[1:]


def check(entries, lines):
    problems = []  # (path, reason)
    seen = {}
    info = blob_info([oid for _p, oid in entries])
    for path, oid in entries:
        reasons = []
        ext = ext_of(path)
        if BANNED_DIR.search(path):
            reasons.append("is under a scratch/reference/voice/recording folder")
        if BANNED_NAME.search(path) and ext not in {".jo", ".py", ".md", ".mjs", ".cjs", ".js", ".json", ".txt"}:
            reasons.append("is named like a recording")
        if ext in AUDIO_VIDEO_EXT:
            reasons.append("is an audio or video file (%s)" % ext)
        if ext in SOUNDFONT_EXT or SOUNDFONT_NAME.search(path.rsplit("/", 1)[-1]):
            reasons.append("is a soundfont or carries a reference name (FluidR3, .sf2)")
        size, body = info.get(oid, (0, b""))
        head = body[:64]
        for magic, off, what in MAGICS:
            if head[off : off + len(magic)] == magic:
                if magic == b"RIFF" and head[8:12] not in RIFF_BAD:
                    continue
                if ext in AUDIO_VIDEO_EXT or ext in SOUNDFONT_EXT:
                    continue  # already reported by name
                reasons.append("has the header of %s, whatever its name" % what)
                break
        is_binary = b"\0" in body[:8192]
        limit = KNOWN_LARGE.get(path)
        if size > MAX_BYTES and limit is None:
            reasons.append("is %.1f MB, over the 5 MB limit, and not a known baked asset "
                           "(tools/check_tracked_files.py KNOWN_LARGE)" % (size / 1048576))
        elif limit is not None and size > limit:
            reasons.append("is %.1f MB, over the %.0f MB allowed for this baked asset"
                           % (size / 1048576, limit / 1048576))
        elif size > MAX_BYTES and not is_binary and limit is None:
            pass
        for r in reasons:
            if (path, r) not in seen:
                seen[(path, r)] = True
                problems.append((path, r))
    for path, line in lines:
        if COPY_FROM.search(line) and not path.endswith(COPY_FROM_OK_SUFFIXES):
            key = (path, "copies from the scratch/reference areas: %s" % line.strip()[:120])
            if key not in seen:
                seen[key] = True
                problems.append(key)
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staged", action="store_true", help="only what is staged for the next commit")
    ap.add_argument("--range", help="commits to check, A..B (files added/changed in them, deleted or not)")
    ap.add_argument("--all-history", metavar="REV", help="every commit reachable from REV")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    top = git("rev-parse", "--show-toplevel", text=True).strip()
    import os
    os.chdir(top)

    entries, lines, what = [], [], []
    if a.range:
        entries += entries_range(a.range)
        lines = list(added_lines(a.range, False))
        what.append("commits %s" % a.range)
    elif a.all_history:
        entries += entries_history(a.all_history)
        what.append("all history of %s" % a.all_history)
    elif a.staged:
        entries += entries_index(True)
        lines = list(added_lines(None, True))
        what.append("staged files")
    else:
        entries += entries_index(False)
        what.append("tracked files")
    problems = check(entries, lines)
    if problems:
        print("check_tracked_files: %d problem(s) in %s -- these must stay out of git:" % (len(problems), what[0]),
              file=sys.stderr)
        for path, reason in problems:
            print("  %s: %s" % (path, reason), file=sys.stderr)
        print("Remove the file from the commit (git rm --cached / amend / rebase) before pushing; if it is "
              "already pushed, tell the coordinator.", file=sys.stderr)
        sys.exit(1)
    if not a.quiet:
        print("check_tracked_files: ok (%d files in %s)" % (len(set(p for p, _ in entries)), what[0]))


if __name__ == "__main__":
    main()
