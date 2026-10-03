#!/usr/bin/env python3
"""Summarise a git repository's history as JSON for architecture analysis.

Usage: history.py [repo_path] > history.json

Reads commit metadata and changed paths only (works on a blobless clone made
with `git clone --filter=blob:none`). Author identities are counted, never
printed.
"""
import collections
import heapq
import json
import os
import re
import subprocess
import sys

KEYWORDS = re.compile(
    r"\b(refactor|rewrite|rewrote|migrat|replace|remov|deprecat|introduc|switch(ed)? to|"
    r"drop(ped)? support|split|extract|merge[d]? .* into|rename|redesign|rearchitect|"
    r"monorepo|breaking)\w*",
    re.I,
)
DECISION_DOC = re.compile(
    r"(^|/)(adrs?|rfcs?|decisions?|design[-_ ]?docs?|architecture|proposals?|keps?|peps?)(/|$)"
    r"|(^|/)(ARCHITECTURE|DESIGN|CHANGELOG|CHANGES|HISTORY|NEWS|RELEASES?|ROADMAP|CONTRIBUTING|"
    r"GOVERNANCE|MAINTAINERS)(\.\w+)?$",
    re.I,
)
MANIFESTS = {
    "package.json", "pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile",
    "go.mod", "go.work", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts",
    "settings.gradle", "settings.gradle.kts", "Gemfile", "composer.json", "mix.exs",
    "CMakeLists.txt", "Makefile", "BUILD", "BUILD.bazel", "WORKSPACE", "MODULE.bazel",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Chart.yaml",
    "tsconfig.json", "deno.json", "Package.swift", "build.sbt", "project.clj", "dune-project",
}
SEMVER = re.compile(r"^\D*(\d+)\.(\d+)(?:\.(\d+))?")


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, errors="replace"
    ).stdout


def reduce_tags(tags, limit=60):
    """Keep the first tag of each major.minor; thin further if still too many."""
    seen, kept, other = set(), [], []
    for name, date in tags:
        m = SEMVER.match(name)
        if not m:
            other.append({"tag": name, "date": date})
            continue
        key = (int(m.group(1)), int(m.group(2)))
        if key not in seen:
            seen.add(key)
            kept.append({"tag": name, "date": date, "major": key[0]})
    if len(kept) > limit:
        majors, firsts = set(), []
        for t in kept:
            if t["major"] not in majors:
                majors.add(t["major"])
                firsts.append(t)
        step = max(1, len(kept) // (limit - len(firsts) or 1))
        kept = sorted(
            {t["tag"]: t for t in firsts + kept[::step]}.values(), key=lambda t: t["date"]
        )
    for t in kept:
        t.pop("major", None)
    return kept, other[:20]


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    if not git(repo, "rev-parse", "--git-dir").strip():
        sys.exit(f"not a git repository: {repo}")

    files = [f for f in git(repo, "ls-files").splitlines() if f]
    live_top = {f.split("/", 1)[0] if "/" in f else "(root files)" for f in files}
    live_two = {"/".join(f.split("/")[:2]) for f in files if f.count("/") >= 2}

    commits_per_year = collections.Counter()
    authors_per_year = collections.defaultdict(set)
    all_authors = set()
    paths = {}  # prefix -> [first, last, commits]
    file_commits = collections.Counter()
    largest = []  # heap of (n_files, date, sha, subject)
    notable = []
    total = 0

    proc = subprocess.Popen(
        ["git", "-C", repo, "log", "--no-renames", "--date=short",
         "--format=@@%H%x09%ad%x09%ae%x09%s", "--name-only"],
        stdout=subprocess.PIPE, text=True, errors="replace",
    )
    cur = None  # (sha, date, subject, n_files, touched prefixes)

    def flush():
        if not cur:
            return
        sha, date, subject, n, touched = cur
        for p in touched:
            rec = paths.setdefault(p, [date, date, 0])
            rec[0] = min(rec[0], date)
            rec[1] = max(rec[1], date)
            rec[2] += 1
        if KEYWORDS.search(subject):
            notable.append({"date": date, "sha": sha[:10], "files_changed": n,
                            "subject": subject[:160]})
        item = (n, date, sha[:10], subject[:140])
        if len(largest) < 15:
            heapq.heappush(largest, item)
        elif item > largest[0]:
            heapq.heapreplace(largest, item)

    for line in proc.stdout:
        line = line.rstrip("\n")
        if line.startswith("@@"):
            flush()
            parts = line[2:].split("\t", 3)
            if len(parts) < 4:
                cur = None
                continue
            sha, date, email, subject = parts
            total += 1
            year = date[:4]
            commits_per_year[year] += 1
            authors_per_year[year].add(email.lower())
            all_authors.add(email.lower())
            cur = [sha, date, subject, 0, set()]
        elif line and cur:
            cur[3] += 1
            file_commits[line] += 1
            seg = line.split("/")
            cur[4].add(seg[0] if len(seg) > 1 else "(root files)")
            if len(seg) >= 3:
                cur[4].add("/".join(seg[:2]))
    flush()
    proc.wait()

    def rows(depth_two):
        out = []
        for p, (first, last, n) in paths.items():
            is_two = "/" in p
            if is_two != depth_two:
                continue
            live = p in (live_two if depth_two else live_top)
            out.append({"path": p, "first_commit": first, "last_commit": last,
                        "commits": n, "exists_now": live})
        out.sort(key=lambda r: -r["commits"])
        return out

    top = rows(False)
    two = rows(True)[:70]

    # Keep the widest-reaching keyword-matched commits of each year, oldest first.
    by_year = collections.defaultdict(list)
    for c in notable:
        by_year[c["date"][:4]].append(c)
    per_year = max(3, 96 // max(1, len(by_year)))
    notable = sorted(
        (c for cs in by_year.values()
         for c in sorted(cs, key=lambda c: -c["files_changed"])[:per_year]),
        key=lambda c: c["date"],
    )

    tags = [
        tuple(l.split("\t")) for l in git(
            repo, "for-each-ref", "--sort=creatordate",
            "--format=%(refname:short)%09%(creatordate:short)", "refs/tags",
        ).splitlines() if "\t" in l
    ]
    release_tags, other_tags = reduce_tags(tags)

    ext = collections.Counter(
        (os.path.splitext(f)[1].lower() or "(none)") for f in files
    )
    dates = sorted(d for rec in paths.values() for d in rec[:2])
    live_files = set(files)

    result = {
        "head": git(repo, "log", "-1", "--format=%H %ad", "--date=short").strip(),
        "remote": git(repo, "config", "--get", "remote.origin.url").strip(),
        "first_commit_date": dates[0] if dates else None,
        "last_commit_date": dates[-1] if dates else None,
        "total_commits": total,
        "total_contributors": len(all_authors),
        "tracked_files": len(files),
        "commits_per_year": dict(sorted(commits_per_year.items())),
        "contributors_per_year": {y: len(s) for y, s in sorted(authors_per_year.items())},
        "file_extensions": dict(ext.most_common(15)),
        "manifests": sorted(f for f in files if os.path.basename(f) in MANIFESTS)[:80],
        "decision_and_history_docs": sorted(f for f in files if DECISION_DOC.search(f))[:80],
        "top_level_paths": [r for r in top if r["exists_now"]],
        "removed_top_level_paths": [r for r in top if not r["exists_now"]][:40],
        "second_level_paths": two,
        "release_tags": release_tags,
        "other_tags": other_tags,
        "tag_count": len(tags),
        "largest_commits": [
            {"files_changed": n, "date": d, "sha": s, "subject": subj}
            for n, d, s, subj in sorted(largest, reverse=True)
        ],
        "notable_commit_subjects": notable,
        "most_changed_files": [
            {"path": p, "commits": n, "exists_now": p in live_files}
            for p, n in file_commits.most_common(25)
        ],
    }
    json.dump(result, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
