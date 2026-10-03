# architect

A Claude Code plugin with two architecture skills:

- **`/architect:xray`** - point it at any repository and get an HTML case study of how it is architected, why, and how it got there.
- **`/architect:design`** - give it a problem and get 2-3 contrasting designs with C4 diagrams, a trade-off analysis and a recommendation.

## /architect:xray

```
/architect:xray https://github.com/pallets/flask
/architect:xray ./path/to/local/repo
```

Example: [gemini-cli, X-rayed](https://antriksh29071989.github.io/claude-plugins/xray/gemini-cli/).

It clones the repository (history only, no file contents until needed), measures its git history, reads the code, and produces `xray/<project>/index.html`: one self-contained page with

- the architecture style and patterns in use, each with the files that show it;
- C4-style diagrams: context, containers, key components, and one traced flow;
- a module map;
- the key design decisions - what was chosen, why, the trade-off - each marked **documented** (the maintainers said so, with a link), **inferred** (read from code and history) or **speculative**;
- a timeline of how the architecture evolved and what drove each turning point;
- strengths, risks and transferable lessons.

Each build also produces `card.png`, a 1200x630 share card, and the page carries link-preview tags pointing at it, so a published X-ray unfurls with an image when shared.

How it works: Claude writes a structured `xray.json`; `scripts/build.py` validates it and renders it through `assets/template.html`. Every X-ray therefore looks the same, and the analysis can be re-rendered without re-running it.

Notes:

- The page loads the Mermaid diagram renderer from a CDN, so diagrams need an internet connection the first time the page is opened. Without it the diagram source is shown instead.
- Light and dark themes follow the viewer's system setting.
- Requires `git` and `python3`. The share card needs Chrome, Chromium, Edge or Brave installed. The GitHub CLI (`gh`) is used for pull-request and issue context if present.
- Claims about *why* a decision was made are only as good as the evidence. Check the **inferred** ones before publishing about someone else's project.

## /architect:design

```
/architect:design design a notification service for 5M daily users across push, email and SMS
```

It frames the problem, sizes it, ranks the architecture drivers, applies the architecture literature, researches how large engineering organisations solved the same problem, and writes to `docs/architecture/<problem-slug>/`:

- `README.md` - summary, comparison matrix, recommendation, risks, sources
- `option-<n>-<name>.md` - one per design, with C4 diagrams and analysis of latency, scalability, availability, consistency, cost, failure modes, security and evolution
- `adr-0001-<decision>.md` - the decision record

Notes:

- The books are not bundled. The plugin carries a map of what each is authoritative on, and the model applies them from its own knowledge; chapter-level citations should be spot-checked.
- Industry research needs web access. Without it, precedents are labelled as unverified.
- Cost figures are estimates with stated assumptions, not quotes.

## Contents

| Path | Purpose |
|---|---|
| `skills/xray/SKILL.md` | The X-ray workflow |
| `skills/xray/scripts/history.py` | Summarises git history as JSON (eras, tags, directory lifetimes, large commits) |
| `skills/xray/scripts/build.py` | Validates `xray.json` and renders the page |
| `skills/xray/assets/template.html` | Page template and diagram theme |
| `skills/xray/assets/card-template.html` | Share card layout |
| `skills/xray/references/report-schema.md` | Data file format and diagram rules |
| `skills/design/SKILL.md` | The design workflow |
| `skills/design/references/` | Literature map, industry precedents, quality attributes, C4 guide, output template |
| `agents/industry-researcher.md` | Subagent for precedent research |
