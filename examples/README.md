# Example

Inputs are the fixtures in [`../tests/fixtures/`](../tests/fixtures/) — three small
hand-written exports that cover the awkward cases on purpose: duplicate URLs inside one
file, the same URL with different titles, case-variant hosts, `http` vs `https`, a URL
without a trailing slash, empty folders, and a folder the builtin map already knows.

Run from the skill root:

```
python3 scripts/merge.py --dry-run \
  --master Edge \
  Edge=tests/fixtures/favorites_test.html \
  Chrome=tests/fixtures/chrome_test.html \
  华为=tests/fixtures/huawei_test.html

python3 scripts/merge.py \
  --out examples/out --stats examples/out/merge_stats.json \
  --master Edge \
  Edge=tests/fixtures/favorites_test.html \
  Chrome=tests/fixtures/chrome_test.html \
  华为=tests/fixtures/huawei_test.html

python3 scripts/tables.py examples/out/merge_stats.json \
  "examples/out/合并书签_Edge_Chrome_华为.html"
```

The first command writes nothing — it prints the routing plan and the folders it would ask
about (`阅读`, `边界`, `华为`), which is what you would put to the user.

Expected: 14 bookmarks out (19 − 3 in-file duplicates − 2 cross-source duplicates), all
three checks PASS. Expected tables: [`expected-tables.md`](expected-tables.md).

What to look for in the tables:

- `https://github.com/` and `https://github.com` are **different** URLs — the trailing slash is not folded away, so both survive
- `GitHub 副本` has the same URL as `GitHub` but a different title → its own row, marked `文件内重复`
- `花粉俱乐部` appears twice inside the Huawei export → the second copy is dropped, and its 最终位置 is `书签栏` because the unmatched `华为` folder was flattened to the end of the toolbar
- `动漫` (a film folder) was lifted into the master's `影剧`
