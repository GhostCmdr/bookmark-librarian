# bookmark-librarian

Merge bookmark exports from several browsers into a single deduplicated file, keeping a
designated master source intact, and report two reconciliation tables.

Pure Python 3 standard library — no dependencies, no network, runs on Windows / macOS / Linux.

## What it does

- Parses Netscape Bookmark HTML (`<!DOCTYPE NETSCAPE-Bookmark-file-1>`), the format every browser exports
- Dedupes by exact URL (only scheme and host are case-folded)
- Keeps the master's copy, order, titles, icons and dates
- Routes the rest by a **folder map** — folders that mean the same thing merge into one, same-name folders merge level by level, everything else is flattened to the end of the toolbar
- **Learns**: answers you give about folder grouping are remembered, so the same question is never asked twice
- **Speaks Chinese or English** — `--lang zh|en` (or `BOOKMARK_LIBRARIAN_LANG`) switches the wording of the plan, the tables and the checks; the file it writes is byte-for-byte the same either way
- Writes one merged file and prints two tables (counts, duplicate detail)

## Install

This skill follows the [Agent Skills](https://agentskills.io/specification) open format — a
skill is just a folder containing a `SKILL.md`, and the same folder works across agents. This
repository **is** that folder: the repo root is the skill, and its name matches the `name` in
the frontmatter (`bookmark-librarian`).

**One command, any agent** — the [`skills` CLI](https://skills.sh/docs/cli) downloads it and
wires it up for whichever agent it finds:

```
npx skills add GhostCmdr/bookmark-librarian
```

**Or install by hand** — clone (or download and unzip) into the directory your agent reads:

```
git clone https://github.com/GhostCmdr/bookmark-librarian.git ~/.claude/skills/bookmark-librarian
```

| Agent | Path |
| --- | --- |
| Any Agent Skills client | `.agents/skills/bookmark-librarian/` |
| Claude Code | `~/.claude/skills/bookmark-librarian/` |
| TraeCode | `.trae/skills/bookmark-librarian/` (project) · `~/.trae-cn/skills/bookmark-librarian/` (global) |
| Cursor | `.cursor/rules/bookmark-librarian.mdc` (or `AGENTS.md`) |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Any other / unsure | paste `SKILL.md` into `AGENTS.md` |

Keep the folder named `bookmark-librarian` — the spec requires the directory name to match the
`name` in the frontmatter.

For agents that do not read YAML frontmatter, copy the `description` line into the top of
the rule file — that line is what triggers the skill.

## Usage

```
python3 scripts/merge.py --master Edge Edge=favorites.html Chrome=bookmarks.html Firefox=bookmarks_ff.html
python3 scripts/tables.py merge_stats.json 合并书签_Edge_Chrome_Firefox.html
```

- `--master <name>` — which source wins. Omit it for no-master mode (all sources equal, full folder structure kept).
- `--out <dir>` — where the merged file goes. Defaults to `~/Desktop`.
- `--stats <file>` — where `merge_stats.json` goes. Defaults to `./merge_stats.json`.
- `--dry-run` — print the routing plan and the "ask" list, write nothing. Add `--plan plan.json` to dump it.
- `--lang zh|en` — the wording of everything printed. Defaults to `zh`; `BOOKMARK_LIBRARIAN_LANG` sets it too, `--lang` wins.
- One source only → in-file dedupe only.
- Compare two exports without merging: `python3 scripts/diff.py A.html Edge B.html Chrome`

The merged file is the only deliverable; the tables are printed to stdout for the chat.

## Language

Every string the user sees — the routing plan, both tables, the diff table, the checks,
`map.py`'s output — comes from a label table (`scripts/i18n.py`), so a run can speak Chinese
or English:

```
python3 scripts/merge.py --lang en --master Edge Edge=favorites.html Chrome=bookmarks.html
python3 scripts/tables.py --lang en merge_stats.json 合并书签_Edge_Chrome.html
```

Language changes **wording only**. `merge_stats.json` keeps its structure and its stable ids
(`in_file_dup` / `vs_master_dup` / `merged_in`, `@toolbar-end`, empty string = toolbar level),
the merged file is still named `合并书签_{…}.html`, and `folder-map.json` is untouched — so a
table produced in one language still lines up with a run in the other.

**Which language gets used?** The scripts never detect it — whoever drives them picks it and
passes it explicitly. The agent is told to follow the language you write in (see `SKILL.md`):
an English request gets `--lang en` on every script it runs, a Chinese request gets `--lang zh`
(or nothing, since that is the default). One run stays in one language — the plan, the tables,
the ask-list questions and the surrounding explanation all match — and if you switch language
mid-task, it switches with you. Only a request with no language at all (a bare file drop) falls
back to the default `zh`.

## Folder map

Which folder names mean the same thing is data, not code:

| Layer | File |
| --- | --- |
| Builtin defaults (ships with the skill) | `scripts/folder-map.json` |
| What you taught (created on first answer) | `~/.bookmark-librarian/folder-map.json` |

`BOOKMARK_LIBRARIAN_HOME` relocates the user layer. The user layer wins: names it claims are
taken away from their builtin group, so teaching `影视` pulls the whole `影剧` group over
to it. Builtin default: `影剧` ← 影视 / 电影 / 动漫 / 动画 / 漫画 / 小说 / 番剧 / 剧集 /
追剧 / Anime / Movies / TV Shows.

```
python3 scripts/map.py list                          # the table in effect
python3 scripts/map.py add --as 读书 阅读             # these names are one folder, called 读书
python3 scripts/map.py confirm 影剧                   # the builtin canonical is fine — stop asking
python3 scripts/map.py skip 边界 华为                  # stop asking; treat as "everything else"
python3 scripts/map.py remove 阅读                    # undo one alias
```

A merge with a master source applies the map silently. A no-master merge asks about every
group that appears under more than one name until you settle it, then follows the recorded
decision — after a few merges there is nothing left to ask.

## Example

See [`examples/`](examples/) for a runnable sample and its expected output.

## Tests

```
python3 tests/test_bookmark_librarian.py
```

42 assertions covering URL boundaries (trailing slash, http vs https, `www.`), master
priority, folder routing, the folder map (builtin groups, taught groups, renamed canonical,
`skip`), empty-folder handling, ordering, read-only sources, the count reconciliation,
no-master mode and an English smoke test across all four scripts. The suite runs the shipped
scripts as subprocesses with an isolated `BOOKMARK_LIBRARIAN_HOME` and pins `BOOKMARK_LIBRARIAN_LANG=zh`,
so it never touches your real `~/.bookmark-librarian` and your environment can't shift the assertions.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Versions follow SemVer; the current version lives in
`metadata.version` in the `SKILL.md` frontmatter.

## License

MIT — see [LICENSE](LICENSE).
