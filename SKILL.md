---
name: bookmark-librarian
description: "Merges browser bookmark HTML exports (Netscape format) into one master-first deduped file plus stats tables. Invoke when the user sends bookmark .html files or asks to merge / dedupe / consolidate bookmarks (合并书签 / 收藏夹合并 / 書籤去重)."
license: MIT
compatibility: Python 3.8+; standard library only, no network access
metadata:
  version: "0.3.2"
---

# Bookmark Librarian

Merge bookmark exports from several browsers into one file, deduplicated against a
designated master source, and report two stats tables.

> 中文版：[SKILL.zh-CN.md](SKILL.zh-CN.md)

## When it triggers

**Trigger**

- A bookmark export `.html` arrives: `NETSCAPE-Bookmark-file-1` appears in the first 2 KB (tolerate BOM and case differences), or the filename contains `favorites` / `bookmarks` / `收藏夹` / `书签`. One file or many.
- Phrasing: merge bookmarks · dedupe bookmarks · consolidate bookmarks · migrate bookmarks · new browser · new computer · 合并书签 · 书签去重 · 收藏夹合并 · 书签迁移
- Traditional Chinese: 合併書籤 · 書籤去重
- Vague but clearly intended: "my bookmarks are a mess", "can these files be combined", "check for duplicates"

**Load but do not merge**

- Dedupe check only → output table 1 + table 2, write no merged file
- Diff two files only → output the diff table only, no merge

**Do not trigger**

- Ordinary web page `.html` (no such DOCTYPE), `.url` / `.webloc` shortcuts, `.json` / `.csv` exports
- Extension-less JSON `Bookmarks` inside a Chrome install dir — tell the user to use the browser's "Export bookmarks" instead
- Adding / editing / deleting a single bookmark, or just bookmarking a URL
- Generating bookmarks from CSV / Markdown / JSON, or creating a bookmark file from scratch
- Importing bookmarks into a browser (a local browser action, not file processing)
- Checking for dead links, or merely reading bookmark contents

**Confirm the master source first**

- "make Edge the base", "use Chrome as the bottom", "favorites is the source of truth" all mean the master; if the user did not say, ask once, or run in no-master mode
- Folder grouping is a separate question, asked only about names the folder map does not know yet — see "The folder map"

## Input

- One or more Netscape Bookmark HTML files (Edge / Chrome / Firefox / Huawei / 360 / QQ / Sogou / Opera / Safari exports all work)
- One of them may be designated master, or not

## Browser-name detection

The output filename carries browser names. Check in this order, stop at the first hit:

1. The user said so ("this is Edge", "exported from Huawei browser") → use it
2. Filename hints: `favorites` / `Microsoft_Edge` / `edge` → Edge; `chrome` → Chrome; `firefox` → Firefox; `safari` → Safari; `opera` → Opera; `brave` → Brave; `huawei` / `华为` → Huawei; `360` → 360; `qq` → QQ; `sogou` / `搜狗` → Sogou; `uc` → UC
3. Default export filenames:

   | Default filename | Browser |
   | --- | --- |
   | `bookmarks_2026_9_26.html` (`bookmarks` + date) | Chrome |
   | `Microsoft_Edge_2026_9_26.html` / `favorites_2026_9_26.html` | Edge (both forms occur across versions) |
   | `Safari Bookmarks.html` | Safari |
   | `bookmarks.html` / `bookmarks.htm` | Firefox / 360 / QQ / Sogou / Opera — **not unique** |

4. Fallback: an ambiguous `bookmarks.html`, or a filename with no hint at all (`1.html`, `新建文件夹 (2).html`) → ask "which browser is this from?" — do not guess

## Rules

1. **Duplicate test**: exact URL comparison, lowercasing scheme and host only. http vs https, presence of `www.`, a trailing slash, `#anchor` and query parameters are all treated as different addresses. Empty HREF and `javascript:` bookmarks do not participate in dedupe and are kept as-is.
2. **Master wins**: for the same URL keep the master's copy and delete copies from other sources; title, icon and add-date all come from the master.
3. **Duplicates inside the master**: keep the first occurrence.
4. **Folder placement (driven by the folder map)**: dedupe globally first, then route each remaining source item. **No wrapper or grouping folders are ever created.** Every source folder path is looked up in the **folder map** — a table of `canonical folder → names that mean the same thing` (see "The folder map" below):
   - **Map hit → lift the whole subtree**: bookmarks in the matched folder *and in every subfolder under it* are flattened, in traversal order, into the canonical folder; neither the folder nor its subfolders survive, and no sub-hierarchy is recreated. The target is the master's own folder when it already belongs to the group — the master's name wins (master has `影视`, canonical is `影剧` → everything goes into `影视`); when the master has none, a new folder named after the canonical is created **at the very end of the toolbar**.
   - **Same-name folders**: when a source top-level folder name matches a master top-level folder, merge level by level; the master's folder names and paths stay unchanged. Missing lower levels are created.
   - **Everything else**: source folders whose top-level name does not match, plus loose bookmarks outside any folder — **drop the folders**, append the bookmarks in source-file order to the end of the master toolbar (after all master content). Newly created canonical folders are appended after those, so the toolbar's last entry is a created folder when any was created.
5. **Empty folders**: the master's empty folders are kept; a source's empty folders are not.
6. **Ordering**: master order is untouched. Items lifted into a canonical folder are appended to the end of that folder; flattened items are appended to the end of the toolbar, followed by any newly created canonical folder. Within a group, source-file order; between sources, the given order.
7. **Source files are read-only**; write a new file.
8. **No-master mode**: all sources are equal, the whole folder structure is kept (rule 4's flattening does not apply — there is no master to route into), the skeleton comes from the first file, and other sources merge level by level into same-name folders. Four differences:
   - The folder map is **not applied on its own**: a canonical name only takes effect once the user has confirmed it (`map.py confirm`, or `map.py add --as`). Until then those folders are kept as they are and listed for the user to decide
   - Empty folders are all kept; rule 5's "source empty folders are not" does not apply
   - Duplicates are still removed, keeping the earlier occurrence, ordered by "file order → in-file traversal order"
   - Table 1's "cross-source duplicates" and "newly merged in" columns show —
9. **Single-file mode**: with only 1 file, do an in-file dedupe only; output the merged file + table 2, and show — in table 1's "cross-source duplicates" and "newly merged in" columns.

## The folder map (it learns as you use it)

Which folder names mean the same thing is **data, not code** — a two-layer table:

| Layer | File | Where it comes from |
| --- | --- | --- |
| Builtin defaults | `scripts/folder-map.json` | ships with the skill |
| What the user taught | `~/.bookmark-librarian/folder-map.json` | created on the first answer |

`BOOKMARK_LIBRARIAN_HOME` relocates the user layer (the tests use it to stay off your real one).

**The user layer wins.** An alias it claims is taken away from its builtin group, and a builtin group whose own name is claimed disappears entirely — that is how renaming a canonical works: teach `影视` and the whole `影剧` group follows it.

Builtin defaults:

| Canonical | Names that route into it |
| --- | --- |
| 影剧 | 影视、电影、动漫、动画、漫画、小说、番剧、剧集、追剧、Anime、Movies、TV Shows |

**The map grows.** Every answer is written to the user layer, so the same question is never asked twice. A merge with a master source applies the map silently. A no-master merge keeps asking about each group that turns up under more than one name until the user settles it — then it just follows the recorded decision. After a few merges the ask list is empty.

Answering an "ask" entry — four ways:

| The user means | Command |
| --- | --- |
| These names are one folder; use this name | `map.py add --as <canonical> <alias>…` |
| The builtin canonical is fine | `map.py confirm <canonical>` |
| Don't ask again — treat it as "everything else" | `map.py skip <alias>…` |
| Undo something I taught | `map.py remove <alias>` |

`map.py list` prints the table currently in effect. In no-master mode, when a group shows up under several names, ask the user to **pick one of the present names as the canonical, or name a new one** — never decide for them.

## Output

Only item 1 is a deliverable (`merge_stats.json` is an intermediate); table 1 / table 2 / the diff table are shown in chat only and never written to a file.

1. Merged bookmark file named `合并书签_{browser1}_{browser2}_….html`, N sources joined with `_` in "master first, then the given order" (e.g. `合并书签_Edge_Chrome_华为.html`)
   - **Written to the user's Desktop by default**: `~/Desktop`, then the OneDrive-redirected Desktop (`~/OneDrive/Desktop`, `~/OneDrive/桌面`), then `~/桌面`; a headless environment with none of those falls back to the working directory. If the user names another directory, use it
   - The `merge_stats.json` intermediate stays in the working directory, not on the Desktop
2. Table 1 · Counts: source / original items / in-file duplicates / cross-source duplicates / kept after dedupe / newly merged in. Last row "合计", and one row below it "合并书签" with only the bookmark count, everything else —
3. Table 2 · Duplicate detail: # / title / URL / occurrences / kept by / final location
   - Same URL + same title occupies one row; "occurrences" lists every path it appears at in every source (`source - path`, loose bookmarks shown as `书签栏`), duplicates within one folder marked ×N
   - "kept by" = the source of the surviving copy (master first; in no-master mode the first source it appeared in); "final location" = its path in the merged file
   - **Same URL but a title differing from the kept copy gets its own row**: "final location" is `—`; if that copy and the kept one are in the **same source file** → "kept by" reads `文件内重复`, if in a **different source** → `移除`
4. Diff table (only in "compare differences" mode, no merge): # / title+URL (one cell, title above URL) / previous location / final location; **only differing rows** — A only, B only, different location. Rows present on both sides at the same location are omitted. Locations read `source - folder path`, loose bookmarks `书签栏`; "previous location" = the item's path in its original file, "final location" = where rule 4 predicts it will land in the merged file (`并入 X` / `拆平到工具栏末尾`)

## Counting rules

- in-file duplicates = number of copies deleted
- cross-source duplicates = number of copies overridden by the master (a differing title still counts as a duplicate; it merely gets its own `移除` row in the detail table)
- kept after dedupe = original − in-file duplicates − cross-source duplicates

The three must reconcile.

## Table constraints

- Same URL + same title occupies one row; a differing title gets its own row marked `文件内重复` or `移除`, with `—` as the final location
- Always state which copy was kept and where it ended up
- Shown in chat, never written into the generated file

## Post-merge checks

1. URLs are globally unique
2. The master's relative order is unchanged
3. original − duplicates = output, equivalent to "master kept + newly merged in = output" (newly merged items are already counted in the original, do not add them again)

## Language

Everything the user sees — the routing plan, tables 1 and 2, the diff table, the three
checks, `map.py`'s output — comes from a label table, so the same run can speak Chinese or
English:

- `--lang zh|en` on `merge.py` / `tables.py` / `diff.py` / `map.py`, or the
  `BOOKMARK_LIBRARIAN_LANG` environment variable. `--lang` wins; the default is `zh`
- Language changes **wording only**. The merged file is still named `合并书签_{…}.html`,
  `merge_stats.json` keeps its structure and its stable ids (`in_file_dup` / `vs_master_dup` /
  `merged_in`, `@toolbar-end`, empty string = toolbar level), and `folder-map.json` is
  untouched — a table produced in one language still lines up with a run in the other
- Only the wording moves: loose bookmarks read `书签栏` in Chinese and `Bookmarks bar` in English

**Follow the user's language.** The scripts never detect it — you pick it, and you pass it
explicitly rather than relying on the default:

- Read the language the user is writing in. English request → add `--lang en` to **every**
  script you run (`merge.py`, `tables.py`, `diff.py`, `map.py`); Chinese request → `--lang zh`,
  or omit it since `zh` is the default
- Keep one language for the whole run: the plan you show, the tables you relay, the ask-list
  questions you put to the user and your own surrounding prose all match it
- If the user switches language mid-task, switch with them and pass the new `--lang` from
  there on
- Only when the request carries no language at all (a bare file drop, a one-word "merge") fall
  back to the default `zh` — do not mix languages in one report

## Running the bundled scripts

The skill ships its implementation under `scripts/` (relative to this SKILL.md). **Run them in order; do not rewrite the logic**:

0. **Plan first, then ask** — the merge always prints the routing plan and an "ask" list. When the list is non-empty, settle it with the user before writing anything:

   ```
   python3 scripts/merge.py [--lang zh|en] --dry-run --plan plan.json --master <master> <n1>=<f1> <n2>=<f2> ...
   ```

   `--dry-run` writes no merged file and no stats; `--plan <file>` dumps the plan as JSON. The printed "待询问" tables are what you put to the user: unmatched top-level folders (in master mode) and groups present under several names (in no-master mode). Record each answer with `map.py`, then re-run without `--dry-run`. A run with nothing to ask needs no extra step.

1. **Merge**

   ```
   python3 scripts/merge.py [--lang zh|en] --master <master-name> <name1>=<file1> <name2>=<file2> ...
   ```

   - `--out <dir>` optional, defaults to the user's Desktop; if the user names another directory, pass it
   - `--stats <file>` optional, defaults to `merge_stats.json` in the current directory
   - No-master mode: drop `--master`; single file: pass just one `<name>=<file>`
   - Produces `合并书签_<name1>_<name2>_….html` and prints checks 1-3
   - On Windows use `python` if `python3` is not on PATH

2. **Table 1 + table 2** (chat only)

   ```
   python3 scripts/tables.py [--lang zh|en] <merge_stats.json> <merged-file.html>
   ```

3. **Diff table** (compare-only, no merge)

   ```
   python3 scripts/diff.py [--lang zh|en] <fileA> <nameA> <fileB> <nameB>
   ```

4. **Folder map** (only when the user answers an ask entry)

   ```
   python3 scripts/map.py [--lang zh|en] list
   python3 scripts/map.py [--lang zh|en] add --as <canonical> <alias> ...
   python3 scripts/map.py [--lang zh|en] confirm <canonical>
   python3 scripts/map.py [--lang zh|en] skip <alias> ...
   python3 scripts/map.py [--lang zh|en] remove <alias>
   ```

The scripts' stdout is the final table — relay it verbatim, do not reformat. `scripts/bk_common.py` is the shared parser / writer; `scripts/folder-map.json` is the builtin map; `scripts/i18n.py` holds the wording for both languages.

## Implementation notes

- **Parsing**: in Netscape Bookmark HTML `<DT><H3>` is a folder and `<DT><A HREF>` is a bookmark; use a stack for nested `<DL>`; the title comes from the tag's text
- **URL comparison**: `urlsplit`, lowercase only scheme and netloc, keep path / query / fragment as-is
- **Folder matching**: dedupe globally first, then route three ways ("map hit → canonical folder / same-name level-by-level merge / everything else flattened to the end of the toolbar"); compare folder names with surrounding whitespace stripped and case ignored; never create a wrapper folder
- **Folder map**: `load_folder_map()` layers `~/.bookmark-librarian/folder-map.json` over the builtin `scripts/folder-map.json`; user entries win by claiming names away from builtin groups. `alias_index()` maps a name to its canonical, `member_keys()` gives every spelling of a group. The reserved canonical `_不再询问` (`FLAT_MARKER`) means "asked already — use the default routing"
- **Encoding**: read with `utf-8-sig`, fall back to `gb18030` for older Chinese browsers, warn and decode leniently if neither fits; force stdout/stderr to UTF-8 so Chinese output survives a cp936 Windows console
- **Language**: user-facing text lives in `scripts/i18n.py`. `merge_stats.json` stores stable ids and `i18n.where()` renders them at display time; `--lang` / `BOOKMARK_LIBRARIAN_LANG` pick the table (`--lang` first), and the wording never touches the data contract, the position ids or the output filename
- **Ordering**: the master tree keeps its order; source items are appended in traversal order to the target folder's end
- **Writing**: UTF-8 output, preserving ICON / ADD_DATE and other original attributes
- **Diff table**: run an in-file dedupe on each side, align by normalised URL; emit A-only / B-only / different-location rows, locations as `source - path` (loose bookmarks `书签栏`), and predict the B side's landing spot with rule 4
- **Table 2**: group by normalised URL first, then split again by whether the title matches the kept copy; for mismatching rows, mark `文件内重复` when it is the same source file, `移除` when it is a different source, and write `—` as the final location
- **Checks**: after merging, re-parse the output file and run the three checks above
