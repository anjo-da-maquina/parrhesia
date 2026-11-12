# Overview for reviewers — Parrhesia (formerly Pleroma)

[Back to top](../README.en.md) | [日本語版](./REVIEWER_OVERVIEW.md)

## Summary (3 lines) + reproduce it yourself

**Parrhesia** audits an AI coding agent's commits directly from the **diff** for
five concrete shortcuts (deleting the failing test, adding a skip marker, etc.).
It also audits its own defense code the same way, and has found, fixed, and
recorded 105 defects so far (§3). This overview itself has been rewritten twice
in response to external review feedback (see the worklog in §5).

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```
No network access and no state left behind afterward.

**A note on what kind of claim each statement below is.** There are three kinds:
(1) results quoted from a real GitHub Actions CI run, which has no network
restrictions; (2) results actually run on the user's own Windows machine; (3)
things that could not be verified in the sandbox this document was written in
(each one is labeled as such). There is no single blanket claim that "everything
here was run and checked."

## 0. What this tool cannot detect (3 lines)

- Whether a natural-language claim in a comment or PR ("all edge cases
  verified") is actually true — that needs a separate mechanism (a second model
  or a human reviewer).
- A measured false-positive rate on a large sample of legitimate commits
  (current negative-control coverage is one test file).
- A guarantee that this project's own operational tooling (e.g. certificate
  management) always follows the principles it states. One such self-found
  inconsistency did exist in the past (§2.1) — it has since been fixed.

## 1. Glossary (for a first-time reader)

| Term in this repo | Plain meaning |
| --- | --- |
| **angels/** | About 55 CI checks: regression tests that mechanically re-verify, on every push, that a previously-found defect hasn't come back. |
| **GRIMOIRE.md** | The raw record of every defect found (sequentially numbered §A–§DA). Each entry is an engineering log entry: how it was found, why, the fix, and how it was verified. |
| **Sanctuary / Sanctum** | This repo's internal name for the isolation mechanism (file-access restriction, network blocking, etc.) used when running AI-generated code. |
| **§A–§DA** | Sequential (alphabetic) IDs for individual defect write-ups in GRIMOIRE.md (A=1, Z=26, AA=27, AZ=52, BA=53, ...). E.g. §AV is the 48th entry, §CX is the 102nd. The count is verified programmatically, not by hand: [`tools/count_grimoire_entries.py`](../tools/count_grimoire_entries.py). |

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

### 2.1 A known self-inconsistency, found and actually fixed

This toolkit claims "zero trust," yet the helper script that renews its own
certificate weekly (`tools/renew_certificate.ps1`/`.sh`) originally replaced a
step that is supposed to require human, out-of-band confirmation with automatic
approval. Running it produced a log showing the trust root's (public key's)
fingerprint changing on every run.

Rather than hide this, it was recorded as a **self-found defect**:
[GRIMOIRE.md §CX](../GRIMOIRE.md). Following external review feedback that
"finding and recording it is good, but actually fixing it would be stronger
evidence," `tools/promote_provisioning_seal.py` was given a `--check-rotation`
flag that mechanically checks whether the proposed key is identical to the
currently-trusted key (a simple renewal) or different (an actual trust-root
rotation). The renewal scripts now auto-approve only on the former, and refuse
to auto-approve on the latter, requiring a human to confirm the fingerprint
out-of-band and approve manually
([GRIMOIRE.md §CZ](../GRIMOIRE.md), with 4 new regression tests). The full
timeline — discovery, then the actual fix — is recorded honestly in both
GRIMOIRE entries and reflected in [docs/BOUNDARY.md](./BOUNDARY.md).

## 3. How it keeps finding defects

CI checks under `angels/` mechanically re-check that every previously-found
defect stays fixed. As of this writing, GRIMOIRE.md actually contains **105
entries (§A–§DA, no gaps or duplicates)**, counted by a script that parses the
headings programmatically rather than by hand
([`tools/count_grimoire_entries.py`](../tools/count_grimoire_entries.py))
(DEVLOG.md's narrative version still says 81 and has not been updated since;
that document now notes this explicitly).

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
| [§AV](../GRIMOIRE.md) — the most surprising find | A nested sandbox's permission scope, meant to only *narrow*, instead *widened* to the entire filesystem. A direction-of-containment bug in the merge logic let a child declaring `allowed_dirs=["/"]` inside a parent `allowed_dirs=["jail_workspace"]` promote the effective scope to `/`. | Opened a child `Sanctum(allowed_dirs=["/"])` inside a parent `Sanctum(allowed_dirs=["jail_workspace"])` and wrote to `/tmp/` → the write succeeded with no exception (confirmed jailbreak). Fixed; 5 new tests in `tests/test_sanctum_nested_allowed_dirs_widening.py`. | [`b9541be`](https://github.com/anjo-da-maquina/parrhesia/commit/b9541be11c8a22f4c14e31832c705035f8acdda2) |
| [§AR](../GRIMOIRE.md) | A judgment message said "execution is impossible," but the CLI's exit code was always `0` (success). A caller could never detect a violation from the exit code. | Ran `python src/kamael_judgment.py <violating file>` → the screen shows a rejection, but `echo $?` is always 0. | [`2c32938`](https://github.com/anjo-da-maquina/parrhesia/commit/2c3293818e5602982aa829753cae5868a65868d8) |
| [§CT](../GRIMOIRE.md) | `socket.getaddrinfo()` (DNS resolution) bypassed both independent defense layers entirely, since it never calls `connect()`. Secret data could be exfiltrated by encoding it into a subdomain label and resolving it (classic DNS exfiltration). | Called `getaddrinfo()` on a disallowed hostname (`"<secret>.attacker.example.com"`) → nothing blocked it; it only failed with the sandbox's own DNS-unreachable OS error (proof nothing was actually enforced). After the fix, the full DNS-exfiltration chain was reproduced and confirmed blocked on both layers. | [`fe8b54f`](https://github.com/anjo-da-maquina/parrhesia/commit/fe8b54f81fdefd912af6dec71322667f7a54b9a0) → real-CI confirmation [`90e0c1a`](https://github.com/anjo-da-maquina/parrhesia/commit/90e0c1a85ecb66aef1e1d1b9ef8ef4e7d4bff974) |

The full record is [GRIMOIRE.md](../GRIMOIRE.md); a narrative version is
[DEVLOG.md](../DEVLOG.md).

## 4. Current state of the test suite (measured, with sources)

### On CI (no network restrictions)

```
commit:     f1e9d01
run:        Sanctuary CI/CD — https://github.com/anjo-da-maquina/parrhesia/actions/runs/43179449880
conclusion: success (zero failure-comments)
result:     843 passed, 2 xfailed, 0 xpassed, 2 warnings in 46.78s
```

`xpassed` went from 11 to 0. Right after the first push of the design change
(CI result for [`70fa173`](https://github.com/anjo-da-maquina/parrhesia/commit/70fa173f45908ac4c3e6f3ef3f67e398ad1afb86)
was `842 passed, 2 xfailed, 1 xpassed`), one case was still xpassing:
`tests/test_openai_agent_loop_template.py::test_execute_safe_action_uses_sanctum_and_is_not_a_stub`.
The real CI log showed the cause — an unconditional `xfail` was also being
applied on the CI-only branch where it always structurally passes regardless
of rsa/cert state — and a follow-up fix scoped the `xfail`'s `condition=` to
exclude CI runs ([GRIMOIRE.md §DA](../GRIMOIRE.md)). The remaining `2 xfailed`
are unrelated to rsa — the Orchestrator/DockerSandbox not-yet-implemented cases
detailed in §4.1.

#### 4.1 Design change: `xfail(strict=False)` → `skipif`

Previously, tests depending on the `rsa` key-generation library used
`pytest.mark.xfail(strict=False)` — "don't turn CI red if this fails because
rsa is missing." On CI (where `rsa` actually installs), this showed up as 11
`xpassed` results, which always needed a long explanation of why passing
unexpectedly was fine.

Following external review feedback that "whether rsa is available is known
before the test even runs — this isn't an unpredictable runtime failure," the
tests were switched to `pytest.mark.skipif`
([GRIMOIRE.md §DA](../GRIMOIRE.md)). As a result:
- On CI (`rsa` present), these tests run normally and show as `passed` (no
  longer the special `xpassed` state).
- In an environment without `rsa` (this sandbox, say), they show as `skipped`
  with an explicit reason.

The remaining `2 xfailed` (unrelated to `rsa`) are unchanged:
`tests/test_orchestrator.py::test_orchestrator_initialization` (reason:
"Orchestrator API is pending implementation") and
`tests/test_sandbox.py::test_docker_sandbox_isolation` (reason: "DockerSandbox
implementation is pending") — both long-standing `strict=True` xfails for
features that simply aren't implemented yet.

### In this exact sandbox (actually fixed during this review)

This sandbox has no `rsa` installed and no PyPI access (confirmed by actually
running `pip install rsa`, which failed with a DNS resolution error). Before
this review, that meant `tests/conftest.py` itself failed to import, which
stopped test collection for the entire suite (confirmed by actually running
`python3 -m pytest`: exit code 4, zero tests run).

That was fixed first (wrapping the import in `tests/conftest.py` in a
try/except, and adding `pytest.importorskip("rsa")` to the handful of files
that import `runtime_audit_gatekeeper` unconditionally). Two further real
defects surfaced during this same review and have also been fixed: a test
depending on the executor's global git config (§CY) and the xfail→skipif
design change (§DA). Re-running the exact same sandbox now gives (actually run,
not estimated):

```
$ python3 -m pytest -q
830 passed, 11 skipped, 4 xfailed, 62 warnings in 27.18s
```

- **0 failed**: the one previously-observed failure
  (`test_preexisting_secret_in_unchanged_lines_is_not_reflagged`, caused by a
  missing git-signing symlink `/tmp/code-sign`) is gone now that the test no
  longer depends on the executor's global git config at all
  ([GRIMOIRE.md §CY](../GRIMOIRE.md)). Verified by actually setting
  `commit.gpgsign = true` in an isolated test `$HOME`: 4 of 5 tests failed
  before the fix, all 5 passed after.
- **11 skipped**: the known `rsa`-dependent environment gap (10 of these moved
  here from `xfailed` as part of the §DA design change) plus
  `tests/test_audit_hook_registration_fails_closed.py`.
- **4 xfailed**: one unrelated to §CX (a genuinely expired test certificate),
  a few more `rsa`-dependent cases not covered by the subprocess-based
  prediction, and the 2 unrelated ones named above (Orchestrator/DockerSandbox
  not yet implemented).

## 5. The human and AI agent's own working process on this project

This project is built jointly by its human owner and Claude (an AI agent built
by Anthropic). Signed commits, CI verification on every change, a disclosed past
process violation, the three-round real-machine debugging session for the
certificate-automation script, and two rounds of red-lining this very overview
are recorded in detail in a separate file:

→ [docs/worklog/ai-agent-notes.en.md](./worklog/ai-agent-notes.en.md)

## 6. Further reading

| Document | Covers |
| --- | --- |
| [README.en.md](../README.en.md) / [README.md](../README.md) | Overview, usage, threat model, design principles |
| [docs/CASE_STUDY.md](./CASE_STUDY.md) | Reproducible demo, including the honest record of its first run scoring 2/5, not 5/5 |
| [DEVLOG.md](../DEVLOG.md) | The defects as a narrative, as of the 81-entry snapshot (see GRIMOIRE.md for the current count) |
| [GRIMOIRE.md](../GRIMOIRE.md) | §A–§DA, 105 entries, the raw, most detailed record |
| [docs/FAQ.md](./FAQ.md) | Differentiation, limitations, and other Q&A |
| [docs/WHY.md](./WHY.md) | The design rationale for auditing rather than trusting AI agents |
| [docs/BOUNDARY.md](./BOUNDARY.md) | What this project does and does not claim to do (including the §CX/§CZ history) |
| [docs/worklog/ai-agent-notes.en.md](./worklog/ai-agent-notes.en.md) | Detailed record of the AI agent's own working process |

## 7. Reproduce it yourself

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```

No network access and no state left behind afterward. Even without `rsa`,
`python3 -m pytest` now collects and runs the whole suite (see §4).
