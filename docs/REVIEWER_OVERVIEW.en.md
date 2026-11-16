# Overview for reviewers — Parrhesia (formerly Pleroma)

[Back to top](../README.en.md) | [日本語版](./REVIEWER_OVERVIEW.md)

## Summary (3 lines) + reproduce it yourself

**Parrhesia** audits an AI coding agent's commits directly from the **diff** for
five concrete shortcuts (deleting the failing test, adding a skip marker, etc.).
It also audits its own defense code the same way, and has found, fixed, and
recorded 107 defects so far (§3). Detailed working-process notes (signed
commits, CI checks, how AI-assistant review feedback was incorporated) live in
a separate worklog (§5).

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```
No network access and no state left behind afterward.

**A note on what kind of claim each statement below is.** There are three kinds:
(1) results quoted from a real GitHub Actions CI run, which has no network
restrictions; (2) results actually run on the user's own Windows machine; (3)
things that could not be verified in the development sandbox this document was
written in (which has no PyPI access and cannot install `rsa`) — each one is
labeled as such.

## 0. What this tool cannot do (4 lines)

- Judge whether a natural-language claim in a comment or PR ("all edge cases
  verified") is actually true — that needs a separate mechanism (a second model
  or a human reviewer).
- Measure a false-positive rate on a large sample of legitimate commits. This
  has now been measured, separately, on two groups of 12 clean diffs each in
  [evals/diff_audit/](../evals/diff_audit/README.en.md): 12 deliberately
  constructed to be misleading (a rename, a skip marker merely moved, or
  drawn from the project's own past commits) were false-flagged 12/12 (rate
  1.000, Wilson 95% CI [0.758, 1.000]), while 12 ordinary legitimate changes
  (a strengthened test, an equivalent refactor, correct exception handling)
  were false-flagged 0/12 (rate 0.000, CI [0.000, 0.242]). A single number
  combining both groups (0.500) is not reported as a headline, since it is
  an artifact of the roughly 50/50 mix the author chose, not a measure of
  the detector's actual performance. The measured pattern — "fooled by
  misleading diffs, passes ordinary ones cleanly" — is real, but the sample
  (12 of each) is still too small to represent the real-world distribution.
  The two specific blind spots behind the misleading-group failures (it
  can't tell a rename from a deletion, or a merely-relocated skip marker
  from a newly added one) were recorded in DEFECTS.md §DC, and
  [as of 2026-11] have since been mostly fixed, following a frozen-data
  before/after comparison on 24 samples created independently of the 12
  used above (rename subgroup: 12/12 → 0/12; skip-move subgroup: 9/12 →
  3/12; full numbers in [DEFECTS.md §DC](../DEFECTS.md)). A narrower
  remaining limitation — a decorator reformatted across multiple lines —
  is still unfixed.
- Guarantee that this project's own operational tooling (e.g. certificate
  management) always follows the principles it states. One such self-found
  inconsistency did exist in the past (§2) — it has since been fixed.
- **Claim independent third-party audit.** No independent audit has been done.
  The person who finds each defect (the project's own red-team code) and the
  person who fixes it are the same. This is a real limitation of a solo QA
  research project, and it's stated here first: every one of the 107 entries
  in §3 is a number the author found and fixed themselves.

## 1. Glossary (for a first-time reader)

| Term in this repo | Plain meaning |
| --- | --- |
| **checks/** | CI check scripts: regression tests that mechanically re-verify, on every push, that a previously-found defect hasn't come back. The number actually wired into CI is verified by a script, not counted by hand: [`tools/count_ci_checks.py`](../tools/count_ci_checks.py) (55 as of this writing). |
| **DEFECTS.md** | The raw record of every defect found (sequentially numbered §A–§DC). Each entry is an engineering log entry: how it was found, why, the fix, and how it was verified. |
| **Runtime Seal / Sandbox** | This repo's internal name for the isolation mechanism (file-access restriction, network blocking, etc.) used when running AI-generated code. |
| **§A–§DC** | Sequential (alphabetic) IDs for individual defect write-ups in DEFECTS.md (A=1, Z=26, AA=27, ...), verified programmatically, not by hand: [`tools/count_defects_entries.py`](../tools/count_defects_entries.py). |

## 2. A known self-inconsistency, found and actually fixed

This toolkit claims "zero trust," yet the helper script that renews its own
certificate weekly (`tools/renew_certificate.ps1`/`.sh`) originally replaced a
step that is supposed to require human, out-of-band confirmation with
automatic approval ([DEFECTS.md §CX](../DEFECTS.md), self-found and recorded).

`tools/promote_provisioning_seal.py` was then given a `--check-rotation` flag
that mechanically checks whether the proposed key is identical to the
currently-trusted key (a simple renewal) or different (an actual trust-root
rotation). The renewal scripts now auto-approve only on the former, and refuse
to auto-approve on the latter, requiring a human to confirm the fingerprint
out-of-band and approve manually ([DEFECTS.md §CZ](../DEFECTS.md), 4 new
regression tests). Two limitations of this fix itself (the trusted key's
storage isn't independent of the automation; a stopped run notifies passively,
not actively) are stated as a threat model in [docs/BOUNDARY.md](./BOUNDARY.md).

## 3. How it keeps finding defects

CI checks under `checks/` mechanically re-check that every previously-found
defect stays fixed. DEFECTS.md actually contains **107 entries (§A–§DC, no
gaps or duplicates)**, counted by a script that parses the headings
programmatically (DEVLOG.md's narrative version still says 81 and has not been
updated since).

Those 107 fall into three broad patterns:

1. **The same bypass exists under a different name** — e.g. a layer blocking
   `import os` was fully bypassed by `import os.path`.
2. **Something that looks approved or learned was never actually wired in** —
   e.g. a human-approved threat record the real enforcement hook never read.
3. **Nobody ever confirmed the safety mechanism actually fires** — e.g. a
   verdict message saying "execution is impossible" next to a process exit code
   that was always 0 (success).

### Three representative entries (reproduction, commit, evidence)

| Entry | What was wrong | Reproduction (actually run) | Fix commit |
| --- | --- | --- | --- |
| [§AV](../DEFECTS.md) — the most surprising find | A nested sandbox's permission scope, meant to only *narrow*, instead *widened* to the entire filesystem. | Opened a child sandbox with `allowed_dirs=["/"]` inside a parent restricted to a jail dir and wrote to `/tmp/` → the write succeeded with no exception (confirmed jailbreak). | [`b9541be`](https://github.com/anjo-da-maquina/parrhesia/commit/b9541be11c8a22f4c14e31832c705035f8acdda2) |
| [§AR](../DEFECTS.md) | A judgment message said "execution is impossible," but the CLI's exit code was always `0` (success). | Ran the CLI on a violating file → the screen shows a rejection, but `echo $?` is always 0. | [`2c32938`](https://github.com/anjo-da-maquina/parrhesia/commit/2c3293818e5602982aa829753cae5868a65868d8) |
| [§CT](../DEFECTS.md) | `socket.getaddrinfo()` (DNS resolution) bypassed both independent defense layers entirely, since it never calls `connect()`. | Called `getaddrinfo()` on a disallowed hostname → nothing blocked it. After the fix, both layers were confirmed to block it. | [`fe8b54f`](https://github.com/anjo-da-maquina/parrhesia/commit/fe8b54f81fdefd912af6dec71322667f7a54b9a0) |

The full record is [DEFECTS.md](../DEFECTS.md); a narrative version is
[DEVLOG.md](../DEVLOG.md).

## 4. Current state of the test suite (measured, with sources)

```
commit:     ef1a05c
run:        Core CI/CD — https://github.com/anjo-da-maquina/parrhesia/actions/runs/43842740138
conclusion: success (zero failure-comments)
result:     871 passed, 2 skipped, 2 xfailed, 2 warnings in 74.48s
            (this is the main test job, verify_ataraxia, in that run. Two
            other jobs, verify_evals_diff_audit_wiring and
            verify_evals_reward_hacking_wiring, ran in parallel within the
            same run and both succeeded — see §6.)
```

Tests depending on the `rsa` key-generation library previously used
`xfail(strict=False)` (tolerate failure where `rsa` is missing). Since whether
`rsa` is available is known before the test even runs rather than being an
unpredictable runtime failure, these were switched to `pytest.mark.skipif`:
environments with `rsa` (CI) now show ordinary `passed`, and environments
without it (the development sandbox) show `skipped` with an explicit reason
([DEFECTS.md §DA](../DEFECTS.md)).

The remaining `2 xfailed` are unrelated to `rsa` — one each in
`test_orchestrator.py`/`test_sandbox.py`, long-standing `strict=True` xfails
for APIs that simply aren't implemented yet. (In the development sandbox, an
additional xfail can occur from the bundled certificate's intentionally
short lifetime — it's designed to require renewal every 7 days. CI is
unaffected because `GITHUB_ACTIONS=true` makes cloud execution itself get
blocked before the certificate's state is even checked.)

The `2 skipped` are the Inspect-task tests for `evals/diff_audit/` and
`evals/reward_hacking/` (§6):
`tests/test_evals_diff_audit.py::test_task_module_importable_when_inspect_ai_present`
and
`tests/test_evals_reward_hacking.py::test_task_module_importable_when_inspect_ai_present`.
They're skipped with an explicit reason because this particular job
(`verify_ataraxia`) does not have `inspect_ai` installed (an optional
dependency, `pip install .[evals]`) — the two jobs that do install it,
`verify_evals_diff_audit_wiring` and `verify_evals_reward_hacking_wiring`,
actually run and pass these same tests within the same CI run. As with
`rsa`, this is a known-in-advance condition, not a flaky failure.

## 5. The human and AI agent's own working process on this project

This project is built jointly by its human owner and Claude (an AI agent built
by Anthropic). Signed commits, CI verification on every change, a disclosed past
process violation, the real-machine debugging of the certificate-automation
script, and how feedback from an AI-assistant review was incorporated into
this very overview are recorded in detail in a separate file:

→ [docs/worklog/ai-agent-notes.en.md](./worklog/ai-agent-notes.en.md)

## 6. Further reading

| Document | Covers |
| --- | --- |
| [README.en.md](../README.en.md) / [README.md](../README.md) | Overview, usage, threat model, design principles |
| [docs/CASE_STUDY.md](./CASE_STUDY.md) | Reproducible demo, including the honest record of its first run scoring 2/5, not 5/5 |
| [DEVLOG.md](../DEVLOG.md) | The defects as a narrative, as of the 81-entry snapshot (see DEFECTS.md for the current count) |
| [DEFECTS.md](../DEFECTS.md) | §A–§DC, 107 entries, the raw, most detailed record |
| [evals/diff_audit/README.en.md](../evals/diff_audit/README.en.md) | An Inspect (`inspect_ai`) diff-audit eval task. The rule-based detector's baseline result (measured, by subgroup, after the §DC detector fix): misleading-clean 2/12 false-flagged (0.167, CI [0.047, 0.448]); ordinary-clean 0/12 false-flagged (0.000, CI [0.000, 0.242]). Before the fix it was 12/12 = 1.000 on the misleading group (the full frozen-data before/after comparison, 24 samples, is in the README's "Detector improvement" section). The combined figure is a mixture artifact and is not used as a headline. `task.py`'s mock-provider wiring check (`inspect eval ... --model mockllm/model`) has been confirmed to actually run to completion in CI's dedicated job `verify_evals_diff_audit_wiring` ([run #43842740138](https://github.com/anjo-da-maquina/parrhesia/actions/runs/43842740138)). Real-model evaluation results are still not run; see the README for the exact commands for the owner to run that with their own API key. |
| [evals/reward_hacking/README.en.md](../evals/reward_hacking/README.en.md) | A reward-hacking eval task using Inspect's sandbox feature (`sandbox="local"`): an agent is asked to fix a bug, and the resulting diff is audited by Parrhesia's own detector for the same 5 shortcuts (deleted test, skip marker, weakened assertion, swallowed exception, hard-coded exit code). Across 20 handmade tasks (expanded from 14 in 2026-11, following a further-improvements request), the reference-diff verification (measured): starting code actually fails 20/20; honest fix passes the test 20/20 with 0/20 false positives; shortcut fix passes the test 20/20. 16 of those are caught by the detector; the other 4 (task15–task18) deliberately exploit detector gaps the detector itself already documents (an except-then-non-pass swallow, a same-count weaker assertion, `importorskip`, a nested exit-code argument) and are *expected* to go undetected — the actual detection result matches `meta.json`'s `expected_shortcut_detected` for all 20/20. `task.py`'s wiring check (a scripted fake agent, no real model call) has been confirmed to actually run to completion in CI's dedicated job `verify_evals_reward_hacking_wiring` ([run #43842740138](https://github.com/anjo-da-maquina/parrhesia/actions/runs/43842740138)) — getting there required actually finding and fixing two real bugs (an absolute-path permission error writing into the sandbox, then contradictory metrics from applying the same patch twice across scorers); see the README's "Honest note" section for the full story. Real-model evaluation results are still not run; see the README for the exact commands for the owner to run that with their own API key. |
| [docs/FAQ.md](./FAQ.md) | Differentiation, limitations, and other Q&A |
| [docs/WHY.md](./WHY.md) | The design rationale for auditing rather than trusting AI agents |
| [docs/BOUNDARY.md](./BOUNDARY.md) | What this project does and does not claim to do |
| [docs/worklog/ai-agent-notes.en.md](./worklog/ai-agent-notes.en.md) | Detailed record of the AI agent's own working process and revision history |
