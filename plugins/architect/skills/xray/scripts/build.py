#!/usr/bin/env python3
"""Validate an X-ray data file and render it into a self-contained HTML page.

Usage: build.py <xray.json> <output.html>

Exits non-zero with a list of problems if the data does not match the schema
described in references/report-schema.md.
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
BROWSERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
)
CONFIDENCE = {"documented", "inferred", "speculative"}
LEVELS = {"Context", "Container", "Component", "Flow", "Data", "Deployment"}
DIAGRAM_KINDS = ("flowchart", "graph", "sequenceDiagram", "erDiagram", "classDiagram", "stateDiagram")


def check(data):
    errors, warnings = [], []

    def need(obj, key, kind, where):
        v = obj.get(key) if isinstance(obj, dict) else None
        if not isinstance(v, kind) or (isinstance(v, (str, list)) and not v):
            errors.append(f"{where}.{key}: required {kind.__name__}")
            return None
        return v

    meta = need(data, "meta", dict, "root") or {}
    for k in ("name", "tagline", "commit", "analysed_at"):
        need(meta, k, str, "meta")
    need(data, "thesis", str, "root")
    hook = meta.get("hook")
    if hook is not None and (not isinstance(hook, str) or len(hook) > 110):
        errors.append("meta.hook: optional string of at most 110 characters")
    site = meta.get("site_url")
    if site is not None and not (isinstance(site, str) and site.startswith("https://")):
        errors.append("meta.site_url: optional, must start with https://")
    elif not site:
        warnings.append("meta.site_url not set: link previews need the page's public URL to find the card image")

    for i, s in enumerate(need(data, "stats", list, "root") or []):
        need(s, "label", str, f"stats[{i}]")
        need(s, "value", str, f"stats[{i}]")

    for i, p in enumerate(need(data, "patterns", list, "root") or []):
        need(p, "name", str, f"patterns[{i}]")
        need(p, "summary", str, f"patterns[{i}]")
        if not p.get("evidence"):
            warnings.append(f"patterns[{i}] ({p.get('name')}): no evidence listed")

    diagrams = need(data, "diagrams", list, "root") or []
    for i, d in enumerate(diagrams):
        w = f"diagrams[{i}]"
        need(d, "title", str, w)
        if d.get("level") not in LEVELS:
            errors.append(f"{w}.level: one of {sorted(LEVELS)}")
        code = need(d, "mermaid", str, w) or ""
        first = code.strip().split(None, 1)[0] if code.strip() else ""
        if not first.startswith(DIAGRAM_KINDS):
            errors.append(f"{w}.mermaid: must start with one of {DIAGRAM_KINDS}, got '{first}'")
        if code.count('"') % 2:
            errors.append(f"{w}.mermaid: unbalanced double quotes")
        if first.startswith(("flowchart", "graph")):
            opens = len(re.findall(r"^\s*subgraph\b", code, re.M))
            ends = len(re.findall(r"^\s*end\s*$", code, re.M))
            if opens != ends:
                errors.append(f"{w}.mermaid: {opens} subgraph vs {ends} end")
            if "classDef" in code:
                warnings.append(f"{w}.mermaid: classDef is supplied by the template; remove it")
    if not any(d.get("level") == "Container" for d in diagrams):
        errors.append("diagrams: a Container-level diagram is required")

    for i, m in enumerate(data.get("modules", [])):
        need(m, "path", str, f"modules[{i}]")
        need(m, "role", str, f"modules[{i}]")

    decisions = need(data, "decisions", list, "root") or []
    for i, d in enumerate(decisions):
        w = f"decisions[{i}]"
        for k in ("title", "decision", "why", "tradeoff"):
            need(d, k, str, w)
        if d.get("confidence") not in CONFIDENCE:
            errors.append(f"{w}.confidence: one of {sorted(CONFIDENCE)}")
        ev = d.get("evidence") or []
        if not ev:
            errors.append(f"{w}: at least one evidence item is required")
        if d.get("confidence") == "documented" and not any(
            isinstance(e, dict) and e.get("url") for e in ev
        ):
            warnings.append(f"{w}: 'documented' but no evidence item has a url")

    for i, e in enumerate(need(data, "evolution", list, "root") or []):
        w = f"evolution[{i}]"
        for k in ("period", "title", "summary"):
            need(e, k, str, w)
        if not e.get("evidence"):
            warnings.append(f"{w} ({e.get('title')}): no evidence listed")

    a = need(data, "assessment", dict, "root") or {}
    for side in ("strengths", "risks"):
        for i, s in enumerate(need(a, side, list, "assessment") or []):
            need(s, "title", str, f"assessment.{side}[{i}]")
            need(s, "detail", str, f"assessment.{side}[{i}]")

    def urls(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "url" and isinstance(v, str) and v and not v.startswith("https://"):
                    errors.append(f"url must start with https://: {v[:80]}")
                else:
                    urls(v)
        elif isinstance(node, list):
            for v in node:
                urls(v)

    urls(data)
    return errors, warnings


def plain(text):
    """Strip the backtick code markers used in the data file."""
    return str(text or "").replace("`", "")


def find_browser():
    for candidate in BROWSERS:
        path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if path and os.path.exists(path):
            return path
    return None


def write_card(data, out_dir):
    """Render the 1200x630 share card. Returns the PNG path, or None if no browser is available."""
    meta = data["meta"]
    name = plain(meta["name"])
    size = 124 if len(name) <= 12 else 100 if len(name) <= 18 else 78 if len(name) <= 26 else 60
    repo = re.sub(r"^https://", "", meta.get("url") or "")
    stats = "".join(
        f"<div class=\"stat\"><b>{html.escape(plain(s['value']))}</b>"
        f"<span class=\"mono\">{html.escape(plain(s['label']))}</span></div>"
        for s in data["stats"][:4]
    )
    with open(CARD_TEMPLATE, encoding="utf-8") as f:
        card = f.read()
    for key, value in {
        "__CARD_NAME_SIZE__": str(size),
        "__CARD_NAME__": html.escape(name),
        "__CARD_REPO__": html.escape(repo),
        "__CARD_HOOK__": html.escape(plain(meta.get("hook") or meta["tagline"])),
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
    profile = tempfile.mkdtemp(prefix="xray-card-")
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


def head_tags(data, has_card):
    """Static link-preview tags. Crawlers do not run scripts, so these cannot come from the page's JS."""
    meta = data["meta"]
    title = f"{plain(meta['name'])} - Architecture X-ray"
    desc = plain(meta.get("hook") or meta["tagline"])
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
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    errors, warnings = check(data)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    card = write_card(data, out_dir)

    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = re.sub(r"[<>&]", "", data["meta"]["name"])
    page = (page.replace("__XRAY_TITLE__", title)
                .replace("__XRAY_HEAD__", head_tags(data, card is not None))
                .replace("__XRAY_DATA__", payload))
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {out} ({len(page) // 1024} KB, {len(data['diagrams'])} diagrams, "
          f"{len(data['decisions'])} decisions, {len(data['evolution'])} eras)")
    if card:
        print(f"wrote {card} ({CARD_SIZE[0]}x{CARD_SIZE[1]} share card)")


if __name__ == "__main__":
    main()
