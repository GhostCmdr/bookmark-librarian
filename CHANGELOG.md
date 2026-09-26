# Changelog

All notable changes to this skill are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

Still in `0.x`: the rules are usable but not finalised — minor versions may change merge
behaviour. Pin a version if you need stable output.

## [0.3.2] - 2026-09-26

### Changed

- **Renamed to `bookmark-librarian`** — the skill, the repository and the frontmatter `name` now
  say what it is (a bookmark librarian) rather than naming one of the things it does. The learned
  folder map moved to `~/.bookmark-librarian/folder-map.json`, and the env vars to
  `BOOKMARK_LIBRARIAN_HOME` / `BOOKMARK_LIBRARIAN_LANG`. Nothing had been published before this
  version, so there is nothing to migrate; the merged file is still `合并书签_{…}.html`

## [0.3.1] - 2026-09-26

### Changed

- **Spec-compliant frontmatter** — `version` moved under `metadata`, where the Agent Skills
  spec puts properties it does not define; the spec's own set is `name` / `description` /
  `license` / `compatibility` / `metadata` / `allowed-tools`. `name` is now unquoted so naive
  parsers read it as-is
- **Universal install docs** — the README now leads with `npx skills add GhostCmdr/bookmark-librarian`,
  and the per-agent path table lists the Agent Skills convention (`.agents/skills/`) first
  instead of opening with TraeCode

## [0.3.0] - 2026-09-26

### Added

- **Language layer** — `scripts/i18n.py` holds every user-facing string; `--lang zh|en` on
  `merge.py` / `tables.py` / `diff.py` / `map.py`, or `BOOKMARK_LIBRARIAN_LANG`, picks the table
  (`--lang` wins, default `zh`). English labels ship alongside the Chinese ones
- `i18n.where()` renders the internal position values (`""` = toolbar level, `@toolbar-end`
  = appended to the end of the toolbar)

### Changed

- Display text is separated from the data contract: `merge_stats.json` keeps stable ASCII ids
  (`in_file_dup` / `vs_master_dup` / `merged_in`) and the merged file is still named
  `合并书签_{…}.html`, whatever the language — so tables printed in one language still line up
  with a run in the other
- `diff.py` and `map.py` gained `--lang` and now read their wording from the label table;
  `bk_common`'s warnings (undecodable file, unreadable map) go through it too

### Fixed

- No-master mode referenced an undefined `TOOLBAR` name (crashed on a loose bookmark in the
  first source) and wrote a localized `kind` into `merge_stats.json`, which broke in-file
  duplicate attribution in table 2
- Test suite pins `BOOKMARK_LIBRARIAN_LANG=zh` so a developer's own environment cannot shift the
  assertions; added an English smoke test across all four scripts (42 assertions)

## [0.2.0] - 2026-09-26

### Added

- **Folder map** — which folder names mean the same thing is now data, not hardcoded rules: builtin defaults in `scripts/folder-map.json` layered under the user's own `~/.bookmark-librarian/folder-map.json` (`BOOKMARK_LIBRARIAN_HOME` relocates it). The user layer wins, so teaching `影视` renames the whole builtin `影剧` group
- `scripts/map.py` — `list` / `add --as <canonical> <alias>…` / `confirm` / `skip` / `remove` to read and grow the map
- `merge.py --dry-run` and `--plan <file>` — print the routing plan plus the "ask" list (unmatched top-level folders in master mode, groups present under several names in no-master mode) before writing anything
- In no-master mode an unconfirmed group is left alone and put to the user instead of being renamed silently
- `_不再询问` marker: record a folder as "asked already, use the default routing"
- Encoding fallback (`utf-8-sig` → `gb18030`) and forced UTF-8 stdout, so GBK exports from older Chinese browsers and cp936 Windows consoles both work

### Changed

- Rule 4 is map-driven instead of listing film folder names; a map hit lifts the whole subtree (subfolders included) into the canonical folder, using the master's own folder name when it already belongs to the group
- A canonical folder missing from the master is created at the very end of the toolbar, after the flattened bookmarks
- Rule 8: source empty folders are now carried over in no-master mode (`walk()` only yields bookmarks, so empty folders are created separately)
- Test suite grew to 36 end-to-end assertions; docs (EN / zh-CN / README) describe the folder map and how it learns

## [0.1.0] - 2026-09-26

### Added

- Master-first merge for Netscape Bookmark HTML exports (browser-agnostic: Edge / Chrome / Firefox / Huawei / 360 / QQ / Sogou / Opera / Safari)
- Folder routing: film folders → `影剧`; same-name folders merged level by level; the rest flattened to the end of the toolbar — no wrapper folders are created
- No-master mode (all sources equal, full folder structure kept) and single-file mode (in-file dedupe only)
- Table 1 (counts) and table 2 (duplicate detail), printed to the chat only; diff table for compare-only runs
- 35-assertion test suite, runnable example with expected output, bilingual SKILL.md (EN / zh-CN)
- Merged file defaults to the user's Desktop; `--out` / `--stats` override it
