# Blind-spot signals

Use these as hypotheses, never labels.

| Signal | Observable trace | What may be hidden |
|---|---|---|
| Avoided crux | The same decision is repeatedly deferred while adjacent work expands | A feared trade-off or missing commitment |
| Framework churn | New frameworks replace one another without testing the previous one | Whether any lens improves a decision |
| Single-lens dominance | Different problems are repeatedly reduced through one favored mechanism | Alternative causal structures and boundary cases |
| Untested premise | A recurring "must", "obviously", or fixed boundary has no attempted falsifier | A soft or self-imposed constraint |
| Counterevidence neglect | Supporting material is elaborated while disconfirming evidence stays generic | The strongest way a project could be wrong |
| Grounding displacement | More synthesis substitutes for reading the raw artifact | What the source actually says |
| Verification displacement | More planning or polish substitutes for running the oracle | Whether the work functions at all |
| Adjacent missing question | Repeated outputs improve answers while leaving the load-bearing question untouched | A more consequential decision or unit of analysis |

Do not count a signal when the behavior follows an explicit scope boundary, a rational safety rule, or
missing access. One high-consequence instance may qualify only when its evidence and consequence are both
clear.

## Saved report contract

When saving the final blind-spot report under the suite note contract, use the following fields and run
`python3 scripts/validate_report.py <report.md> --mode daily|weekly`. The validator checks form, not the
truth of the diagnosis.

```markdown
## 今日盲区镜

- **窗口**：<dates and artifact types>
- **判断**：<one blind spot | 证据不足，今日不判盲区>
- **证据**：<anchored observations, or why the window is too thin>
- **被遮住的东西**：<evidence, alternative, or consequence that stayed unseen>
- **反方解释**：<best benign alternative>
- **今日反制动作**：<one bounded action or observation target>
```
