# claude-plugins

Personal collection of Claude Code plugins.

## Plugins

| Plugin | Description |
|---|---|
| [architect](plugins/architect) | Architecture toolkit: `/architect:design` proposes and compares designs for a problem; `/architect:xray` turns any repository into an HTML architecture case study. |

## Install

Add this repository as a marketplace, then install a plugin from it:

```
/plugin marketplace add /path/to/claude-plugins
/plugin install architect@antriksh-plugins
```

To try a plugin without installing it:

```
claude --plugin-dir ./plugins/architect
```

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest listing every plugin
plugins/<name>/
  .claude-plugin/plugin.json      # plugin manifest
  skills/<skill>/SKILL.md         # skills (also invocable as /<name>:<skill>)
  agents/<agent>.md               # subagents
  README.md
```

## Adding a plugin

1. Create `plugins/<name>/` with a `.claude-plugin/plugin.json`.
2. Add an entry to `.claude-plugin/marketplace.json`.
3. Run `claude plugin validate .` from the repository root.
