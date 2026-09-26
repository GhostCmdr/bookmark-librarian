"""合并书签（SKILL.md 规则 1-9）：主库优先去重 + 副库按文件夹映射表归置。

用法:
  python3 merge.py --master <主库名> <名1>=<文件1> <名2>=<文件2> ...
  python3 merge.py <名1>=<文件1> <名2>=<文件2> ...              # 无主库模式
  python3 merge.py <名>=<文件>                                  # 单文件：只做文件内去重

可选:
  --out <目录>     交付物落点，默认用户桌面
  --stats <文件>   merge_stats.json 落点，默认当前目录
  --dry-run        只出归置预案与待询问清单，不写合并文件、不写 stats
  --plan <文件>    把预案写成 JSON（配合 --dry-run 用，给 agent 读）

产出:
  <out>/合并书签_<名1>_<名2>_….html
  <stats>                            供 tables.py 出表一 / 表二
"""
import argparse
import collections
import json
import os
import sys
import time
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bk_common import (  # noqa: E402
    FLAT_MARKER,
    alias_index,
    force_utf8_stdout,
    group_members,
    iter_folders,
    load_folder_map,
    member_keys,
    name_key,
    normalize_url,
    parse,
    path_group,
    user_keys,
    walk,
    write_bookmarks,
)
import i18n  # noqa: E402
from bk_common import TOOLBAR_END  # noqa: E402


def find_folder(node, name):
    key = name_key(name)
    for c in node["children"]:
        if c["type"] == "folder" and name_key(c["name"]) == key:
            return c
    return None


def make_folder(name, now):
    return {"type": "folder", "name": name,
            "attrs": {"add_date": now, "last_modified": now}, "children": []}


def new_item(bm):
    return {"type": "bookmark", "title": bm["title"], "href": bm["href"],
            "attrs": dict(bm["attrs"]), "children": []}


def blank_stats():
    return collections.defaultdict(
        lambda: {"original": 0, "in_file_dup": 0, "cross_dup": 0, "new": 0})


def toolbar_of(root):
    return root["children"][0] if root["children"] else root


def top_names(node):
    return {name_key(c["name"]) for c in node["children"] if c["type"] == "folder"}


def scan(base):
    """遍历工具栏，拿到 {文件夹路径: 条数} 和 {一级文件夹: 前 3 个标题}。"""
    counts = collections.Counter()
    samples = collections.defaultdict(list)
    for fpath, bm in walk(base):
        counts[fpath] += 1
        if fpath:
            s = samples[fpath[0]]
            if len(s) < 3:
                t = bm["title"] or bm["href"]
                if t not in s:
                    s.append(t)
    return counts, samples


def plan_source(counts, idx, master_tops, master_mode, taught):
    """每个文件夹路径的落点：group(规范名) / same / flat / keep。

    映射表命中的文件夹一律拆平进目标文件夹；主库模式下主库说了算，无主库模式下只有
    用户确认过的规范名才生效（没确认的先原样保留，等问了再说）。
    """
    plan = {}
    for fpath in counts:
        if not fpath:
            plan[fpath] = ("flat", None) if master_mode else ("keep", None)
            continue
        canon, _seg = path_group(fpath, idx)
        if canon == FLAT_MARKER:
            plan[fpath] = ("flat", FLAT_MARKER) if master_mode else ("keep", FLAT_MARKER)
        elif canon and (master_mode or name_key(canon) in taught):
            plan[fpath] = ("group", canon)
        elif master_mode and name_key(fpath[0]) in master_tops:
            plan[fpath] = ("same", None)
        elif master_mode:
            plan[fpath] = ("flat", None)
        else:
            plan[fpath] = ("keep", canon)
    return plan


def ensure_path(base, fpath, now):
    """按路径逐级找 / 建文件夹，返回最末一级。"""
    node = base
    for seg in fpath:
        ch = find_folder(node, seg)
        if ch is None:
            ch = make_folder(seg, now)
            node["children"].append(ch)
        node = ch
    return node


def group_target(base, canonical, folder_map, now, cache, pending):
    """主库已有的同组成员文件夹优先（名字用主库的），否则新建规范名文件夹。

    新建的不立刻挂到工具栏上，先攒进 pending，等拆平的书签都追加完了再统一接到末尾——
    这样「新建的规范文件夹排在工具栏最末」是确定的，不随来源处理顺序漂移。
    """
    hit = cache.get(canonical)
    if hit is not None:
        return hit
    keys = member_keys(folder_map, canonical)
    for c in base["children"]:
        if c["type"] == "folder" and name_key(c["name"]) in keys:
            cache[canonical] = c
            return c
    created = make_folder(canonical, now)
    pending.append(created)
    cache[canonical] = created
    return created


def merge_master(sources, now, folder_map):
    """规则 1-7：主库为准去重，副库按 映射表 / 同名 / 其余 三路归置。"""
    master = sources[0][0]
    root = sources[0][2]
    base = toolbar_of(root)
    idx = alias_index(folder_map)
    taught = user_keys()
    master_tops = top_names(base)

    seen, dups, added, flat = {}, [], [], []
    stats = blank_stats()
    cache, pending = {}, []

    def prune(node, path):
        kept = []
        for c in node["children"]:
            if c["type"] == "folder":
                prune(c, path + (c["name"],))
                kept.append(c)
                continue
            stats[master]["original"] += 1
            u = normalize_url(c["href"])
            pos = "/".join(path)
            if u and u in seen:
                stats[master]["in_file_dup"] += 1
                dups.append({"source": master, "title": c["title"], "url": c["href"],
                             "path": pos, "kept_at": seen[u][1], "kind": "in_file_dup"})
            else:
                if u:
                    seen[u] = (master, pos)
                kept.append(c)
        node["children"] = kept

    prune(base, ())

    for label, _path, src_root in sources[1:]:
        src_base = toolbar_of(src_root)
        counts, _samples = scan(src_base)
        plan = plan_source(counts, idx, master_tops, True, taught)
        local = {}
        for fpath, bm in walk(src_base):
            stats[label]["original"] += 1
            u = normalize_url(bm["href"])
            pos = "/".join(fpath)
            if u and u in local:
                stats[label]["in_file_dup"] += 1
                dups.append({"source": label, "title": bm["title"], "url": bm["href"],
                             "path": pos, "kept_at": local[u], "kind": "in_file_dup"})
                continue
            if u:
                local[u] = pos
            if u and u in seen:
                stats[label]["cross_dup"] += 1
                dups.append({"source": label, "title": bm["title"], "url": bm["href"],
                             "path": pos, "kept_at": seen[u][1], "kind": "vs_master_dup"})
                continue

            item = new_item(bm)
            stats[label]["new"] += 1
            added.append({"source": label, "title": bm["title"], "url": bm["href"],
                          "path": pos, "kind": "merged_in"})

            kind, canon = plan.get(fpath, ("flat", None))
            if kind == "group":
                tgt = group_target(base, canon, folder_map, now, cache, pending)
                tgt["children"].append(item)
                if u:
                    seen[u] = (label, tgt["name"])
                continue

            if kind == "same":
                node, matched = base, 0
                for seg in fpath:
                    ch = find_folder(node, seg)
                    if ch is None:
                        break
                    node, matched = ch, matched + 1
                for seg in fpath[matched:]:
                    ch = find_folder(node, seg)
                    if ch is None:
                        ch = make_folder(seg, now)
                        node["children"].append(ch)
                    node = ch
                node["children"].append(item)
                if u:
                    seen[u] = (label, pos)
                continue

            flat.append(item)
            if u:
                seen[u] = (label, TOOLBAR_END)

    base["children"].extend(flat)
    base["children"].extend(pending)     # 新建的规范文件夹排在工具栏最末
    return root, stats, dups, added, "master"


def merge_plain(sources, now, folder_map):
    """规则 8：无主库。骨架取第一个文件，空文件夹全保留，同名逐级并入，确认过的语义组归一。"""
    first = sources[0][0]
    root = sources[0][2]
    base = toolbar_of(root)
    idx = alias_index(folder_map)
    taught = user_keys()
    seen, dups, added = {}, [], []
    stats = blank_stats()
    cache, pending = {}, []

    def prune(node, path):
        kept = []
        for c in node["children"]:
            if c["type"] == "folder":
                prune(c, path + (c["name"],))
                kept.append(c)          # 空文件夹保留
                continue
            stats[first]["original"] += 1
            u = normalize_url(c["href"])
            pos = "/".join(path)
            if u and u in seen:
                stats[first]["in_file_dup"] += 1
                dups.append({"source": first, "title": c["title"], "url": c["href"],
                             "path": pos, "kept_at": seen[u][1], "kind": "in_file_dup"})
            else:
                if u:
                    seen[u] = (first, pos)
                kept.append(c)
        node["children"] = kept

    prune(base, ())

    for label, _path, src_root in sources[1:]:
        src_base = toolbar_of(src_root)
        counts, _samples = scan(src_base)
        plan = plan_source(counts, idx, set(), False, taught)
        local = {}

        # 规则 8：无主库时空文件夹也保留。walk() 只吐书签，所以空文件夹要单独补建；
        # 走映射表归一（group）的路径不建，它整棵并进规范文件夹。
        for fpath, _node in iter_folders(src_base):
            kind, _canon = plan.get(fpath, ("keep", None))
            if kind == "keep":
                ensure_path(base, fpath, now)

        for fpath, bm in walk(src_base):
            stats[label]["original"] += 1
            u = normalize_url(bm["href"])
            pos = "/".join(fpath)
            if u and u in local:
                stats[label]["in_file_dup"] += 1
                dups.append({"source": label, "title": bm["title"], "url": bm["href"],
                             "path": pos, "kept_at": local[u], "kind": "in_file_dup"})
                continue
            if u:
                local[u] = pos
            if u and u in seen:
                stats[label]["cross_dup"] += 1
                dups.append({"source": label, "title": bm["title"], "url": bm["href"],
                             "path": pos, "kept_at": seen[u][1], "kind": "vs_master_dup"})
                continue

            item = new_item(bm)
            stats[label]["new"] += 1
            added.append({"source": label, "title": bm["title"], "url": bm["href"],
                          "path": pos, "kind": "merged_in"})

            kind, canon = plan.get(fpath, ("keep", None))
            if kind == "group":
                tgt = group_target(base, canon, folder_map, now, cache, pending)
                tgt["children"].append(item)
                if u:
                    seen[u] = (label, tgt["name"])
                continue

            ensure_path(base, fpath, now)["children"].append(item)
            if u:
                seen[u] = (label, pos)

    base["children"].extend(pending)
    return root, stats, dups, added, "plain"


def build_report(sources, master_mode, folder_map):
    """归置预案：每条「来源 / 文件夹 / 落点」+ 待询问清单。"""
    idx = alias_index(folder_map)
    taught = user_keys()
    base = toolbar_of(sources[0][2])
    master_tops = top_names(base) if master_mode else set()

    routed, groups = [], collections.OrderedDict()
    asks = collections.OrderedDict()
    present = collections.defaultdict(lambda: {"names": [], "count": 0, "sources": []})

    for i, (label, _path, root) in enumerate(sources):
        counts, samples = scan(toolbar_of(root))
        plan = plan_source(counts, idx, master_tops, master_mode, taught)
        skeleton = i == 0
        for fpath, n in counts.items():
            here = "/".join(fpath)
            kind, canon = plan[fpath]
            if skeleton and master_mode:
                continue        # 主库自己的文件夹不动，也不参与归置统计
            hit, _seg = path_group(fpath, idx) if fpath else (None, None)
            if hit and hit != FLAT_MARKER:
                info = present[hit]
                info["count"] += n
                if label not in info["sources"]:
                    info["sources"].append(label)
                keys = member_keys(folder_map, hit)
                for seg in fpath:
                    if name_key(seg) in keys:
                        if seg not in info["names"]:
                            info["names"].append(seg)
                        break
            if kind == "group":
                g = groups.setdefault(canon, {"group": canon, "count": 0, "from": []})
                g["count"] += n
                if here not in g["from"]:
                    g["from"].append(here)
            elif master_mode and kind == "flat" and fpath and canon != FLAT_MARKER:
                b = asks.setdefault(fpath[0], {"folder": fpath[0], "count": 0,
                                               "sources": [], "samples": samples[fpath[0]]})
                b["count"] += n
                if label not in b["sources"]:
                    b["sources"].append(label)
            if skeleton:
                continue        # 第一个文件是骨架（主库 / 无主库的底）
            routed.append({"source": label, "folder": here, "count": n, "kind": kind,
                           "target": canon or ""})

    for canon, g in groups.items():
        keys = member_keys(folder_map, canon)
        hit = next((c["name"] for c in base["children"]
                    if c["type"] == "folder" and name_key(c["name"]) in keys), None)
        g["target"] = hit or canon
        g["created"] = hit is None

    ask_groups = []
    if not master_mode:
        for canon, info in present.items():
            if canon == FLAT_MARKER or len(info["names"]) < 2:
                continue
            if name_key(canon) in taught:
                continue
            ask_groups.append({"group": canon, "names_present": info["names"],
                               "members": group_members(folder_map, canon),
                               "count": info["count"], "sources": info["sources"]})

    return {"mode": "master" if master_mode else "plain",
            "master": sources[0][0] if master_mode else None,
            "map_user_path": os.path.join(
                os.environ.get("BOOKMARK_LIBRARIAN_HOME")
                or os.path.join(os.path.expanduser("~"), ".bookmark-librarian"),
                "folder-map.json"),
            "routes": routed, "groups": list(groups.values()),
            "ask_folders": list(asks.values()), "ask_groups": ask_groups}


def print_report(rep, L):
    rule = {"same": L["rule_same"], "flat": L["rule_flat"], "keep": L["rule_keep"]}
    mode = L["mode_master"].format(name=rep["master"]) if rep["mode"] == "master" \
        else L["mode_plain"]
    print(L["plan_title"].format(mode=mode))
    print()
    print(L["th_routes"])
    print("| --- | --- | --- | --- |")
    for r in rep["routes"]:
        if r["kind"] in ("group", "same"):
            dest = L["into"].format(name=r["target"] if r["kind"] == "group" else r["folder"])
        else:
            dest = rule.get(r["kind"], r["kind"])
        print("| %s | %s | %d | %s |" % (r["source"], i18n.where(L, r["folder"]),
                                         r["count"], dest))
    if rep["groups"]:
        print()
        print(L["groups_title"])
        print()
        print(L["th_groups"])
        print("| --- | --- | --- | --- |")
        for g in rep["groups"]:
            tag = L["created"] if g["created"] else (
                L["exists_master"] if rep["mode"] == "master" else L["exists"])
            print("| %s | %s%s | %s | %d |" % (
                g["group"], g["target"], tag,
                "、".join(i18n.where(L, x) for x in g["from"]), g["count"]))
    if rep["ask_folders"]:
        print()
        print(L["ask_folders_title"])
        print()
        print(L["th_ask_folders"])
        print("| --- | --- | --- | --- |")
        for a in rep["ask_folders"]:
            print("| %s | %s | %d | %s |" % (a["folder"], "、".join(a["sources"]), a["count"],
                                             "、".join(a["samples"])))
    if rep["ask_groups"]:
        print()
        print(L["ask_groups_title"])
        print()
        print(L["th_ask_groups"])
        print("| --- | --- | --- | --- |")
        for a in rep["ask_groups"]:
            print("| %s | %s | %d | %s |" % (a["group"], "、".join(a["names_present"]),
                                             a["count"], "、".join(a["members"])))
    print()
    print(L["next_ask"] if rep["ask_folders"] or rep["ask_groups"] else L["all_covered"])


def verify(master_path, merged_path, raw, removed, L):
    """校验 1-3。"""
    res = []
    items = walk(toolbar_of(parse(merged_path)))
    urls = [normalize_url(b["href"]) for _, b in items]
    res.append((L["v_unique"], len(urls) == len(set(urls)),
                L["v_unique_detail"].format(n=len(urls), u=len(set(urls)))))
    if master_path:
        master_urls = list(dict.fromkeys(
            normalize_url(b["href"]) for _, b in walk(toolbar_of(parse(master_path)))))
        in_out = [u for u in urls if u in set(master_urls)]
        res.append((L["v_order"], in_out == master_urls,
                    L["v_order_detail"].format(n=len(master_urls))))
    res.append((L["v_math"], raw - removed == len(items),
                L["v_math_detail"].format(raw=raw, removed=removed, out=len(items))))
    return res


def default_out():
    """交付物默认落桌面；没有桌面目录（容器 / 无 GUI）就退回当前目录。"""
    candidates = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "桌面"),
        os.path.join(os.path.expanduser("~"), "桌面"),
    ]
    for desk in candidates:
        if os.path.isdir(desk):
            return desk
    return os.getcwd()


def argv_lang(argv):
    """先于 argparse 把 --lang 抠出来，好让 --help 本身也用对语言。"""
    if "--lang" in argv:
        i = argv.index("--lang")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def main():
    force_utf8_stdout()
    L = i18n.labels(argv_lang(sys.argv[1:]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help=L["help_out"])
    ap.add_argument("--stats", default=None, help=L["help_stats"])
    ap.add_argument("--master", default=None)
    ap.add_argument("--dry-run", action="store_true", help=L["help_dry"])
    ap.add_argument("--plan", default=None, help=L["help_plan"])
    ap.add_argument("--lang", default=None, choices=i18n.LANGS, help=L["help_lang"])
    ap.add_argument("sources", nargs="+", help=L["help_sources"])
    a = ap.parse_args()
    L = i18n.labels(a.lang)

    pairs = []
    for s in a.sources:
        if "=" not in s:
            ap.error(L["err_source"].format(arg=s))
        label, path = s.split("=", 1)
        pairs.append((label.strip(), path.strip()))
    if a.master:
        hit = [p for p in pairs if name_key(p[0]) == name_key(a.master)]
        if not hit:
            ap.error(L["err_master"].format(name=a.master, labels=[p[0] for p in pairs]))
        pairs = hit + [p for p in pairs if p is not hit[0]]

    sources = [(label, path, parse(path)) for label, path in pairs]
    folder_map = load_folder_map()
    master_mode = bool(a.master) and len(sources) > 1

    rep = build_report(sources, master_mode, folder_map)
    print_report(rep, L)
    if a.plan:
        plan_path = os.path.abspath(a.plan)
        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
        with open(plan_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print(L["plan_written"].format(path=plan_path))
    if a.dry_run:
        print(L["dry_note"])
        return 0

    out = os.path.abspath(a.out or default_out())
    os.makedirs(out, exist_ok=True)
    now = str(int(time.time()))
    if master_mode:
        root, stats, dups, added, mode = merge_master(sources, now, folder_map)
    else:
        root, stats, dups, added, mode = merge_plain(sources, now, folder_map)

    out_name = "合并书签_%s.html" % "_".join(l for l, _, _ in sources)
    merged_path = os.path.join(out, out_name)
    write_bookmarks(root, merged_path)

    raw = sum(s["original"] for s in stats.values())
    in_file = sum(s["in_file_dup"] for s in stats.values())
    cross = sum(s["cross_dup"] for s in stats.values())
    kept = raw - in_file - cross

    rows = [{"key": l, "label": l, "original": stats[l]["original"],
             "in_file_dup": stats[l]["in_file_dup"], "cross_dup": stats[l]["cross_dup"],
             "new": stats[l]["new"],
             "kept": stats[l]["original"] - stats[l]["in_file_dup"] - stats[l]["cross_dup"]}
            for l, _, _ in sources]
    items = walk(toolbar_of(root))
    payload = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "master": sources[0][0] if master_mode else None,
        "sources": rows,
        "total_raw": raw, "total_merged": kept, "total_removed": raw - kept,
        "unique_domains": len({urlsplit(b["href"]).netloc.lower() for _, b in items}),
        "dups": dups, "added_new": added,
    }
    stats_path = os.path.abspath(a.stats or os.path.join(os.getcwd(), "merge_stats.json"))
    os.makedirs(os.path.dirname(stats_path), exist_ok=True)
    with open(stats_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(L["merged_file"].format(path=merged_path))
    print(L["stats_file"].format(path=stats_path))
    for name, ok, detail in verify(sources[0][1] if master_mode else None,
                                   merged_path, raw, raw - kept, L):
        print("%-4s %s   [%s]" % ("PASS" if ok else "FAIL", name, detail))
    print(L["next_step"].format(stats=stats_path, merged=merged_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
