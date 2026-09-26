"""End-to-end tests for the bookmark-librarian skill.

Runs the shipped scripts (merge.py / map.py / diff.py) against tests/fixtures/ with an
isolated BOOKMARK_LIBRARIAN_HOME, so the assertions measure what the skill actually does
instead of a re-implementation of the rules.

Usage: python3 tests/test_bookmark_librarian.py
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCRIPTS = os.path.join(SKILL, "scripts")
FIX = os.path.join(HERE, "fixtures")
PY = sys.executable

EDGE = os.path.join(FIX, "favorites_test.html")
CHROME = os.path.join(FIX, "chrome_test.html")
HUAWEI = os.path.join(FIX, "huawei_test.html")

# Keep the learned table away from the real ~/.bookmark-librarian before bk_common is imported.
SANDBOX = tempfile.mkdtemp(prefix="bm-import-")
os.environ["BOOKMARK_LIBRARIAN_HOME"] = SANDBOX
sys.path.insert(0, SCRIPTS)
from bk_common import normalize_url, parse  # noqa: E402

TOOLBAR = "书签栏"


def fingerprint(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# 内容指纹而不是字节数：仓库检出时 core.autocrlf 会把 LF 换成 CRLF，字节数会变，
# 但那不算「源文件被改了」，用定值断言会让别人克隆下来就跑不过。
FIXTURE_FP = {p: fingerprint(p) for p in (EDGE, CHROME, HUAWEI)}

MASTER_NO_FILM = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3 ADD_DATE="1700000000" PERSONAL_TOOLBAR_FOLDER="true">收藏夹栏</H3>
    <DL><p>
        <DT><H3 ADD_DATE="1700000000">影视</H3>
        <DL><p>
            <DT><A HREF="https://www.bilibili.com/" ADD_DATE="1700000010">哔哩哔哩</A>
        </DL><p>
    </DL><p>
</DL><p>
"""

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))


class Sandbox:
    """One isolated run: its own learned map + its own output directory."""

    def __init__(self):
        self.home = tempfile.mkdtemp(prefix="bm-home-")
        self.out = tempfile.mkdtemp(prefix="bm-out-")

    def run(self, script, *args):
        env = dict(os.environ, BOOKMARK_LIBRARIAN_HOME=self.home, PYTHONIOENCODING="utf-8",
                   BOOKMARK_LIBRARIAN_LANG="zh")   # 钉住中文，免得跑测人的环境变量影响断言
        p = subprocess.run([PY, os.path.join(SCRIPTS, script)] + list(args),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=env, cwd=self.out)
        return p

    def merge(self, *args):
        return self.run("merge.py", "--out", self.out, *args)

    def merged(self, name="合并书签_Edge_Chrome_华为.html"):
        return os.path.join(self.out, name)

    def stats_path(self, name="merge_stats.json"):
        return os.path.join(self.out, name)

    def stats(self, name="merge_stats.json"):
        import json
        with open(os.path.join(self.out, name), encoding="utf-8") as f:
            return json.load(f)

    def cleanup(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.out, ignore_errors=True)


def read(path):
    """(所有文件夹路径, [(路径, 标题)], 工具栏一级条目) —— 文件夹含空的。"""
    root = parse(path)
    base = root["children"][0] if root["children"] else root
    folders, books = [], []

    def visit(node, prefix):
        for c in node["children"]:
            if c["type"] == "folder":
                p = prefix + (c["name"],)
                folders.append(p)
                visit(c, p)
            else:
                books.append((prefix, c["title"]))

    visit(base, ())
    tops = [("D", c["name"]) if c["type"] == "folder" else ("A", c["title"])
            for c in base["children"]]
    return folders, books, tops


def titles(books, path):
    return [t for p, t in books if p == path]


def walk_all(root):
    base = root["children"][0] if root["children"] else root
    out = []

    def visit(node, prefix):
        for c in node["children"]:
            if c["type"] == "folder":
                visit(c, prefix + (c["name"],))
            else:
                out.append((prefix, c))

    visit(base, ())
    return out


# ---------------------------------------------------------------- A. 主库模式 · 内置映射
def case_master_builtin():
    sb = Sandbox()
    p = sb.merge("--master", "Edge", "Edge=" + EDGE, "Chrome=" + CHROME, "华为=" + HUAWEI)
    folders, books, tops = read(sb.merged())

    check("A·合并成功", p.returncode == 0, p.stderr.strip()[-200:])
    check("A·规则4 同名文件夹逐级并入（开发 = GitHub/MDN/Vue）",
          titles(books, ("开发",)) == ["GitHub", "MDN", "Vue"], str(titles(books, ("开发",))))
    check("A·规则4 内置语义组命中（动漫 → 影剧）",
          titles(books, ("影剧",)) == ["哔哩哔哩", "樱花动漫"], str(titles(books, ("影剧",))))
    check("A·规则4 未匹配文件夹拆平到工具栏末尾",
          tops == [("D", "开发"), ("D", "工具"), ("D", "影剧"), ("A", "百度"), ("A", "少数派"),
                   ("A", "知乎"), ("A", "无斜杠"), ("A", "http版"), ("A", "www版"),
                   ("A", "花粉俱乐部"), ("A", "华为云")], str(tops))
    check("A·规则4 不产生包装文件夹",
          not any(f in ("阅读", "边界", "华为", "Chrome 书签", "华为浏览器") for f in folders)
          and all(len(f) == 1 or f[0] in ("开发", "工具", "影剧") for f in folders), str(folders))
    check("A·规则5 主库空文件夹保留",
          ("开发", "待整理") in folders and ("工具", "空白") in folders)
    check("A·规则5 副库空文件夹不保留", ("开发", "临时") not in folders)
    check("A·规则2 主库优先（GitHub 用主库标题与图标）",
          "GitHub" in titles(books, ("开发",)) and "GitHub 副本" not in titles(books, ("开发",)))

    all_urls = [normalize_url(b["href"]) for _p, b in walk_all(parse(sb.merged()))]
    check("A·校验1 网址全局唯一", len(all_urls) == len(set(all_urls)),
          "%d/%d" % (len(set(all_urls)), len(all_urls)))
    check("A·规则1 边界地址未被误并（斜杠 / http / www）",
          len([u for u in all_urls if u.startswith("https://github.com")]) == 2,
          str([u for u in all_urls if "github.com" in u]))

    d = sb.stats()
    check("A·统计 原始19 / 文件内3 / 跨来源2 / 保留14",
          (d["total_raw"], sum(s["in_file_dup"] for s in d["sources"]),
           sum(s["cross_dup"] for s in d["sources"]), d["total_merged"]) == (19, 3, 2, 14),
          "%s/%s" % (d["total_raw"], d["total_merged"]))
    check("A·统计 原始 − 重复 = 输出",
          d["total_raw"] - d["total_removed"] == d["total_merged"])

    check("A·预案 列出待询问的未匹配文件夹",
          all(x in p.stdout for x in ("阅读", "边界", "华为")) and "待询问" in p.stdout)
    changed = [os.path.basename(p) for p in FIXTURE_FP if fingerprint(p) != FIXTURE_FP[p]]
    check("A·规则7 源文件只读", not changed, str(changed))
    sb.cleanup()


# ---------------------------------------------------------------- B. 主库模式 · 教的规则
def case_master_taught():
    sb = Sandbox()
    sb.run("map.py", "add", "--as", "读书", "阅读")
    sb.run("map.py", "skip", "边界", "华为")
    p = sb.merge("--master", "Edge", "Edge=" + EDGE, "Chrome=" + CHROME, "华为=" + HUAWEI)
    folders, books, tops = read(sb.merged())

    check("B·教的规则生效（阅读 → 读书，主库没有就新建）",
          titles(books, ("读书",)) == ["少数派"] and ("读书",) in folders,
          str(titles(books, ("读书",))))
    check("B·新建的规范文件夹落在工具栏末尾", tops[-1] == ("D", "读书"), str(tops[-1:]))
    check("B·标记「不再询问」的文件夹不再进待询问清单",
          "待询问" not in p.stdout or "边界" not in p.stdout.split("待询问")[-1],
          p.stdout[-300:])
    check("B·被 skip 的文件夹仍按「其余」拆平", ("边界",) not in folders and ("华为",) not in folders)
    sb.cleanup()


# ---------------------------------------------------------------- C. 主库缺组文件夹
def case_master_missing_group_folder():
    sb = Sandbox()
    sb.merge("--master", "Chrome", "Chrome=" + CHROME, "华为=" + HUAWEI)
    folders, books, _tops = read(sb.merged("合并书签_Chrome_华为.html"))

    check("C·主库没有该组文件夹时在工具栏下新建（影剧）",
          ("影剧",) in folders and titles(books, ("影剧",)) == ["樱花动漫"],
          str(titles(books, ("影剧",))))
    check("C·主库原有内容顺序不变",
          titles(books, ("开发",))[:3] == ["GitHub", "掘金", "Vue"], str(titles(books, ("开发",))))
    sb.cleanup()


# ---------------------------------------------------------------- D. 主库的别名文件夹名优先
def case_master_name_wins():
    sb = Sandbox()
    master = os.path.join(sb.out, "master_影视.html")
    with open(master, "w", encoding="utf-8") as f:
        f.write(MASTER_NO_FILM)
    sb.merge("--master", "Edge", "Edge=" + master, "华为=" + HUAWEI)
    folders, books, _tops = read(sb.merged("合并书签_Edge_华为.html"))

    check("D·主库已有同组成员文件夹时用主库的名字（影视，不新建影剧）",
          ("影视",) in folders and ("影剧",) not in folders
          and titles(books, ("影视",)) == ["哔哩哔哩", "樱花动漫"],
          str(titles(books, ("影视",))))
    sb.cleanup()


# ---------------------------------------------------------------- E. 无主库 · 未确认的组
def case_plain_unconfirmed():
    sb = Sandbox()
    p = sb.merge("Edge=" + EDGE, "Chrome=" + CHROME, "华为=" + HUAWEI)
    folders, books, _tops = read(sb.merged())

    check("E·无主库 同名文件夹仍按名字合并",
          titles(books, ("开发",)) == ["GitHub", "MDN", "Vue"], str(titles(books, ("开发",))))
    check("E·无主库 未确认的语义组不擅自改名（动漫 原样保留）",
          ("动漫",) in folders and titles(books, ("动漫",)) == ["樱花动漫"]
          and titles(books, ("影剧",)) == ["哔哩哔哩"], str(folders))
    check("E·无主库 空文件夹全部保留（待整理 / 空白 / 临时）",
          all(x in folders for x in (("开发", "待整理"), ("工具", "空白"), ("开发", "临时"))),
          str(folders))
    check("E·无主库 不产生包装文件夹",
          not any(f in ("Chrome 书签", "华为浏览器") for f in folders), str(folders))
    check("E·无主库 预案里问用户规范名（影剧 vs 动漫）",
          "待询问" in p.stdout and "动漫" in p.stdout and "影剧" in p.stdout)
    d = sb.stats()
    check("E·无主库 统计口径 19/3/2", (d["total_raw"], d["total_merged"]) == (19, 14),
          "%s/%s" % (d["total_raw"], d["total_merged"]))
    check("E·无主库 表一的跨来源重复与新增并入记 —",
          d["mode"] == "plain" and d["master"] is None)
    sb.cleanup()


# ---------------------------------------------------------------- F. 无主库 · 确认过的组
def case_plain_confirmed():
    sb = Sandbox()
    sb.run("map.py", "confirm", "影剧")
    sb.merge("Edge=" + EDGE, "Chrome=" + CHROME, "华为=" + HUAWEI)
    folders, books, _tops = read(sb.merged())

    check("F·确认后语义组生效（影剧 = 哔哩哔哩 + 樱花动漫）",
          titles(books, ("影剧",)) == ["哔哩哔哩", "樱花动漫"] and ("动漫",) not in folders,
          str(titles(books, ("影剧",))))
    sb.cleanup()


# ---------------------------------------------------------------- G. 单文件模式
def case_single_file():
    sb = Sandbox()
    sb.merge("Edge=" + EDGE)
    _folders, books, _tops = read(sb.merged("合并书签_Edge.html"))
    d = sb.stats()

    check("G·单文件只做文件内去重（6 → 5）", len(books) == 5 and d["total_merged"] == 5,
          str(len(books)))
    check("G·单文件 表一跨来源两列记 —",
          all(s["cross_dup"] == 0 and s["new"] == 0 for s in d["sources"]))
    sb.cleanup()


# ---------------------------------------------------------------- H. 映射表覆盖语义
def case_map_overlay():
    sb = Sandbox()
    sb.run("map.py", "add", "--as", "影视", "电影")
    p = sb.run("map.py", "list")
    rows = [l for l in p.stdout.splitlines() if l.startswith("| ")]
    film = [r for r in rows if r.startswith("| 影视 ")]
    old = [r for r in rows if r.startswith("| 影剧 ")]

    check("H·改规范名会把整组吸收过来（影视 一组含电影/动漫/影剧）",
          bool(film) and all(x in film[0] for x in ("电影", "动漫", "影剧")), str(film))
    check("H·被吸收的旧规范名不再是单独一组", not old, str(old))

    # 主库没有影剧时，落点应跟着新的规范名走
    master = os.path.join(sb.out, "master_nofilm.html")
    with open(master, "w", encoding="utf-8") as f:
        f.write(MASTER_NO_FILM)
    sb.merge("--master", "Edge", "Edge=" + master, "华为=" + HUAWEI)
    folders, books, _tops = read(sb.merged("合并书签_Edge_华为.html"))
    check("H·改过的规范名决定新建的文件夹名",
          ("影视",) in folders and titles(books, ("影视",)) == ["哔哩哔哩", "樱花动漫"],
          str(folders))

    sb.run("map.py", "remove", "电影")
    p = sb.run("map.py", "list")
    check("H·remove 能从用户表里撤掉别名", "| 影视 |" not in p.stdout or "电影" not in p.stdout,
          p.stdout)
    sb.cleanup()


# ---------------------------------------------------------------- I. 差异表
def case_diff():
    sb = Sandbox()
    p = sb.run("diff.py", CHROME, "Chrome", EDGE, "Edge")
    check("I·差异表按规则 4 预判落点",
          "最终保存位置" in p.stdout and "并入 开发" in p.stdout and "拆平到工具栏末尾" in p.stdout,
          p.stdout[-400:])
    sb.cleanup()


# ---------------------------------------------------------------- J. 多语言
def case_language():
    sb = Sandbox()
    p = sb.merge("--lang", "en", "--master", "Edge", "Edge=" + EDGE,
                 "Chrome=" + CHROME, "华为=" + HUAWEI)
    check("J·merge --lang en 预案/校验/收尾都出英文",
          all(x in p.stdout for x in ("Routing plan", "check 1", "Merged file")),
          p.stdout[-300:])

    t = sb.run("tables.py", "--lang", "en", sb.stats_path(), sb.merged())
    check("J·tables --lang en 出英文表一表二",
          "Table 1 · Counts" in t.stdout and "In-file duplicates" in t.stdout
          and "Table 2" in t.stdout, t.stdout[-300:])

    m = sb.run("map.py", "--lang", "en", "list")
    check("J·map --lang en 出英文映射表",
          "Canonical folder" in m.stdout and "Builtin:" in m.stdout, m.stdout[:200])

    d = sb.run("diff.py", "--lang", "en", CHROME, "Chrome", EDGE, "Edge")
    check("J·diff --lang en 出英文差异表",
          "Final location" in d.stdout and "flatten to the end of the toolbar" in d.stdout,
          d.stdout[-300:])

    # 语言只动文案：merge_stats.json 的结构与取值必须仍是稳定 ASCII id
    st = sb.stats()
    kinds = {x["kind"] for x in st["dups"] + st["added_new"]}
    check("J·数据契约不随语言变（kind 用稳定 id）",
          kinds <= {"in_file_dup", "vs_master_dup", "merged_in"} and st["mode"] == "master",
          str(sorted(kinds)))
    check("J·输出文件名不随语言变",
          os.path.isfile(sb.merged()), sb.merged())
    sb.cleanup()


def main():
    for case in (case_master_builtin, case_master_taught, case_master_missing_group_folder,
                 case_master_name_wins, case_plain_unconfirmed, case_plain_confirmed,
                 case_single_file, case_map_overlay, case_diff, case_language):
        try:
            case()
        except Exception as e:                                   # noqa: BLE001
            check("%s 抛异常" % case.__name__, False, "%s: %s" % (type(e).__name__, e))

    print("=" * 72)
    print("bookmark-librarian 端到端测试报告")
    print("=" * 72)
    passed = 0
    for name, ok, detail in RESULTS:
        print("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("   [%s]" % detail) if detail else ""))
        passed += 1 if ok else 0
    print("-" * 72)
    print("合计: %d/%d 通过" % (passed, len(RESULTS)))
    shutil.rmtree(SANDBOX, ignore_errors=True)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
