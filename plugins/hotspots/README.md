# hotspots

A Claude Code plugin that turns "we have tech debt" into a ranked, evidenced list of what to fix first.

```
/hotspots:map https://github.com/google-gemini/gemini-cli
/hotspots:map . --months 6
```

Example: [gemini-cli hotspot map](https://antriksh29071989.github.io/claude-plugins/hotspots/gemini-cli/).

## What you get

`hotspots/<project>/index.html`, one self-contained page:

- **How concentrated change is** - for example "38% of all changes land in 5% of files".
- **A heat map of the codebase** - every source file as a rectangle, sized by lines of code and coloured by hotspot score.
- **The top hotspots, diagnosed** - what each file is, why it keeps changing, one specific refactoring, a first step, an effort rating, and the evidence. Each has a complexity trend line.
- **Churn against complexity** - a scatter plot of every file.
- **Files that change together** - pairs that keep landing in the same commit, with what links them.
- **The ranking as a table**, and **an ordered plan**.
- `card.png`, a 1200x630 share card, with link-preview tags in the page.

## How it works

1. [`analyze.py`](skills/map/scripts/analyze.py) measures the repository: commits per file in the window, indentation complexity, fix-style commits, author counts, complexity trends and change coupling. It writes `metrics.json`.
2. Claude reads the top-scoring files and their history and writes `report.json`: the diagnoses and the plan.
3. [`build.py`](skills/map/scripts/build.py) checks the report against the metrics and renders the page. Every number on the page comes from `metrics.json`, not from the model.

The scoring follows Adam Tornhill's hotspot analysis (*Your Code as a Crime Scene*):

```
score = (commits touching the file / most for any file) x (complexity / highest for any file)
```

You can run the measurement on its own, with no AI involved:

```
python3 skills/map/scripts/analyze.py /path/to/repo --months 12 > metrics.json
```

## Limits

- Complexity is indentation-based: language-neutral and fast, but a proxy. Deeply nested data literals score high.
- Fix counts come from commit-subject keywords.
- Test, generated and vendored files are excluded by path patterns, which can miss unusual layouts.
- A high score means a file is worth a look, not that it is badly written. The diagnoses are an AI reading of the code; check them before acting on or publishing them.
- Author identities are counted, never output.

Requires `git` and `python3`. The share card needs Chrome, Chromium, Edge or Brave. The page itself has no external dependencies and works offline.
