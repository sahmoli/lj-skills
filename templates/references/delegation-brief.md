# Delegation brief and acceptance contract

Read this reference when drafting a brief or verifying a returned result.

## Draft a brief

Use the smallest structure that makes the outcome inspectable. Always state the task, minimum state change,
boundaries, acceptance evidence, and delivery. Add rationale, current baseline, assumptions, work units, or
stop conditions only when they resolve a material ambiguity.

```text
【任务】<concrete outcome>
【最小状态变化】<object: A → B>
【边界】<write whitelist; frozen areas; prohibited external or irreversible actions>
【验收】<command, evidence, or named human judgment>
【交付】<artifacts, evidence, and unresolved facts>
```

An execution brief must preserve the starting baseline and forbid changing tests, thresholds, assertions,
or the object under test merely to obtain a pass. An exploration brief must name the decision it informs and
separate evidence, inference, and unknowns. Neither brief authorizes a durable Wiki change, external action,
or irreversible operation.

## Accept returned work

Inspect actual artifacts and rerun the stated acceptance checks. If the original brief cannot be recovered,
report the observable target and evidence, and mark missing acceptance criteria unknown. Summarize pass/fail,
what changed, evidence, remaining risk, and the next decision.

## Provenance

The task-book and anti-gaming ideas were adapted and substantially rewritten from
[`KKKKhazix/khazix-skills/leader`](https://github.com/KKKKhazix/khazix-skills/tree/7e95e25917f9/leader)
(MIT). The delegation gates, research evidence boundary, human ownership rule, and lj-suite routing are
Juan-specific.
