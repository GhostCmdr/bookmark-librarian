"""出表一（数量汇总）和表二（重复明细），只在对话里展示，不落盘。

用法: python3 tables.py <merge_stats.json> <合并书签.html>
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bk_common import force_utf8_stdout, normalize_url, parse, walk  # noqa: E402
import i18n  # noqa: E402

SEP = " - "


def cut(s, n):
    s = (s or "").replace("|", "\\|").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "…"


def load_kept(path, L):
    """合并文件里每个网址实际留下的 (位置, 标题)。"""
    kept = {}
    root = parse(path)
    for p, b in walk(root["children"][0] if root["children"] else root):
        u = normalize_url(b["href"])
        if u and u not in kept:
            kept[u] = (SEP.join(p) or L["toolbar"], b["title"])
    return kept


def table1(d, L):
    labels = {s["key"]: s["label"] for s in d["sources"]}
    one = d["mode"] == "plain" or len(d["sources"]) == 1
    out = [L["th_t1"], "| --- | --- | --- | --- | --- | --- |"]
    tot = [0, 0, 0, 0, 0]
    for s in d["sources"]:
        name = labels[s["key"]]
        if d.get("master") == s["key"]:
            name += L["master_tag"]
        vals = [s["original"], s["in_file_dup"], s["cross_dup"], s["kept"], s["new"]]
        tot = [a + b for a, b in zip(tot, vals)]
        cells = [vals[0], vals[1], vals[2], vals[3], vals[4]]
        if one:
            cells[2] = cells[4] = L["dash"]
        out.append("| %s | %s |" % (name, " | ".join(str(v) for v in cells)))
    tot_cells = [tot[0], tot[1], tot[2], tot[3], tot[4]]
    if one:
        tot_cells[2] = tot_cells[4] = L["dash"]
    out.append("| **%s** | %s |" % (L["t1_total"], " | ".join(str(v) for v in tot_cells)))
    out.append("| %s | %d | %s | %s | %s | %s |"
               % (L["t1_merged"], d["total_merged"], L["dash"], L["dash"], L["dash"], L["dash"]))
    return "\n".join(out)


def table2(d, kept, L):
    labels = {s["key"]: s["label"] for s in d["sources"]}
    fallback = d.get("master") or d["sources"][0]["key"]
    kept_src = {}
    for x in d["dups"]:
        u = normalize_url(x["url"])
        if x["kind"] == "in_file_dup":
            kept_src.setdefault(u, x["source"])
        else:
            kept_src.setdefault(u, fallback)
    for x in d["added_new"]:
        kept_src.setdefault(normalize_url(x["url"]), x["source"])

    loc, order = {}, []
    for x in d["dups"]:
        u = normalize_url(x["url"])
        if u not in loc:
            loc[u] = []
            order.append(u)
        loc[u].append(x)

    def name(k):
        return labels.get(k, k)

    rows = []
    for u in order:
        kpos, ktitle = kept.get(u, (L["not_found"], L["not_found"]))
        ksrc = kept_src.get(u, fallback)
        same, other = [], []
        for x in loc[u]:
            (same if x["title"] == ktitle else other).append(x)
        # 出现位置只写「原文件里的位置」：每条记录给出它被留下的那份和它的副本各自在哪
        pos = []
        for x in loc[u]:
            owner = d.get("master") if x["kind"] == "vs_master_dup" else x["source"]
            pos.append("%s%s%s" % (name(owner), SEP, i18n.where(L, x["kept_at"])))
            pos.append("%s%s%s" % (name(x["source"]), SEP, i18n.where(L, x["path"])))
        label = name(ksrc) + (L["master_tag"] if ksrc == d.get("master") else "")
        rows.append((ktitle, u, "；".join(dict.fromkeys(pos)), label, kpos))
        seen = {}
        for x in other:
            flag = "in_file_dup" if x["source"] == ksrc else "removed"
            seen.setdefault((x["title"], flag), []).append(
                "%s%s%s" % (name(x["source"]), SEP, i18n.where(L, x["path"])))
        for (t, flag), ps in seen.items():
            rows.append((t, u, "；".join(dict.fromkeys(ps)), flag, L["dash"]))

    out = [L["th_t2"], "| --- | --- | --- | --- | --- | --- |"]
    for i, (t, u, p, s, f) in enumerate(rows, 1):
        out.append("| %d | %s | %s | %s | %s | %s |"
                   % (i, cut(t, 60), u, p, L.get(s, s), f))
    return "\n".join(out), rows


if __name__ == "__main__":
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default=None, choices=i18n.LANGS)
    ap.add_argument("stats")
    ap.add_argument("merged")
    a = ap.parse_args()
    L = i18n.labels(a.lang)

    d = json.load(open(a.stats, encoding="utf-8"))
    t2, rows = table2(d, load_kept(a.merged, L), L)
    removed = sum(1 for r in rows if r[3] == "removed")
    in_file = sum(1 for r in rows if r[3] == "in_file_dup")
    print(L["t1_title"] + "\n")
    print(table1(d, L))
    print("\n" + L["t2_title"].format(n=len(rows), removed=removed, in_file=in_file) + "\n")
    print(t2)
