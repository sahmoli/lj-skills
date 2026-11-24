# Whole-book coverage map

Copy this template for each complete book. Record page/chapter/section anchors precisely enough to return
to the source.

## Reading companion and validation

Inside the live Wiki lane, pair the coverage map with a companion in `raw/reading/`. The companion uses
the same timestamp as its coverage file and has this frontmatter and section spine:

```markdown
---
type: reading-companion
genre: 拆书 (lj-book)
lane: raw/reading
status: complete | partial | hypothesis
book: <title>
author: <author>
source: <raw path or verified citation>
created: YYYY-MM-DD
---

- **x**：<problem>
- **f**：<runnable framework or method>
- **f(x)**：<changed judgment or action>

# x：作者在处理什么问题
# f：作者怎样回答，机制如何运行
# f(x)：回答之后怎样重新判断或行动
# Juan 的 delta：零点、位移、保留意见
# 迁移与边界
# 资料校准
```

Run `python3 scripts/validate_note.py <book.md> --coverage <coverage.md>` after a saved companion. A
pass confirms only the mechanical coverage contract.

```markdown
---
type: book-coverage
book: <title>
status: complete | partial
source: <raw path>
---

## Coverage zones

- Introduction/front matter: <anchor + what problem/method the author declares>
- Early setup: <anchor + units/distinctions>
- Middle mechanism: <anchor + how the answer operates>
- Late findings: <anchor + what follows>
- Ending/boundaries: <anchor + limits or unresolved questions>

## Candidate components

| ID | Component | Location | Causal role | Delete breaks reconstruction? | Keep in f? |
|---|---|---|---|---|---|
| C1 | | | question / unit / mechanism / evidence / finding / boundary | yes/no | yes/no |

## Coverage verdict

- Missing zones:
- Material status: full text | substantial excerpts | thin/partial
- Safe claim ceiling:
```
