# bookmark-librarian

把多个浏览器的书签导出文件合并成一份，以指定主库为准去重。纯 Python 3 标准库 —— 无依赖、
无网络，Windows / macOS / Linux 通用。

> English version: [README.md](README.md)

## 功能

- 解析 Netscape 书签 HTML —— 所有浏览器导出的都是这个格式
- 按完整 URL 去重，主库那份的副本、顺序、标题、图标、日期原样保留
- 其余条目按**文件夹映射表**归置：同义的文件夹合并成一个，同名的逐级并入，剩下的拆平到工具栏末尾
- **会记住** —— 你对文件夹归类的回答会被存下来，同样的问题不会问第二次
- **中英双语** —— `--lang zh|en` 只改文案，别的都不动
- 输出一份合并文件，并打印两张统计表（条数、重复明细）

## 安装

```
npx skills add GhostCmdr/bookmark-librarian
```

本技能遵循 [Agent Skills](https://agentskills.io/specification) 开放格式，同一个文件夹在各家
agent 上通用 —— `skills` CLI 会自动探测你装了哪些并完成配置。

手动安装：克隆到你的 agent 读取的目录，文件夹名保持 `bookmark-librarian`：

| Agent | 路径 |
| --- | --- |
| 任意 Agent Skills 客户端 | `.agents/skills/bookmark-librarian/` |
| Claude Code | `~/.claude/skills/bookmark-librarian/` |
| TraeCode | `.trae/skills/bookmark-librarian/`（项目）· `~/.trae-cn/skills/bookmark-librarian/`（全局） |
| Cursor | `.cursor/rules/bookmark-librarian.mdc` |
| 其他 / 不确定 | 把 `SKILL.md` 的内容贴进 `AGENTS.md` |

## 用法

```
python3 scripts/merge.py --master Edge Edge=favorites.html Chrome=bookmarks.html
python3 scripts/tables.py merge_stats.json 合并书签_Edge_Chrome.html
```

- `--master <名称>` —— 以哪个来源为准。省略即无主库模式（各来源平等，完整保留文件夹层级）
- `--out <目录>` —— 合并文件的落点，默认桌面
- `--dry-run` —— 只打印归置预案和待询问清单，不写任何文件
- `--lang zh|en` —— 所有打印文案的语言，默认 `zh`
- 只给一个来源 → 仅做文件内去重
- 不合并、只比较两个导出文件：`python3 scripts/diff.py A.html Edge B.html Chrome`

合并文件是唯一的交付物；两张表只打印到对话里。

文件夹归类是数据而非代码：`scripts/folder-map.json` 是内置默认，`~/.bookmark-librarian/folder-map.json`
记住你教过的。完整规则见 `SKILL.md`，可运行示例见 `examples/`。

## 测试

```
python3 tests/test_bookmark_librarian.py
```

## 许可

MIT —— 见 [LICENSE](LICENSE)。
