"""Netscape bookmark HTML parsing / writing helpers."""
import json
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

# utf-8-sig covers both BOM and BOM-less UTF-8; gb18030 catches exports from older
# Chinese browsers (360 / QQ / Sogou) that write GBK.
READ_ENCODINGS = ("utf-8-sig", "gb18030")

# BOOKMARK_LIBRARIAN_HOME lets a test (or a portable install) keep its learned table away
# from the real ~/.bookmark-librarian.
USER_MAP_DIR = os.environ.get("BOOKMARK_LIBRARIAN_HOME") or os.path.join(
    os.path.expanduser("~"), ".bookmark-librarian")
USER_MAP_PATH = os.path.join(USER_MAP_DIR, "folder-map.json")
BUILTIN_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "folder-map.json")

# Reserved canonical meaning "asked already — stop asking, use the default routing".
FLAT_MARKER = "_不再询问"

# 位置值的内部表示（写进 merge_stats.json，与界面语言无关）：空串 = 工具栏层（散书签），
# TOOLBAR_END = 被拆平、追加到工具栏末尾。显示时由 i18n.where() 换成文案。
TOOLBAR_END = "@toolbar-end"


def force_utf8_stdout():
    """A Windows console often defaults to cp936; pin stdout/stderr to UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def warn(key, **kw):
    """Warnings are user-facing too. i18n imports this module, so import it lazily."""
    import i18n
    sys.stderr.write(i18n.labels()[key].format(**kw) + "\n")


def read_text(path):
    for enc in READ_ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    warn("warn_encoding", path=path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {"type": "folder", "name": "ROOT", "attrs": {}, "children": []}
        self.stack = [self.root]
        self.cur = None

    def handle_starttag(self, tag, attrs):
        d = {k.lower(): (v or "") for k, v in attrs}
        if tag == "h3":
            node = {"type": "folder", "name": "", "attrs": d, "children": []}
            self.stack[-1]["children"].append(node)
            self.stack.append(node)
            self.cur = node
        elif tag == "a":
            node = {
                "type": "bookmark",
                "title": "",
                "href": d.get("href", ""),
                "attrs": d,
                "children": [],
            }
            self.stack[-1]["children"].append(node)
            self.cur = node

    def handle_endtag(self, tag):
        if tag == "dl":
            if len(self.stack) > 1:
                self.stack.pop()
        self.cur = None

    def handle_data(self, data):
        if self.cur is None:
            return
        if self.cur["type"] == "folder":
            self.cur["name"] += data.strip()
        else:
            self.cur["title"] += data.strip()


def parse(path):
    p = _Parser()
    p.feed(read_text(path))
    p.close()
    return p.root


def normalize_url(u):
    """Rule 1: lowercase scheme + host only. Path / query / fragment stay significant.

    Trailing slash, default ports, `www.` and anchors must NOT be folded away —
    they can point at genuinely different resources, and dedupe is destructive.
    """
    u = (u or "").strip()
    if not u:
        return ""
    p = urlsplit(u)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, p.fragment))


def name_key(name):
    """Folder names compare case-insensitively, ignoring surrounding whitespace."""
    return (name or "").strip().lower()


def _read_map(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        warn("warn_map", path=path, err=e)
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for canon, aliases in data.items():
        if not isinstance(canon, str):
            continue
        if isinstance(aliases, str):
            aliases = [aliases]
        out[canon] = [a for a in (aliases or []) if isinstance(a, str) and a]
    return out


def load_user_map():
    """Only what the user taught, i.e. ~/.bookmark-librarian/folder-map.json."""
    return _read_map(USER_MAP_PATH)


def save_user_map(folder_map):
    os.makedirs(USER_MAP_DIR, exist_ok=True)
    with open(USER_MAP_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(folder_map, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def load_folder_map():
    """{canonical: [alias, ...]} — builtin defaults with the user's table layered on top.

    The user's table wins. An alias it claims is taken away from its builtin group, and a
    builtin group whose own name is claimed disappears entirely. That is how "rename the
    group" works: teaching 影视 as the canonical pulls the whole 影剧 group over to it.
    """
    merged = {}
    for canon, aliases in _read_map(BUILTIN_MAP_PATH).items():
        merged[canon] = list(dict.fromkeys([canon] + aliases))

    user = _read_map(USER_MAP_PATH)
    if not user:
        return merged

    claimed = set()
    for canon, aliases in user.items():
        claimed.add(name_key(canon))
        claimed.update(name_key(a) for a in aliases)

    for canon in list(merged):
        if name_key(canon) in claimed:
            del merged[canon]
            continue
        rest = [a for a in merged[canon] if name_key(a) not in claimed]
        if rest:
            merged[canon] = rest
        else:
            del merged[canon]

    for canon, aliases in user.items():
        bucket = merged.setdefault(canon, [canon])
        for a in [canon] + aliases:
            if a not in bucket:
                bucket.append(a)
    return merged


def alias_index(folder_map):
    """{alias key -> canonical}; the first canonical claiming an alias wins."""
    idx = {}
    for canon, aliases in folder_map.items():
        for a in aliases:
            idx.setdefault(name_key(a), canon)
        idx.setdefault(name_key(canon), canon)
    return idx


def group_members(folder_map, canonical):
    """Every spelling that means this folder, canonical included (original case kept)."""
    for canon, aliases in folder_map.items():
        if name_key(canon) == name_key(canonical):
            return list(dict.fromkeys([canon] + aliases))
    return [canonical]


def member_keys(folder_map, canonical):
    """group_members as comparison keys."""
    return {name_key(a) for a in group_members(folder_map, canonical)}


def user_keys():
    """name_keys the user's own table mentions — how "taught" is told from "builtin"."""
    keys = set()
    for canon, aliases in load_user_map().items():
        keys.add(name_key(canon))
        keys.update(name_key(a) for a in aliases)
    return keys


def path_group(path, idx):
    """(canonical, matched segment) for the first folder on the path a mapping claims."""
    for seg in path:
        canon = idx.get(name_key(seg))
        if canon:
            return canon, seg
    return None, None


def walk(node, path=(), out=None):
    """Yield (folder_path_tuple, bookmark_node)."""
    if out is None:
        out = []
    for c in node["children"]:
        if c["type"] == "folder":
            walk(c, path + (c["name"],), out)
        else:
            out.append((path, c))
    return out


def iter_folders(node, path=()):
    for c in node["children"]:
        if c["type"] == "folder":
            yield path + (c["name"],), c
            yield from iter_folders(c, path + (c["name"],))


def esc(s):
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render(node, indent=1, lines=None):
    if lines is None:
        lines = []
    pad = "    " * indent
    for c in node["children"]:
        if c["type"] == "folder":
            extra = ""
            if c["attrs"].get("personal_toolbar_folder"):
                extra += ' PERSONAL_TOOLBAR_FOLDER="true"'
            if c["attrs"].get("add_date"):
                extra += ' ADD_DATE="%s"' % esc(c["attrs"]["add_date"])
            if c["attrs"].get("last_modified"):
                extra += ' LAST_MODIFIED="%s"' % esc(c["attrs"]["last_modified"])
            lines.append("%s<DT><H3%s>%s</H3>" % (pad, extra, esc(c["name"])))
            lines.append("%s<DL><p>" % pad)
            render(c, indent + 1, lines)
            lines.append("%s</DL><p>" % pad)
        else:
            extra = ""
            for k in ("add_date", "icon", "icon_uri", "last_modified", "last_visit"):
                if c["attrs"].get(k):
                    extra += ' %s="%s"' % (k.upper(), esc(c["attrs"][k]))
            lines.append(
                '%s<DT><A HREF="%s"%s>%s</A>' % (pad, esc(c["href"]), extra, esc(c["title"]))
            )
    return lines


def write_bookmarks(root, out_path, title="Bookmarks"):
    body = render(root)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n")
        f.write(
            "<!-- This is an automatically generated file.\n"
            "     It will be read and overwritten.\n"
            "     DO NOT EDIT! -->\n"
        )
        f.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n')
        f.write("<TITLE>%s</TITLE>\n" % title)
        f.write("<H1>%s</H1>\n" % title)
        f.write("<DL><p>\n")
        for ln in body:
            f.write(ln + "\n")
        f.write("</DL><p>\n")
