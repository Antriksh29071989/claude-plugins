# Hotspot report file

`report.json` holds the written analysis. `scripts/build.py` validates it against `metrics.json` and renders the page. All numbers, the heat map, the scatter plot, the table and the stat tiles are drawn from `metrics.json`; the report supplies only the words.

## Text rules

- Plain text only. HTML is shown literally.
- Backticks render as inline code: use them for file names and identifiers.
- One to three sentences per field.

## Structure

```json
{
  "meta": {
    "name": "project-name",
    "url": "https://github.com/owner/project-name",
    "analysed_at": "YYYY-MM-DD",
    "hook": "The most striking measured finding, as a headline of at most 110 characters.",
    "site_url": "https://<user>.github.io/<repo>/hotspots/project-name/"
  },
  "thesis": "Two or three sentences: how concentrated change is, where the heat sits, and whether it is getting worse.",
  "findings": [
    { "title": "Short claim", "detail": "The numbers behind it, from metrics.json." }
  ],
  "diagnoses": [
    {
      "path": "src/exact/path/from/metrics.ts",
      "role": "What the file is for, in one sentence.",
      "why_hot": "The mechanism that makes it change so often and be hard to change.",
      "recommendation": "One specific refactoring that removes that mechanism.",
      "first_step": "A concrete step small enough to start this sprint.",
      "risk_if_ignored": "What gets worse if nothing is done.",
      "effort": "S",
      "evidence": [
        "126 of its 229 commits are typed feat",
        "Sample fix: 'exact commit subject'"
      ]
    }
  ],
  "coupling_notes": [
    {
      "a": "path/one.ts",
      "b": "path/two.ts",
      "explanation": "What links the two files.",
      "action": "What would break the link."
    }
  ],
  "plan": [
    "First step: the cheapest high-value fix.",
    "Second step."
  ],
  "method": {
    "scope": "Window, commit analysed, and what you read.",
    "limits": [ "Anything odd in the ranking, anything you could not examine." ]
  }
}
```

## Rules the build enforces

| Field | Rule |
|---|---|
| `meta.name`, `meta.analysed_at`, `thesis` | Required |
| `meta.url`, `meta.site_url` | Optional; must start with `https://` |
| `meta.hook` | Optional; at most 110 characters; shown on the share card |
| `findings` | 3 to 6 items, each with `title` and `detail` |
| `diagnoses` | At least 5; must include each of the top 5 hotspots in `metrics.json` |
| `diagnoses[].path` | Must match a path in `metrics.hotspots` exactly; no duplicates |
| `diagnoses[].effort` | `S`, `M` or `L` |
| `diagnoses[].evidence` | At least one item |
| `coupling_notes[]` | Optional; the pair must exist in `metrics.coupling` |
| `plan` | 3 to 7 ordered steps |

`role`, `why_hot` and `recommendation` are required on every diagnosis; `first_step` and `risk_if_ignored` are optional but expected.

## What the metrics mean

| Metric | Definition |
|---|---|
| `revisions` | Non-merge commits touching the file inside the window |
| `complexity` | Indentation complexity: the sum of every non-blank line's nesting depth |
| `score` | `(revisions / max revisions) x (complexity / max complexity)` |
| `change_share` | `revisions` divided by all commits in the window |
| `fixes` | Commits whose subject matches fix, bug, hotfix, regression, revert, crash, broken or incorrect |
| `authors` | Distinct author emails that touched the file in the window (a count; identities are never output) |
| `complexity_change` | Relative change in complexity between the first and last sampled revision in the window |
| `coupling.degree` | Shared commits divided by the pair's average `revisions`; commits touching more than 30 source files are ignored |
| `concentration` | Share of all file changes that land in the busiest 1%, 5%, 10% and 20% of files |
