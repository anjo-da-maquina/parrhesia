# Overview for reviewers — Parrhesia (formerly Pleroma)

[Back to top](../README.en.md) | [日本語版](./REVIEWER_OVERVIEW.md)

**A note on what kind of claim each statement below is.** There are three kinds:
(1) results quoted from a real GitHub Actions CI run, which has no network
restrictions; (2) results actually run on the user's own Windows machine; (3)
things that could not be verified in the sandbox this document was written in
(each one is labeled as such). There is no single blanket claim that "everything
here was run and checked."

## 0. Up front: what this tool cannot detect (3 lines)

- Whether a natural-language claim in a comment or PR ("all edge cases
  verified") is actually true — that needs a separate mechanism (a second model
  or a human reviewer).
- A measured false-positive rate on a large sample of legitimate commits
  (current negative-control coverage is one test file).
- A guarantee that this project's own operational tooling (e.g. certificate
  management) always follows the principles it states. In fact, one known
  inconsistency exists (see §2).

## 1. Glossary (for a first-time reader)

| Term in this repo | Plain meaning |
| --- | --- |
| **angels/** | About 55 CI checks: regression tests that mechanically re-verify, on every push, that a previously-found defect hasn't come back. |
| **GRIMOIRE.md** | The raw record of every defect found (sequentially numbered §A–§CX). Each entry is an engineering log entry: how it was found, why, the fix, and how it was verified. |
| **Sanctuary / Sanctum** | This repo's internal name for the isolation mechanism (file-access restriction, network blocking, etc.) used when running AI-generated code. |
| **§A–§CX** | Sequential (alphabetic) IDs for individual defect write-ups in GRIMOIRE.md. E.g. §AV is the 32nd entry, §CX is the 101st. |

## 2. What this project does

**Parrhesia** audits the commits an AI coding agent produces, directly from the
diff, for five concrete shortcuts agents take under time pressure: deleting the
failing test, adding a skip marker, weakening an assertion, swallowing an
exception, and hardcoding an exit code.

The project also turns the same scrutiny on itself: its own zero-trust runtime
guard is continuously attacked by its own red-team code, and every defect that
red-team finds gets written up and converted into a permanent regression check.
That self-application is the project's main piece of evidence.

- Details: [README.en.md](../README.en.md) / [README.md (Japanese)](../README.md)
- A reproducible demo with real output: [docs/CASE_STUDY.md](./CASE_STUDY.md)

### 2.1 A known self-inconsistency (disclosed, not hidden)

This toolkit claims "zero trust," yet the helper script that renews its own
certificate weekly (`tools/renew_certificate.ps1`/`.sh`) replaces a step that is
supposed to require human, out-of-band confirmation with automatic approval.
Running it produces a log showing the trust root's (public key's) fingerprint
changing on every run.

Rather than hide this, it is recorded as a **self-found defect**:
[GRIMOIRE.md §CX](../GRIMOIRE.md), with a corresponding entry added to
[docs/BOUNDARY.md](./BOUNDARY.md)'s known limitations. A permanent fix (keeping
the out-of-band check outside the automation, or technically enforcing a
single-trusted-device assumption) is not yet implemented as of this writing.
This is placed near the top because it's the first thing a reviewer should
check when judging this project's internal consistency.

## 3. How it keeps finding defects

CI checks under `angels/` mechanically re-check that every previously-found
defect stays fixed. As of this writing, GRIMOIRE.md actually contains **101
entries (§A–§CX)**, counted directly (DEVLOG.md's narrative version still says
81 and has not been updated since; that document now notes this explicitly).

Those 101 fall into three broad patterns:

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
| [§AV](../GRIMOIRE.md) — the most surprising find | A nested sandbox's permission scope, meant to only *narrow*, instead *widened* to the entire filesystem. A direction-of-containment bug in the merge logic let a child declaring `allowed_dirs=["/"]` inside a parent `allowed_dirs=["jail_workspace"]` promote the effective scope to `/`. | Opened a child `Sanctum(allowed_dirs=["/"])` inside a parent `Sanctum(allowed_dirs=["jail_workspace"])` and wrote to `/tmp/` → the write succeeded with no exception (confirmed jailbreak). Fixed; 5 new tests in `tests/test_sanctum_nested_allowed_dirs_widening.py`. | [`b9541be`](https://github.com/anjo-da-maquina/parrhesia/commit/b9541be11c8a22f4c14e31832c705035f8acdda2) |
| [§AR](../GRIMOIRE.md) | A judgment message said "execution is impossible," but the CLI's exit code was always `0` (success). A caller could never detect a violation from the exit code. | Ran `python src/kamael_judgment.py <violating file>` → the screen shows a rejection, but `echo $?` is always 0. | [`2c32938`](https://github.com/anjo-da-maquina/parrhesia/commit/2c3293818e5602982aa829753cae5868a65868d8) |
| [§CT](../GRIMOIRE.md) | `socket.getaddrinfo()` (DNS resolution) bypassed both independent defense layers entirely, since it never calls `connect()`. Secret data could be exfiltrated by encoding it into a subdomain label and resolving it (classic DNS exfiltration). | Called `getaddrinfo()` on a disallowed hostname (`"<secret>.attacker.example.com"`) → nothing blocked it; it only failed with the sandbox's own DNS-unreachable OS error (proof nothing was actually enforced). After the fix, the full DNS-exfiltration chain was reproduced and confirmed blocked on both layers. | [`fe8b54f`](https://github.com/anjo-da-maquina/parrhesia/commit/fe8b54f81fdefd912af6dec71322667f7a54b9a0) → real-CI confirmation [`90e0c1a`](https://github.com/anjo-da-maquina/parrhesia/commit/90e0c1a85ecb66aef1e1d1b9ef8ef4e7d4bff974) |

The full record is [GRIMOIRE.md](../GRIMOIRE.md); a narrative version is
[DEVLOG.md](../DEVLOG.md).

## 4. Current state of the test suite (measured, with sources)

### On CI (no network restrictions)

```
commit:     f83a17a
run:        Sanctuary CI/CD — https://github.com/anjo-da-maquina/parrhesia/actions/runs/43173405996
conclusion: success (zero failure-comments)
result:     828 passed, 2 xfailed, 11 xpassed, 2 warnings in 43.59s
```

The 11 `xpassed` are intentional. They belong to tests depending on the `rsa`
library (e.g. one to four each in `tests/test_guard_ctypes_dlsym_bypass.py`,
`tests/test_gatekeeper_ctypes_dlsym_bypass_guard.py`,
`tests/test_thread_safety_maquina_seal.py`,
`tests/test_openai_agent_loop_template.py`). The sandbox this document is
written in has no PyPI access and cannot install `rsa`, so those tests carry a
documented `pytest.mark.xfail(strict=False)` there. On CI, where `rsa` actually
installs, they simply pass — reported as `xpassed`, and `strict=False` means
this never turns CI red. **This is a record of an environment difference, not
evidence that more xpasses are better** — in any third-party environment with
`rsa` installed, these 11 would just show as ordinary `passed`.

The remaining `2 xfailed` are unrelated to `rsa`:
`tests/test_orchestrator.py::test_orchestrator_initialization` (reason:
"Orchestrator API is pending implementation") and
`tests/test_sandbox.py::test_docker_sandbox_isolation` (reason: "DockerSandbox
implementation is pending") — both long-standing `strict=True` xfails for
features that simply aren't implemented yet.

### In this exact sandbox (actually fixed during this review)

This sandbox has no `rsa` installed and no PyPI access (confirmed by actually
running `pip install rsa`, which failed with a DNS resolution error). Before
this review, that meant `tests/conftest.py` itself failed to import, which
**stopped test collection for the entire suite** (confirmed by actually running
`python3 -m pytest`: exit code 4, zero tests run).

This was fixed as part of responding to this review (wrapping the import in
`tests/conftest.py` in a try/except, and adding `pytest.importorskip("rsa")` to
the handful of files that import `runtime_audit_gatekeeper` unconditionally).
Re-running the exact same sandbox afterward gives (actually run, not estimated):

```
$ python3 -m pytest -q
825 passed, 1 failed, 1 skipped, 14 xfailed, 62 warnings in 28.26s
```

- **1 failed**:
  `tests/test_pre_commit_secret_scan.py::test_preexisting_secret_in_unchanged_lines_is_not_reflagged`.
  Not a code defect — a known, sandbox-specific flake (the git-signing symlink
  `/tmp/code-sign` occasionally disappears, breaking `git commit` inside this
  one test). Confirmed the symlink was indeed missing.
- **1 skipped**: `tests/test_audit_hook_registration_fails_closed.py` (depends
  on `rsa`, skipped with an explicit reason).
- **14 xfailed**: mostly the same documented `rsa`-dependent environment gap,
  plus one unrelated to this review (a genuinely expired test certificate).

## 5. The human and AI agent's own working process on this project

This project is built jointly by its human owner and Claude (an AI agent built
by Anthropic). Signed commits, CI verification on every change, a disclosed past
process violation, and a three-round real-machine debugging session for the
certificate-automation script are recorded in detail in a separate file:

→ [docs/worklog/ai-agent-notes.en.md](./worklog/ai-agent-notes.en.md)

## 6. Further reading

| Document | Covers |
| --- | --- |
| [README.en.md](../README.en.md) / [README.md](../README.md) | Overview, usage, threat model, design principles |
| [docs/CASE_STUDY.md](./CASE_STUDY.md) | Reproducible demo, including the honest record of its first run scoring 2/5, not 5/5 |
| [DEVLOG.md](../DEVLOG.md) | The defects as a narrative, as of the 81-entry snapshot (see GRIMOIRE.md for the current count) |
| [GRIMOIRE.md](../GRIMOIRE.md) | §A–§CX, 101 entries, the raw, most detailed record |
| [docs/FAQ.md](./FAQ.md) | Differentiation, limitations, and other Q&A |
| [docs/WHY.md](./WHY.md) | The design rationale for auditing rather than trusting AI agents |
| [docs/BOUNDARY.md](./BOUNDARY.md) | What this project does and does not claim to do (including the §CX inconsistency) |
| [docs/worklog/ai-agent-notes.en.md](./worklog/ai-agent-notes.en.md) | Detailed record of the AI agent's own working process |

## 7. Reproduce it yourself

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```

No network access and no state left behind afterward. Even without `rsa`,
`python3 -m pytest` now collects and runs the whole suite (see §4).
