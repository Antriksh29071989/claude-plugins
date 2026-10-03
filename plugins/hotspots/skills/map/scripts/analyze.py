#!/usr/bin/env python3
"""Measure where a repository's change effort and complexity overlap.

Usage: analyze.py <repo> [--months 12] [--include-tests] > metrics.json

Method (after Adam Tornhill, "Your Code as a Crime Scene"):
  hotspot score = (revisions / max revisions) x (complexity / max complexity)
where revisions is the number of commits touching a file inside the window and
complexity is indentation-based: the sum of every line's nesting depth.

Author identities are counted, never printed.
"""
import argparse
import collections
import datetime
import itertools
import json
import os
import re
import subprocess
import sys

SOURCE_EXT = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".kts", ".scala", ".go", ".rs",
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".m", ".mm", ".swift", ".cs", ".fs", ".vb", ".rb",
    ".php", ".pl", ".pm", ".lua", ".r", ".jl", ".dart", ".ex", ".exs", ".erl", ".hs", ".ml", ".clj",
    ".cljs", ".groovy", ".sh", ".bash", ".zsh", ".ps1", ".sql", ".vue", ".svelte", ".sol", ".zig", ".nim",
}
EXCLUDE = re.compile(
    r"(^|/)(node_modules|vendor|vendored|third_party|third-party|dist|build|out|target|bundle|generated|"
    r"gen|__generated__|__snapshots__|__mocks__|fixtures?|testdata|migrations|\.github)(/|$)"
    r"|\.min\.|\.generated\.|\.pb\.|_pb2\.|\.d\.ts$|\.snap$|(^|/)(package-lock|yarn|pnpm-lock)\."
)
TEST = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|e2e|integration-tests?|test-utils?|testing)(/|$)"
    r"|(\.|_|-)(test|spec|tests)\.[a-z]+$|(^|/)test_[^/]+$|_test\.[a-z]+$|Tests?\.[a-z]+$"
)
FIX = re.compile(r"\b(fix(es|ed)?|bug|hotfix|regression|revert|crash|broken|incorrect)\b", re.I)
MAX_COUPLING_COMMIT = 30
TREND_POINTS = 6
TREND_FILES = 12
MAP_FILES = 500


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, errors="replace"
    ).stdout


def measure(text):
    """Return (non-blank lines, indentation complexity, max depth)."""
    indents = []
    for line in text.splitlines():
        stripped = line.lstrip(" \t")
        if not stripped:
            continue
        lead = line[: len(line) - len(stripped)]
        indents.append(lead.count(" ") + 4 * lead.count("\t"))
    if not indents:
        return 0, 0, 0
    steps = [i for i in indents if i > 0]
    unit = 4
    if steps:
        smallest = min(steps)
        unit = smallest if smallest in (2, 3, 4, 8) else 4
    depths = [i / unit for i in indents]
    return len(indents), round(sum(depths)), round(max(depths))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--include-tests", action="store_true")
    args = ap.parse_args()
    repo = args.repo
    if not git(repo, "rev-parse", "--git-dir").strip():
        sys.exit(f"not a git repository: {repo}")

    head_sha, head_date = git(repo, "log", "-1", "--format=%H %ad", "--date=short").split()
    end = datetime.date.fromisoformat(head_date)
    start = end - datetime.timedelta(days=round(args.months * 30.44))

    tracked = [f for f in git(repo, "ls-files").splitlines() if f]
    skipped_tests = 0
    files = {}
    for path in tracked:
        if os.path.splitext(path)[1].lower() not in SOURCE_EXT or EXCLUDE.search(path):
            continue
        is_test = bool(TEST.search(path))
        if is_test and not args.include_tests:
            skipped_tests += 1
            continue
        try:
            with open(os.path.join(repo, path), encoding="utf-8", errors="replace") as fh:
                loc, complexity, depth = measure(fh.read())
        except OSError:
            continue
        if loc == 0:
            continue
        files[path] = {"path": path, "loc": loc, "complexity": complexity, "max_depth": depth,
                       "revisions": 0, "fixes": 0, "authors": collections.Counter(), "is_test": is_test}

    # One pass over the window's history.
    proc = subprocess.Popen(
        ["git", "-C", repo, "log", "--no-merges", "--no-renames", f"--since={start.isoformat()}",
         "--date=short", "--format=@@%H%x09%ad%x09%ae%x09%s", "--name-only"],
        stdout=subprocess.PIPE, text=True, errors="replace",
    )
    commits = 0
    touches_total = 0
    pair_counts = collections.Counter()
    cur_files, cur_meta = [], None

    def flush():
        nonlocal touches_total
        if cur_meta is None:
            return
        email, is_fix = cur_meta
        present = [f for f in cur_files if f in files]
        for f in present:
            rec = files[f]
            rec["revisions"] += 1
            rec["authors"][email] += 1
            if is_fix:
                rec["fixes"] += 1
        touches_total += len(present)
        if 2 <= len(present) <= MAX_COUPLING_COMMIT:
            for a, b in itertools.combinations(sorted(present), 2):
                pair_counts[(a, b)] += 1

    for line in proc.stdout:
        line = line.rstrip("\n")
        if line.startswith("@@"):
            flush()
            parts = line[2:].split("\t", 3)
            if len(parts) < 4:
                cur_meta, cur_files = None, []
                continue
            commits += 1
            cur_meta = (parts[2].lower(), bool(FIX.search(parts[3])))
            cur_files = []
        elif line:
            cur_files.append(line)
    flush()
    proc.wait()

    if not files:
        sys.exit("no source files found to analyse")
    max_rev = max(f["revisions"] for f in files.values()) or 1
    max_cx = max(f["complexity"] for f in files.values()) or 1
    rows = []
    for rec in files.values():
        authors = rec.pop("authors")
        total = sum(authors.values())
        rec["authors"] = len(authors)
        rec["main_author_share"] = round(max(authors.values()) / total, 2) if total else 0
        rec["score"] = round((rec["revisions"] / max_rev) * (rec["complexity"] / max_cx), 4)
        rec["change_share"] = round(rec["revisions"] / commits, 4) if commits else 0
        rows.append(rec)
    rows.sort(key=lambda r: (-r["score"], -r["revisions"]))
    for rank, rec in enumerate(rows, 1):
        rec["rank"] = rank

    # How concentrated is change? Share of file-touches landing in the busiest files.
    by_rev = sorted((r["revisions"] for r in rows), reverse=True)
    concentration = []
    for pct in (1, 5, 10, 20):
        n = max(1, round(len(by_rev) * pct / 100))
        concentration.append({"top_files_pct": pct, "files": n,
                              "share_of_changes": round(sum(by_rev[:n]) / touches_total, 3) if touches_total else 0})
    untouched = sum(1 for r in rows if r["revisions"] == 0)

    # Complexity trend of the top hotspots: sample the file at evenly spaced commits in the window.
    hotspots = [r for r in rows if r["revisions"] > 0][:TREND_FILES]
    for rec in hotspots:
        shas = [l.split() for l in git(
            repo, "log", "--no-merges", f"--since={start.isoformat()}", "--date=short",
            "--format=%H %ad", "--", rec["path"]).splitlines() if l.strip()]
        shas.reverse()
        if len(shas) > TREND_POINTS:
            step = (len(shas) - 1) / (TREND_POINTS - 1)
            shas = [shas[round(i * step)] for i in range(TREND_POINTS)]
        trend = []
        for sha, date in shas:
            blob = subprocess.run(["git", "-C", repo, "show", f"{sha}:{rec['path']}"],
                                  capture_output=True, text=True, errors="replace")
            if blob.returncode == 0:
                loc, cx, _ = measure(blob.stdout)
                trend.append({"date": date, "loc": loc, "complexity": cx})
        rec["trend"] = trend
        if len(trend) >= 2 and trend[0]["complexity"]:
            rec["complexity_change"] = round(trend[-1]["complexity"] / trend[0]["complexity"] - 1, 2)

    # Change coupling: pairs that keep changing in the same commit.
    coupling = []
    for (a, b), shared in pair_counts.items():
        if shared < 5:
            continue
        ra, rb = files[a]["revisions"], files[b]["revisions"]
        degree = shared / ((ra + rb) / 2)
        if degree >= 0.4:
            coupling.append({"a": a, "b": b, "shared_commits": shared, "degree": round(degree, 2),
                             "same_directory": os.path.dirname(a) == os.path.dirname(b)})
    coupling.sort(key=lambda c: (c["same_directory"], -c["shared_commits"] * c["degree"]))
    coupling = coupling[:20]

    # Directory rollup (first two path segments).
    dirs = collections.defaultdict(lambda: {"files": 0, "loc": 0, "revisions": 0, "score": 0.0})
    for r in rows:
        seg = r["path"].split("/")
        key = "/".join(seg[:2]) if len(seg) > 2 else (seg[0] if len(seg) > 1 else "(root)")
        d = dirs[key]
        d["files"] += 1
        d["loc"] += r["loc"]
        d["revisions"] += r["revisions"]
        d["score"] += r["score"]
    directories = sorted(({"path": k, **v, "score": round(v["score"], 3)} for k, v in dirs.items()),
                         key=lambda d: -d["score"])[:25]

    # Files for the map: the biggest ones plus everything that scores.
    keep = {r["path"] for r in sorted(rows, key=lambda r: -r["loc"])[:MAP_FILES]}
    keep |= {r["path"] for r in rows[:150]}
    map_files = [{k: r[k] for k in ("path", "loc", "complexity", "revisions", "score", "rank")}
                 for r in rows if r["path"] in keep]

    slim = ("path", "rank", "score", "revisions", "change_share", "fixes", "loc", "complexity", "max_depth",
            "authors", "main_author_share", "is_test", "trend", "complexity_change")
    result = {
        "head": head_sha,
        "remote": git(repo, "config", "--get", "remote.origin.url").strip(),
        "window": {"from": start.isoformat(), "to": end.isoformat(), "months": args.months},
        "commits_in_window": commits,
        "files_analysed": len(rows),
        "files_untouched_in_window": untouched,
        "test_files_excluded": skipped_tests,
        "total_loc": sum(r["loc"] for r in rows),
        "max_revisions": max_rev,
        "max_complexity": max_cx,
        "concentration": concentration,
        "hotspots": [{k: r[k] for k in slim if k in r} for r in rows[:40] if r["revisions"] > 0],
        "coupling": coupling,
        "directories": directories,
        "map_files": map_files,
        "map_files_omitted": len(rows) - len(map_files),
    }
    json.dump(result, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
