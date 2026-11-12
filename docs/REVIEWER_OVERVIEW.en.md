# Overview for reviewers — Parrhesia (formerly Pleroma)

[Back to top](../README.en.md) | [日本語版](./REVIEWER_OVERVIEW.md)

## Summary (3 lines) + reproduce it yourself

**Parrhesia** audits an AI coding agent's commits directly from the **diff** for
five concrete shortcuts (deleting the failing test, adding a skip marker, etc.).
It also audits its own defense code the same way, and has found, fixed, and
recorded 105 defects so far (§3). Detailed working-process notes (signed
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
- Measure a false-positive rate on a large sample of legitimate commits
  (current negative-control coverage is one test file).
- Guarantee that this project's own operational tooling (e.g. certificate
  management) always follows the principles it states. One such self-found
  inconsistency did exist in the past (§2) — it has since been fixed.
- **Claim independent third-party audit.** No independent audit has been done.
  The person who finds each defect (the project's own red-team code) and the
  person who fixes it are the same. This is a real limitation of a solo QA
  research project, and it's stated here first: every one of the 105 entries
  in §3 is a number the author found and fixed themselves.

## 1. Glossary (for a first-time reader)

| Term in this repo | Plain meaning |
| --- | --- |
| **checks/** | CI check scripts: regression tests that mechanically re-verify, on every push, that a previously-found defect hasn't come back. The number actually wired into CI is verified by a script, not counted by hand: [`tools/count_ci_checks.py`](../tools/count_ci_checks.py) (55 as of this writing). |
| **DEFECTS.md** | The raw record of every defect found (sequentially numbered §A–§DA). Each entry is an engineering log entry: how it was found, why, the fix, and how it was verified. |
| **Sanctuary / Sanctum** | This repo's internal name for the isolation mechanism (file-access restriction, network blocking, etc.) used when running AI-generated code. |
| **§A–§DA** | Sequential (alphabetic) IDs for individual defect write-ups in DEFECTS.md (A=1, Z=26, AA=27, ...), verified programmatically, not by hand: [`tools/count_defects_entries.py`](../tools/count_defects_entries.py). |

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
defect stays fixed. DEFECTS.md actually contains **105 entries (§A–§DA, no
gaps or duplicates)**, counted by a script that parses the headings
programmatically (DEVLOG.md's narrative version still says 81 and has not been
updated since).

Those 105 fall into three broad patterns:

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
commit:     f1e9d01
run:        Sanctuary CI/CD — https://github.com/anjo-da-maquina/parrhesia/actions/runs/43179449880
conclusion: success (zero failure-comments)
result:     843 passed, 2 xfailed, 0 xpassed, 2 warnings in 46.78s
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
| [DEFECTS.md](../DEFECTS.md) | §A–§DA, 105 entries, the raw, most detailed record |
| [docs/FAQ.md](./FAQ.md) | Differentiation, limitations, and other Q&A |
| [docs/WHY.md](./WHY.md) | The design rationale for auditing rather than trusting AI agents |
| [docs/BOUNDARY.md](./BOUNDARY.md) | What this project does and does not claim to do |
| [docs/worklog/ai-agent-notes.en.md](./worklog/ai-agent-notes.en.md) | Detailed record of the AI agent's own working process and revision history |
