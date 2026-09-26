"""差异表：只列两个书签文件之间有差异的条目（不合并）。

列：序号 / 标题+网址 / 原来位置 / 最终保存位置
行：仅 A 有、仅 B 有、位置不同；两边都有且位置相同的不出行。
只在对话中展示，不落盘。

用法: python3 diff.py [--lang zh|en] <A文件> <A名称> <B文件> <B名称>
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bk_common import (  # noqa: E402
    FLAT_MARKER,
    alias_index,
    force_utf8_stdout,
    load_folder_map,
    member_keys,
    name_key,
    normalize_url,
    parse,
    path_group,
    walk,
)
import i18n  # noqa: E402

SEP = " - "


def toolbar(root):
    for c in root["children"]:
        if c["type"] == "folder" and c["attrs"].get("personal_toolbar_folder"):
            return c
    for c in root["children"]:
        if c["type"] == "folder":
            return c
    return root


def entries(root):
    """归一化 URL -> (标题, 位置)。位置是内部表示：空串 = 工具栏层（散书签）。

    文件内重复保留首次出现；空 HREF 不参与去重，各给一个占位键。
    """
    out = {}
    n = 0
    for path, bm in walk(toolbar(root)):
        u = normalize_url(bm["href"])
        if not u:
            n += 1
            u = "\x00empty#%d" % n
        if u in out:
            continue
        out[u] = (bm["title"], SEP.join(path))
    return out


def top_folders(root):
    return [c["name"] for c in toolbar(root)["children"] if c["type"] == "folder"]


def route(pos, tops, idx, folder_map, L):
    """规则 4 预判落点：映射表命中 -> 归入语义组 / 一级同名 -> 并入 / 其余 -> 拆平到工具栏末尾。"""
    segs = pos.split(SEP) if pos else []
    canon, _seg = path_group(segs, idx)
    if canon and canon != FLAT_MARKER:
        keys = member_keys(folder_map, canon)
        hit = next((t for t in tops if name_key(t) in keys), None)
        return L["into"].format(name=hit or (canon + L["created"]))
    if segs:
        head = name_key(segs[0])
        for t in tops:
            if name_key(t) == head:
                return L["into"].format(name=t)
    return L["flat_end"]


def build(a_path, a_name, b_path, b_name, L):
    a_root, b_root = parse(a_path), parse(b_path)
    a, b = entries(a_root), entries(b_root)
    tops = top_folders(a_root)
    folder_map = load_folder_map()
    idx = alias_index(folder_map)

    def at(name, pos):
        return "%s%s%s" % (name, SEP, i18n.where(L, pos))

    rows = []
    for u, (t, p) in a.items():
        if u not in b:
            rows.append((t, u, at(a_name, p), at(a_name, p)))
        elif b[u][1] != p:
            rows.append((t, u,
                         "%s ／ %s" % (at(a_name, p), at(b_name, b[u][1])),
                         at(a_name, p)))
    for u, (t, p) in b.items():
        if u not in a:
            rows.append((t, u, at(b_name, p), route(p, tops, idx, folder_map, L)))
    return rows, len(a), len(b)


def render(rows, L):
    out = [L["th_diff"], "| --- | --- | --- | --- |"]
    for i, (t, u, old, new) in enumerate(rows, 1):
        cell = "%s<br>%s" % (t or L["no_title"],
                             u if not u.startswith("\x00empty#") else L["empty_url"])
        out.append("| %d | %s | %s | %s |" % (i, cell, old, new))
    return "\n".join(out)


if __name__ == "__main__":
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default=None, choices=i18n.LANGS)
    ap.add_argument("a_path")
    ap.add_argument("a_name")
    ap.add_argument("b_path")
    ap.add_argument("b_name")
    a = ap.parse_args()
    L = i18n.labels(a.lang)
    rows, na, nb = build(a.a_path, a.a_name, a.b_path, a.b_name, L)
    print(L["diff_summary"].format(a=a.a_name, na=na, b=a.b_name, nb=nb, rows=len(rows)))
    print(render(rows, L))
