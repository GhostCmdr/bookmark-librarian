# bookmark-librarian

Merge bookmark exports from several browsers into one deduplicated file, keeping a
designated master source intact. Pure Python 3 standard library — no dependencies, no
network, runs on Windows / macOS / Linux.

## What it does

- Reads Netscape Bookmark HTML — the format every browser exports
- Dedupes by exact URL, and keeps the master's copy, order, titles, icons and dates
- Routes the rest by a **folder map**: folders that mean the same thing merge into one,
  same-name folders merge level by level, everything else is flattened to the end of the toolbar
- **Learns** — your answers about folder grouping are remembered, so it never asks twice
- **Chinese or English** — `--lang zh|en` changes the wording, nothing else
- Writes one merged file and prints two tables (counts, duplicate detail)

## Install

```
npx skills add GhostCmdr/bookmark-librarian
```

It follows the [Agent Skills](https://agentskills.io/specification) open format, so the same
folder works across agents — the `skills` CLI detects which ones you have and wires it up.

To install by hand, clone into the folder your agent reads, keeping the name
`bookmark-librarian`:

| Agent | Path |
| --- | --- |
| Any Agent Skills client | `.agents/skills/bookmark-librarian/` |
| Claude Code | `~/.claude/skills/bookmark-librarian/` |
| TraeCode | `.trae/skills/bookmark-librarian/` (project) · `~/.trae-cn/skills/bookmark-librarian/` (global) |
| Cursor | `.cursor/rules/bookmark-librarian.mdc` |
| Any other / unsure | paste `SKILL.md` into `AGENTS.md` |

## Usage

```
python3 scripts/merge.py --master Edge Edge=favorites.html Chrome=bookmarks.html
python3 scripts/tables.py merge_stats.json 合并书签_Edge_Chrome.html
```

- `--master <name>` — which source wins. Omit it for no-master mode (all sources equal,
  full folder structure kept)
- `--out <dir>` — where the merged file goes. Defaults to your desktop
- `--dry-run` — print the routing plan and the ask list, write nothing
- `--lang zh|en` — the wording of everything printed. Defaults to `zh`
- One source only → in-file dedupe only
- Compare two exports without merging: `python3 scripts/diff.py A.html Edge B.html Chrome`

The merged file is the only deliverable; the tables are printed to the chat.

Folder grouping is data, not code: `scripts/folder-map.json` ships the defaults and
`~/.bookmark-librarian/folder-map.json` remembers what you taught. See `SKILL.md` for the
full rules, and `examples/` for a runnable sample.

## Tests

```
python3 tests/test_bookmark_librarian.py
```

## License

MIT — see [LICENSE](LICENSE).
