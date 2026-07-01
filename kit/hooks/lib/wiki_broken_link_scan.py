import os
import re
import sys

repo_root = os.environ.get("REPO_ROOT", "")
wiki_root = os.environ.get("WIKI_ROOT", "")
changed_str = os.environ.get("CHANGED_FILES", "")
if not wiki_root or not os.path.isdir(wiki_root) or not changed_str.strip():
    sys.exit(0)

# Build basename index from ALL wiki .md files (resolution corpus = full wiki,
# scan corpus = changed files only).
all_md = []
for dirpath, _dirnames, filenames in os.walk(wiki_root):
    for fn in filenames:
        if fn.endswith(".md"):
            all_md.append(os.path.join(dirpath, fn))

# Index by basename (without .md) for unqualified [[name]] resolution.
basename_index = {}
for p in all_md:
    stem = os.path.splitext(os.path.basename(p))[0]
    basename_index.setdefault(stem, []).append(p)

# Changed files set (absolute paths under wiki_root).
changed_files = set()
for line in changed_str.splitlines():
    line = line.strip()
    if not line:
        continue
    abs_path = os.path.join(repo_root, line)
    if os.path.isfile(abs_path):
        changed_files.add(abs_path)

# Regex: matches [[anything]] excluding empty + multi-line.
LINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")
# TOML table syntax inside code blocks: [[tool.X.Y]] (dotted, no path sep)
TOML_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.\-]*$")


def resolve(target: str, source_file: str) -> bool:
    """Return True if link target resolves to an existing wiki .md file."""
    # Strip alias: [[path|alias]] → path
    target = target.split("|", 1)[0].strip()
    # Empty / anchor-only: skip (treat as valid)
    if not target or target.startswith("#"):
        return True
    # Markdown ellipsis literal: [[...]]
    if target == "...":
        return True
    # External URLs in wiki-link form (rare): treat as valid (out of scope)
    if target.startswith(("http://", "https://", "mailto:")):
        return True
    # Placeholder pattern: [[NNNN-slug]] in templates/examples (uppercase NNNN)
    if "NNNN" in target:
        return True
    # TOML table headers `[[tool.X.Y]]` inside fenced code blocks — skip
    # (no path separator, contains dots).
    if "/" not in target and "." in target and TOML_RE.match(target):
        return True
    # Drop trailing .md if user wrote it explicitly
    if target.endswith(".md"):
        target = target[:-3]
    # Drop fragment: path#section → path
    target = target.split("#", 1)[0]
    if not target:
        return True

    # Resolve relative path (contains /) — try THREE interpretations:
    #   1) relative to source_file's dir (handles ../decisions/X)
    #   2) relative to wiki_root (handles project/components/X from any source)
    #   3) relative to repo_root (handles cross-repo refs like ../../CLAUDE)
    # Pass if any resolves to existing file.
    if "/" in target:
        # (1) relative to source dir
        rel_candidate = os.path.normpath(os.path.join(os.path.dirname(source_file), target + ".md"))
        if os.path.isfile(rel_candidate):
            return True
        # (2) relative to wiki root
        abs_candidate = os.path.normpath(os.path.join(wiki_root, target + ".md"))
        if abs_candidate.startswith(wiki_root) and os.path.isfile(abs_candidate):
            return True
        # (3) cross-repo ref via ../../ — resolve from source dir, allow exit
        # from wiki tree, must still exist within repo_root.
        if repo_root and rel_candidate.startswith(repo_root):
            return False  # already checked in (1) — explicit fail
        return False

    # Unqualified basename: search basename_index
    return target in basename_index


broken = []  # list of (relpath, line_no, raw_link)

# Triple-backtick fenced-block delimiter — built via chr(0x60) к avoid
# bash backtick parsing collision inside `$(... <<'PYEOF' ...)` heredoc.
FENCE = chr(0x60) * 3
BACKTICK = chr(0x60)

# Scan ONLY changed wiki files (avoid historical plan noise).
for md_path in sorted(changed_files):
    try:
        with open(md_path, encoding="utf-8") as f:
            in_code_block = False
            for line_no, line in enumerate(f, start=1):
                # Track fenced code blocks (FENCE opener/closer toggle).
                stripped = line.lstrip()
                if stripped.startswith(FENCE):
                    in_code_block = not in_code_block
                    continue
                # Skip link scanning inside code blocks (TOML tables / shell).
                if in_code_block:
                    continue
                for m in LINK_RE.finditer(line):
                    link = m.group(1).strip()
                    if not link:
                        continue
                    # Skip if match is inside inline-code span (odd backtick
                    # count before match position = inside `code`).
                    if line[: m.start()].count(BACKTICK) % 2 == 1:
                        continue
                    if not resolve(link, md_path):
                        rel = os.path.relpath(md_path, wiki_root)
                        broken.append((rel, line_no, link))
    except (OSError, UnicodeDecodeError):
        continue

if broken:
    for rel, ln, link in broken:
        print(f"{rel}:{ln}: [[{link}]]")
