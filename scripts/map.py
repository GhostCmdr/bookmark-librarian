"""管理「文件夹映射表」——决定副库里哪些文件夹名算同一类，归到哪个文件夹。

两层：内置默认在 scripts/folder-map.json（随技能走），用户教过的存在
~/.bookmark-librarian/folder-map.json（不进仓库，可用 BOOKMARK_LIBRARIAN_HOME 换位置）。
用户的表优先：它认领的别名会从内置组里拿走，内置组的规范名被认领时整组消失——
所以「改规范名」就是把新名字和旧组的名字一起教一遍。

用法:
  python3 map.py [--lang zh|en] list                        看当前生效的全部映射
  python3 map.py [--lang zh|en] add --as <规范名> <别名>…    把这些名字归成一组，规范名是 <规范名>
  python3 map.py [--lang zh|en] confirm <规范名>             内置组按现在的规范名记成「我认了」，以后不再问
  python3 map.py [--lang zh|en] skip <别名>…                 记成「不要再问，按默认处理」
  python3 map.py [--lang zh|en] remove <别名>                从用户表里删掉一个别名（内置默认删不掉）
"""
import sys

from bk_common import (
    BUILTIN_MAP_PATH,
    FLAT_MARKER,
    USER_MAP_PATH,
    alias_index,
    force_utf8_stdout,
    load_folder_map,
    load_user_map,
    name_key,
    save_user_map,
)
import i18n


def cmd_list(L):
    fmap = load_folder_map()
    user = load_user_map()
    print(L["map_builtin"].format(path=BUILTIN_MAP_PATH))
    print(L["map_user"].format(path=USER_MAP_PATH) + ("" if user else L["map_user_missing"]))
    if not fmap:
        print(L["map_empty"])
        return 0
    print()
    print(L["th_map"])
    print("| --- | --- | --- |")
    for canon in sorted(fmap, key=name_key):
        aliases = [a for a in fmap[canon] if name_key(a) != name_key(canon)]
        if canon == FLAT_MARKER:
            print("| %s | %s | %s |" % (FLAT_MARKER, "、".join(aliases) or L["dash"],
                                        L["map_src_user"]))
            continue
        src = L["map_src_user"] if canon in user else L["map_src_builtin"]
        print("| %s | %s | %s |" % (canon, "、".join(aliases) or L["dash"], src))
    return 0


def cmd_add(aliases, canonical, L):
    """把这些别名归到规范名名下；碰到已有组就把整组吸收过来。"""
    aliases = [a for a in aliases if a and name_key(a) != name_key(canonical)]
    if not canonical:
        print(L["map_usage"])
        return 2
    fmap = load_folder_map()
    idx = alias_index(fmap)
    absorb = set()
    for a in aliases + [canonical]:
        g = idx.get(name_key(a))
        if g and name_key(g) != name_key(canonical) and g != FLAT_MARKER:
            absorb.update(fmap.get(g, [g]))
    user = load_user_map()
    bucket = user.setdefault(canonical, [])
    for a in aliases + sorted(absorb, key=name_key):
        if a not in bucket:
            bucket.append(a)
    save_user_map(user)
    print(L["map_added"].format(canonical=canonical,
                                aliases="、".join(bucket) or L["map_only_itself"]))
    if absorb:
        print(L["map_absorbed"].format(names="、".join(sorted(absorb, key=name_key))))
    print(L["map_written"].format(path=USER_MAP_PATH))
    return 0


def cmd_confirm(canonical, L):
    """把内置组按当前规范名记成用户已确认，无主库模式下才会生效。"""
    fmap = load_folder_map()
    idx = alias_index(fmap)
    g = idx.get(name_key(canonical))
    if not g or g == FLAT_MARKER:
        print(L["map_no_group"].format(name=canonical))
        return 1
    members = [a for a in fmap.get(g, [g]) if name_key(a) != name_key(g)]
    user = load_user_map()
    bucket = user.setdefault(g, [])
    for a in members:
        if a not in bucket:
            bucket.append(a)
    save_user_map(user)
    print(L["map_confirmed"].format(group=g, aliases="、".join(bucket) or L["map_only_itself"]))
    print(L["map_written"].format(path=USER_MAP_PATH))
    return 0


def cmd_skip(aliases, L):
    """记成「不要再问」，主库模式按「其余」拆平，无主库模式原样保留。"""
    aliases = [a for a in aliases if a]
    if not aliases:
        print(L["map_usage"])
        return 2
    user = load_user_map()
    bucket = user.setdefault(FLAT_MARKER, [])
    for a in aliases:
        if a not in bucket:
            bucket.append(a)
    save_user_map(user)
    print(L["map_skipped"].format(names="、".join(aliases)))
    print(L["map_written"].format(path=USER_MAP_PATH))
    return 0


def cmd_remove(alias, L):
    user = load_user_map()
    hit = False
    for canon in list(user):
        if alias in user[canon]:
            user[canon].remove(alias)
            hit = True
            if not user[canon]:
                del user[canon]
    if not hit:
        print(L["map_not_in_user"].format(alias=alias))
        return 1
    save_user_map(user)
    print(L["map_removed"].format(alias=alias))
    return 0


def strip_lang(args):
    """抠出 --lang（i18n 也认 BOOKMARK_LIBRARIAN_LANG），其余原样返回给子命令。"""
    out, lang = [], None
    i = 0
    while i < len(args):
        if args[i] == "--lang" and i + 1 < len(args):
            lang = args[i + 1]
            i += 2
            continue
        out.append(args[i])
        i += 1
    return out, lang


def main():
    force_utf8_stdout()
    args, lang = strip_lang(sys.argv[1:])
    L = i18n.labels(lang)
    if not args or args[0] in ("-h", "--help", "help"):
        print(L["map_usage"])
        return 0
    cmd = args[0]
    if cmd == "list" and len(args) == 1:
        return cmd_list(L)
    if cmd == "add":
        if "--as" not in args:
            print(L["map_usage"])
            return 2
        i = args.index("--as")
        aliases = args[1:i] + args[i + 2:]
        if i + 1 >= len(args):
            print(L["map_usage"])
            return 2
        return cmd_add(aliases, args[i + 1], L)
    if cmd == "confirm" and len(args) == 2:
        return cmd_confirm(args[1], L)
    if cmd == "skip" and len(args) >= 2:
        return cmd_skip(args[1:], L)
    if cmd == "remove" and len(args) == 2:
        return cmd_remove(args[1], L)
    print(L["map_usage"])
    return 2


if __name__ == "__main__":
    sys.exit(main())
