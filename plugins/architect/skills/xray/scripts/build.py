#!/usr/bin/env python3
"""Validate an X-ray data file and render it into a self-contained HTML page.

Usage: build.py <xray.json> <output.html>

Exits non-zero with a list of problems if the data does not match the schema
described in references/report-schema.md.
"""
import json
import os
import re
import sys

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "template.html")
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

    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = re.sub(r"[<>&]", "", data["meta"]["name"])
    html = html.replace("__XRAY_TITLE__", title).replace("__XRAY_DATA__", payload)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out} ({len(html) // 1024} KB, {len(data['diagrams'])} diagrams, "
          f"{len(data['decisions'])} decisions, {len(data['evolution'])} eras)")


if __name__ == "__main__":
    main()
