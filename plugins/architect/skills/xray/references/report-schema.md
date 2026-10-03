# X-ray data file

`xray.json` is the only thing you write. `scripts/build.py` validates it and renders `assets/template.html` into the final page.

## Text rules

- Plain text only. HTML in any field is shown literally, not rendered.
- Wrap identifiers and file paths in backticks to render them as inline code.
- `url` values must start with `https://`. Link to a file or commit at the analysed commit where possible, e.g. `https://github.com/<owner>/<repo>/blob/<sha>/path/to/file.py`.
- Keep `summary`, `why` and `detail` fields to one to three sentences.

## Structure

```json
{
  "meta": {
    "name": "project-name",
    "url": "https://github.com/owner/project-name",
    "tagline": "What it is, in one line.",
    "hook": "The single most interesting finding, as a headline of at most 110 characters.",
    "site_url": "https://<user>.github.io/<repo>/xray/project-name/",
    "commit": "full or short HEAD sha",
    "analysed_at": "YYYY-MM-DD"
  },
  "thesis": "Two or three sentences: the central architectural idea and the trade it makes.",
  "stats": [
    { "label": "First commit", "value": "2010" },
    { "label": "Commits", "value": "5,412" },
    { "label": "Contributors", "value": "830" },
    { "label": "Primary language", "value": "Python" },
    { "label": "Tracked files", "value": "312" },
    { "label": "Releases", "value": "58 tags" }
  ],
  "patterns": [
    {
      "name": "Microkernel with extensions",
      "kind": "style",
      "summary": "A small core defines hooks; features arrive as extensions that register against them.",
      "evidence": [
        { "label": "src/app.py: extension registry", "url": "https://github.com/..." },
        "src/signals.py"
      ]
    }
  ],
  "diagrams": [
    {
      "level": "Context",
      "title": "Where it sits",
      "caption": "One sentence saying what to notice.",
      "mermaid": "flowchart TB\n  dev([\"Developer\"]):::person --> app[\"project-name<br/>WSGI framework\"]:::system\n"
    }
  ],
  "modules": [
    { "path": "src/project/app.py", "role": "Application object and request dispatch", "notes": "Most-changed file in the repository" }
  ],
  "decisions": [
    {
      "title": "Short name of the decision",
      "decision": "What was chosen, concretely.",
      "why": "The reasoning.",
      "tradeoff": "What it cost or ruled out.",
      "alternatives": "What was rejected (optional).",
      "when": "2011, v0.7 (optional)",
      "confidence": "documented",
      "evidence": [ { "label": "docs/design.rst", "url": "https://github.com/..." } ]
    }
  ],
  "evolution": [
    {
      "period": "2010 - 2011",
      "title": "Single-file origins",
      "summary": "What the architecture looked like and what changed.",
      "changes": [ "Structural change one", "Structural change two" ],
      "why": "What drove it. Say 'inferred' in the sentence if undocumented.",
      "evidence": [ { "label": "tag 0.7 (2011-06-28)" }, { "label": "commit abc1234", "url": "https://github.com/..." } ]
    }
  ],
  "assessment": {
    "strengths": [ { "title": "Short claim", "detail": "What makes it true, tied to something observable." } ],
    "risks": [ { "title": "Short claim", "detail": "The cost, and where it shows." } ]
  },
  "takeaways": [ "A lesson another team could apply." ],
  "method": {
    "scope": "What was read and how (for example: full history via blobless clone; core packages X and Y read in full; Z skimmed).",
    "limits": [ "Areas not examined.", "Claims that could not be verified." ]
  }
}
```

Field notes:

| Field | Rule |
|---|---|
| `meta.hook` | Optional. Headline for the share card and link preview; falls back to `tagline`. Lead with the finding, not a description of the project |
| `meta.site_url` | Optional. The public URL the page will be served from. Link previews need it to locate the card image; leave it out if the page will not be published |
| `stats` | 4-8 items; the first four appear on the share card, values as short strings, taken from `history.json` or commands you ran |
| `patterns[].kind` | `style`, `pattern` or `principle` |
| `diagrams[].level` | `Context`, `Container`, `Component`, `Flow`, `Data` or `Deployment`; at least one `Container` |
| `decisions[].confidence` | `documented`, `inferred` or `speculative`; `documented` needs an evidence item with a `url` |
| `decisions[].evidence` | At least one item |
| `evidence` items | Either a string or `{ "label": "...", "url": "https://..." }` |
| `modules` | Optional; 6-15 rows |
| `evolution` | 4-8 eras, oldest first |

## Diagrams

Diagrams are Mermaid source in a JSON string (`\n` for newlines, `\"` for quotes). The build accepts `flowchart`, `sequenceDiagram`, `erDiagram`, `classDiagram` and `stateDiagram`.

### Structure views: `flowchart`

Use `flowchart TB` (or `LR` for pipelines) for Context, Container, Component and Deployment views. The template supplies the colours; attach one of these classes to every node and do not write `classDef` or `style` lines yourself:

| Class | Use for | Suggested shape |
|---|---|---|
| `person` | Users and operators | `id(["Name"])` |
| `system` | The system or its main parts (containers, packages) | `id["Name"]` |
| `component` | Parts inside a container | `id["Name"]` |
| `store` | Databases, caches, files, object stores | `id[("Name")]` |
| `queue` | Queues, logs, streams, buses | `id[["Name"]]` |
| `external` | Anything outside the project | `id["Name"]` |

Rules that prevent render failures:

- Every label in double quotes. No double quotes inside a label; use single quotes if needed.
- Two lines per node at most: `"Name<br/>technology or role"`. `<br/>` is the only markup allowed.
- Node ids are plain identifiers (`letters_digits`). Do not use `end`, `graph`, `subgraph`, `class` or `style` as ids.
- Label every edge with what flows or why: `a -->|"parses into"| b`. Use `-.->` for asynchronous or optional paths.
- Group with `subgraph id["Title"]` ... `end`; every `subgraph` needs its own `end` line.
- Avoid `(`, `)`, `{`, `}`, `#` and `;` inside edge labels.

```
flowchart TB
  user(["Application developer"]):::person
  subgraph fw["project-name"]
    app["Application object<br/>routing and dispatch"]:::system
    ctx["Context stack<br/>request and app state"]:::component
    ext["Extension registry<br/>hooks and signals"]:::component
  end
  wsgi["WSGI server<br/>gunicorn, uWSGI"]:::external
  db[("Application database")]:::store
  user -->|"builds apps with"| app
  wsgi -->|"calls with each request"| app
  app -->|"pushes"| ctx
  app -->|"fires hooks on"| ext
  ext -.->|"extensions connect to"| db
```

### Flow views: `sequenceDiagram`

Participants are elements that appear in the structure views, with the same names.

```
sequenceDiagram
  participant S as WSGI server
  participant A as Application object
  participant R as Router
  participant V as View function
  S->>A: call with environ
  A->>R: match URL
  R-->>A: endpoint and arguments
  A->>V: dispatch
  V-->>A: return value
  A-->>S: response iterable
  Note over A,V: Hooks run before and after dispatch
```

Rules: no semicolons or `#` in message text; keep messages short; `-)` for asynchronous sends; at most about 8 participants.

### Data views: `erDiagram` or `classDiagram`

Only when a schema or a core type hierarchy is itself one of the key decisions.
