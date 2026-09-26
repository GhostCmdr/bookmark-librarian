"""界面文案层：内部数据一律用稳定 id，只有给人看的字才过这里。

为什么分两层：merge.py 把 kind 和位置值写进 merge_stats.json，tables.py 再靠它们分支。
那些值是数据契约，不能跟着界面语言变，所以数据用 id（in_file / vs_master / @toolbar-end），
显示时才查这张表。

语言从 --lang 或 BOOKMARK_LIBRARIAN_LANG 来，默认中文。它只影响文案：输出文件名固定
`合并书签_….html`，merge_stats.json 的结构和取值、folder-map.json 的格式都不随语言变。
"""
import os

from bk_common import TOOLBAR_END

DEFAULT_LANG = "zh"
LANGS = ("zh", "en")

ZH = {
    "toolbar": "书签栏",
    "toolbar_end": "工具栏末尾",
    "loose": "（散书签）",
    "created": "（新建）",
    "exists_master": "（主库已有）",
    "exists": "（已有）",
    "into": "并入 {name}",
    "master_tag": "（主库）",
    "dash": "—",

    # 重复条目的类型（kind）
    "in_file_dup": "文件内重复",
    "vs_master_dup": "与主库重复",
    "merged_in": "合并新增",
    "removed": "移除",

    # 预案
    "plan_title": "## 归置预案（{mode}）",
    "mode_master": "主库模式：{name}",
    "mode_plain": "无主库模式",
    "th_routes": "| 来源 | 文件夹 | 条数 | 落点 |",
    "groups_title": "### 映射表命中",
    "th_groups": "| 语义组 | 落点 | 来源文件夹 | 条数 |",
    "ask_folders_title": "### 待询问 · 一级文件夹对不上主库、映射表里也没有",
    "th_ask_folders": "| 文件夹 | 来源 | 条数 | 示例 |",
    "ask_groups_title": "### 待询问 · 同一组出现了多个名字，规范名还没定过",
    "th_ask_groups": "| 语义组 | 现有名字 | 条数 | 可选的规范名 |",
    "next_ask": "下一步: 先问用户上面「待询问」的条目怎么归置，用 map.py 记下来，再重跑（去掉 --dry-run）。",
    "all_covered": "映射表已覆盖全部文件夹，无需询问。",
    "plan_written": "预案: {path}",
    "dry_note": "（--dry-run：未写合并文件、未写 stats）",
    "rule_same": "同名并入",
    "rule_flat": "拆平到工具栏末尾",
    "rule_keep": "原样保留",
    "help_out": "输出目录，默认用户桌面",
    "help_stats": "merge_stats.json 落点，默认当前目录",
    "help_plan": "把预案写成 JSON 的落点",
    "help_dry": "只出预案，不写文件",
    "help_sources": "<名称>=<文件路径>",
    "help_lang": "界面语言: zh / en（默认 zh）",

    # 校验
    "v_unique": "校验1 网址全局唯一",
    "v_unique_detail": "{n} 条 / {u} 唯一",
    "v_order": "校验2 主库相对顺序未变",
    "v_order_detail": "{n} 条主库条目顺序一致",
    "v_math": "校验3 原始 − 重复 = 输出",
    "v_math_detail": "{raw} − {removed} = {out}",

    # 收尾
    "merged_file": "合并文件: {path}",
    "stats_file": "统计: {path}",
    "next_step": "下一步: python3 tables.py \"{stats}\" \"{merged}\"",
    "err_source": "来源要写成 <名称>=<文件路径>，收到: {arg}",
    "err_master": "--master {name} 不在来源里：{labels}",

    # 表一 / 表二
    "t1_title": "## 表一 · 数量汇总",
    "th_t1": "| 来源 | 原始条目 | 文件内重复 | 跨来源重复 | 去重后保留 | 其中新增并入 |",
    "t1_total": "合计",
    "t1_merged": "合并书签",
    "t2_title": "## 表二 · 重复明细（{n} 行，其中「移除」{removed} 行、「文件内重复」{in_file} 行）",
    "th_t2": "| 序号 | 标题 | 网址 | 出现位置 | 保留来源 | 最终位置 |",
    "not_found": "未找到",

    # 差异表
    "th_diff": "| 序号 | 标题 / 网址 | 原来位置 | 最终保存位置 |",
    "no_title": "（无标题）",
    "empty_url": "（空网址）",
    "diff_summary": "{a} {na} 条 / {b} {nb} 条，差异 {rows} 行",
    "flat_end": "拆平到工具栏末尾",

    # 告警（bk_common）
    "warn_encoding": "警告: {path} 不是 UTF-8 也不是 GB18030，按 UTF-8 宽松解码",
    "warn_map": "警告: 忽略无法读取的映射表 {path} ({err})",

    # 映射表 CLI
    "map_builtin": "内置: {path}",
    "map_user": "用户: {path}",
    "map_user_missing": "   (尚未创建)",
    "map_empty": "\n映射表为空：所有对不上的文件夹都会走「询问」流程。",
    "th_map": "| 规范文件夹 | 会归入它的别名 | 来源 |",
    "map_src_user": "用户",
    "map_src_builtin": "内置",
    "map_only_itself": "（只有它自己）",
    "map_added": "已记录: {canonical} = {aliases}",
    "map_absorbed": "吸收了原有组: {names}",
    "map_written": "写入: {path}",
    "map_confirmed": "已确认: {group} = {aliases}",
    "map_no_group": "映射表里没有「{name}」这一组；要新建用 add --as",
    "map_skipped": "已记录: {names} → 不再询问，按默认处理",
    "map_removed": "已移除: {alias}",
    "map_not_in_user": "用户表里没有 {alias}；内置默认改不掉（要改就在用户表里 add 到别的组）",
    "map_usage": """用法:
  python3 map.py list                        看当前生效的全部映射
  python3 map.py add --as <规范名> <别名>…    把这些名字归成一组，规范名是 <规范名>
  python3 map.py confirm <规范名>             内置组按现在的规范名记成「我认了」，以后不再问
  python3 map.py skip <别名>…                 记成「不要再问，按默认处理」
  python3 map.py remove <别名>                从用户表里删掉一个别名（内置默认删不掉）""",
}

EN = {
    "toolbar": "Bookmarks bar",
    "toolbar_end": "end of toolbar",
    "loose": "(loose bookmarks)",
    "created": " (new)",
    "exists_master": " (in master)",
    "exists": " (exists)",
    "into": "merge into {name}",
    "master_tag": " (master)",
    "dash": "—",

    "in_file_dup": "in-file duplicate",
    "vs_master_dup": "duplicate of the master",
    "merged_in": "newly merged in",
    "removed": "removed",

    "plan_title": "## Routing plan ({mode})",
    "mode_master": "master mode: {name}",
    "mode_plain": "no-master mode",
    "th_routes": "| Source | Folder | Items | Landing |",
    "groups_title": "### Folder-map hits",
    "th_groups": "| Group | Landing | Source folders | Items |",
    "ask_folders_title": "### To ask · top-level folder matches neither the master nor the map",
    "th_ask_folders": "| Folder | Sources | Items | Samples |",
    "ask_groups_title": "### To ask · one group under several names, no canonical settled yet",
    "th_ask_groups": "| Group | Names present | Items | Canonical options |",
    "next_ask": "Next: ask the user how the \"to ask\" entries above should land, record it with map.py, then re-run without --dry-run.",
    "all_covered": "The map covers every folder — nothing to ask.",
    "plan_written": "Plan: {path}",
    "dry_note": "(--dry-run: no merged file, no stats written)",
    "rule_same": "merged by name",
    "rule_flat": "flattened to the end of the toolbar",
    "rule_keep": "kept as-is",
    "help_out": "output directory (default: the user's Desktop)",
    "help_stats": "where merge_stats.json goes (default: cwd)",
    "help_plan": "where to dump the plan as JSON",
    "help_dry": "print the plan only, write nothing",
    "help_sources": "<name>=<file path>",
    "help_lang": "UI language: zh / en (default zh)",

    "v_unique": "check 1 · URLs globally unique",
    "v_unique_detail": "{n} items / {u} unique",
    "v_order": "check 2 · master relative order unchanged",
    "v_order_detail": "{n} master items in the same order",
    "v_math": "check 3 · raw − duplicates = output",
    "v_math_detail": "{raw} − {removed} = {out}",

    "merged_file": "Merged file: {path}",
    "stats_file": "Stats: {path}",
    "next_step": "Next: python3 tables.py \"{stats}\" \"{merged}\"",
    "err_source": "A source must read <name>=<file path>, got: {arg}",
    "err_master": "--master {name} is not among the sources: {labels}",

    "t1_title": "## Table 1 · Counts",
    "th_t1": "| Source | Original items | In-file duplicates | Cross-source duplicates | Kept after dedupe | Newly merged in |",
    "t1_total": "Total",
    "t1_merged": "Merged bookmarks",
    "t2_title": "## Table 2 · Duplicate detail ({n} rows: {removed} removed, {in_file} in-file)",
    "th_t2": "| # | Title | URL | Occurrences | Kept by | Final location |",
    "not_found": "not found",

    "th_diff": "| # | Title / URL | Previous location | Final location |",
    "no_title": "(no title)",
    "empty_url": "(empty URL)",
    "diff_summary": "{a} {na} items / {b} {nb} items, {rows} differing rows",
    "flat_end": "flatten to the end of the toolbar",

    "warn_encoding": "warning: {path} is neither UTF-8 nor GB18030; decoding leniently as UTF-8",
    "warn_map": "warning: ignoring unreadable map {path} ({err})",

    "map_builtin": "Builtin: {path}",
    "map_user": "User: {path}",
    "map_user_missing": "   (not created yet)",
    "map_empty": "\nThe map is empty: every unmatched folder goes through the ask flow.",
    "th_map": "| Canonical folder | Names that route into it | From |",
    "map_src_user": "user",
    "map_src_builtin": "builtin",
    "map_only_itself": "(only itself)",
    "map_added": "Recorded: {canonical} = {aliases}",
    "map_absorbed": "Absorbed existing group: {names}",
    "map_written": "Written to: {path}",
    "map_confirmed": "Confirmed: {group} = {aliases}",
    "map_no_group": "No group named \"{name}\" in the map; create one with add --as",
    "map_skipped": "Recorded: {names} → stop asking, use the default routing",
    "map_removed": "Removed: {alias}",
    "map_not_in_user": "The user table has no {alias}; builtin defaults cannot be deleted (teach it into another group instead)",
    "map_usage": """Usage:
  python3 map.py list                        show the effective map
  python3 map.py add --as <canonical> <alias>…   group these names under <canonical>
  python3 map.py confirm <canonical>         accept the builtin canonical, stop asking
  python3 map.py skip <alias>…               stop asking, use the default routing
  python3 map.py remove <alias>              drop one alias from the user table""",
}

TABLES = {"zh": ZH, "en": EN}


def resolve_lang(explicit=None):
    """--lang 优先，其次 BOOKMARK_LIBRARIAN_LANG，都不认就回默认中文。"""
    for cand in (explicit, os.environ.get("BOOKMARK_LIBRARIAN_LANG")):
        code = (cand or "").strip().lower()
        if code in TABLES:
            return code
    return DEFAULT_LANG


def labels(lang=None):
    return TABLES[resolve_lang(lang)]


def where(L, pos):
    """内部位置值 -> 显示文案。空串 = 工具栏层（散书签），TOOLBAR_END = 追加到工具栏末尾。"""
    if pos == TOOLBAR_END:
        return L["toolbar_end"]
    return pos or L["toolbar"]
