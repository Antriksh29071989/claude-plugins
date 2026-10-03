#!/usr/bin/env python3
"""Validate a hotspot report against its metrics and render the page and share card.

Usage: build.py <report.json> <metrics.json> <output.html>

report.json is the written analysis (see references/report-schema.md);
metrics.json is the unmodified output of analyze.py. Every number on the page
comes from the metrics file.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
TEMPLATE = os.path.join(ASSETS, "template.html")
CARD_TEMPLATE = os.path.join(ASSETS, "card-template.html")
CARD_SIZE = (1200, 630)
EFFORT = {"S", "M", "L"}
BROWSERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
)


def check(report, metrics):
    errors, warnings = [], []

    def need(obj, key, kind, where):
        v = obj.get(key) if isinstance(obj, dict) else None
        if not isinstance(v, kind) or (isinstance(v, (str, list)) and not v):
            errors.append(f"{where}.{key}: required {kind.__name__}")
            return None
        return v

    for key in ("head", "window", "hotspots", "map_files", "concentration", "commits_in_window"):
        if key not in metrics:
            errors.append(f"metrics.{key} missing: pass the unmodified output of analyze.py")
    if errors:
        return errors, warnings

    meta = need(report, "meta", dict, "report") or {}
    for k in ("name", "analysed_at"):
        need(meta, k, str, "meta")
    hook = meta.get("hook")
    if hook is not None and (not isinstance(hook, str) or len(hook) > 110):
        errors.append("meta.hook: optional string of at most 110 characters")
    site = meta.get("site_url")
    if site is not None and not (isinstance(site, str) and site.startswith("https://")):
        errors.append("meta.site_url: optional, must start with https://")
    elif not site:
        warnings.append("meta.site_url not set: link previews need the page's public URL to find the card image")
    url = meta.get("url")
    if url is not None and not (isinstance(url, str) and url.startswith("https://")):
        errors.append("meta.url: must start with https://")
    need(report, "thesis", str, "report")

    findings = need(report, "findings", list, "report") or []
    if not 3 <= len(findings) <= 6:
        errors.append("findings: 3 to 6 items")
    for i, f in enumerate(findings):
        need(f, "title", str, f"findings[{i}]")
        need(f, "detail", str, f"findings[{i}]")

    known = {h["path"] for h in metrics["hotspots"]}
    top10 = [h["path"] for h in metrics["hotspots"][:10]]
    diagnoses = need(report, "diagnoses", list, "report") or []
    seen = set()
    for i, d in enumerate(diagnoses):
        w = f"diagnoses[{i}]"
        path = need(d, "path", str, w)
        if path and path not in known:
            errors.append(f"{w}.path: '{path}' is not in the metrics hotspot list")
        if path in seen:
            errors.append(f"{w}.path: duplicate")
        seen.add(path)
        for k in ("role", "why_hot", "recommendation"):
            need(d, k, str, w)
        if d.get("effort") not in EFFORT:
            errors.append(f"{w}.effort: one of {sorted(EFFORT)}")
        if not d.get("evidence"):
            errors.append(f"{w}: at least one evidence item (what you read that supports the diagnosis)")
    if len(diagnoses) < 5:
        errors.append("diagnoses: at least 5")
    missing = [p for p in top10[:5] if p not in seen]
    if missing:
        errors.append(f"diagnoses: the top 5 hotspots must each be diagnosed; missing {missing}")

    pairs = {frozenset((c["a"], c["b"])) for c in metrics.get("coupling", [])}
    for i, c in enumerate(report.get("coupling_notes", [])):
        w = f"coupling_notes[{i}]"
        if frozenset((c.get("a"), c.get("b"))) not in pairs:
            errors.append(f"{w}: pair is not in the metrics coupling list")
        need(c, "explanation", str, w)

    plan = need(report, "plan", list, "report") or []
    if not 3 <= len(plan) <= 7:
        errors.append("plan: 3 to 7 ordered steps")
    return errors, warnings


def plain(text):
    return str(text or "").replace("`", "")


def find_browser():
    for candidate in BROWSERS:
        path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if path and os.path.exists(path):
            return path
    return None


def card_stats(metrics):
    c5 = next((c for c in metrics["concentration"] if c["top_files_pct"] == 5), metrics["concentration"][0])
    return [
        (f"{round(c5['share_of_changes'] * 100)}%", f"of changes in {c5['top_files_pct']}% of files"),
        (f"{metrics['commits_in_window']:,}", f"commits, {metrics['window']['months']} months"),
        (f"{metrics['files_analysed']:,}", "source files"),
        (f"{metrics['total_loc']:,}", "lines of code"),
    ]


def write_card(report, metrics, out_dir):
    """Render the 1200x630 share card. Returns the PNG path, or None if no browser is available."""
    meta = report["meta"]
    name = plain(meta["name"])
    size = 124 if len(name) <= 12 else 100 if len(name) <= 18 else 78 if len(name) <= 26 else 60
    repo = re.sub(r"^https://", "", meta.get("url") or "")
    stats = "".join(
        f'<div class="stat"><b>{html.escape(v)}</b><span class="mono">{html.escape(l)}</span></div>'
        for v, l in card_stats(metrics)
    )
    with open(CARD_TEMPLATE, encoding="utf-8") as f:
        card = f.read()
    for key, value in {
        "__CARD_NAME_SIZE__": str(size),
        "__CARD_NAME__": html.escape(name),
        "__CARD_REPO__": html.escape(repo),
        "__CARD_HOOK__": html.escape(plain(meta.get("hook") or report["thesis"])[:160]),
        "__CARD_STATS__": stats,
    }.items():
        card = card.replace(key, value)
    card_html = os.path.join(out_dir, "card.html")
    card_png = os.path.join(out_dir, "card.png")
    with open(card_html, "w", encoding="utf-8") as f:
        f.write(card)

    browser = find_browser()
    if not browser:
        print("warning: no Chrome-family browser found; card.html written but card.png was not rendered",
              file=sys.stderr)
        return None
    if os.path.exists(card_png):
        os.remove(card_png)
    profile = tempfile.mkdtemp(prefix="hotspots-card-")
    proc = subprocess.Popen(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
         "--force-device-scale-factor=1", f"--user-data-dir={profile}",
         f"--window-size={CARD_SIZE[0]},{CARD_SIZE[1]}", f"--screenshot={card_png}",
         "file://" + os.path.abspath(card_html)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Headless Chrome does not always exit after a screenshot, so wait for the file, not the process.
    deadline = time.time() + 40
    while time.time() < deadline and not (os.path.exists(card_png) and os.path.getsize(card_png) > 0):
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    time.sleep(0.5)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    shutil.rmtree(profile, ignore_errors=True)
    if os.path.exists(card_png) and os.path.getsize(card_png) > 0:
        return card_png
    print("warning: the browser did not produce card.png", file=sys.stderr)
    return None


def head_tags(report, has_card):
    """Static link-preview tags. Crawlers do not run scripts, so these cannot come from the page's JS."""
    meta = report["meta"]
    title = f"{plain(meta['name'])} - Tech-debt hotspot map"
    desc = plain(meta.get("hook") or report["thesis"])[:200]
    site = (meta.get("site_url") or "").rstrip("/")
    tags = [
        ("name", "description", desc),
        ("property", "og:type", "article"),
        ("property", "og:title", title),
        ("property", "og:description", desc),
        ("name", "twitter:title", title),
        ("name", "twitter:description", desc),
    ]
    if site:
        tags.append(("property", "og:url", site + "/"))
    if has_card:
        image = f"{site}/card.png" if site else "card.png"
        tags += [
            ("property", "og:image", image),
            ("property", "og:image:width", str(CARD_SIZE[0])),
            ("property", "og:image:height", str(CARD_SIZE[1])),
            ("property", "og:image:alt", f"{title}: {desc}"),
            ("name", "twitter:card", "summary_large_image"),
            ("name", "twitter:image", image),
        ]
    return "\n".join(
        f'<meta {kind}="{key}" content="{html.escape(value, quote=True)}">' for kind, key, value in tags
    )


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    report_path, metrics_path, out = sys.argv[1:]
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)
    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)
    errors, warnings = check(report, metrics)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    card = write_card(report, metrics, out_dir)

    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    payload = json.dumps({"report": report, "metrics": metrics}, ensure_ascii=False).replace("</", "<\\/")
    title = re.sub(r"[<>&]", "", report["meta"]["name"])
    page = (page.replace("__HS_TITLE__", title)
                .replace("__HS_HEAD__", head_tags(report, card is not None))
                .replace("__HS_DATA__", payload))
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {out} ({len(page) // 1024} KB, {len(report['diagnoses'])} diagnoses, "
          f"{len(metrics['map_files'])} files on the map)")
    if card:
        print(f"wrote {card} ({CARD_SIZE[0]}x{CARD_SIZE[1]} share card)")


if __name__ == "__main__":
    main()
