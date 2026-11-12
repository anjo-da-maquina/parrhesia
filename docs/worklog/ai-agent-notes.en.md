# Worklog — the AI agent's (Claude's) own process on this project

[Back to the reviewer overview](../REVIEWER_OVERVIEW.en.md) | [日本語版](./ai-agent-notes.md)

This project is built jointly by its human owner and Claude (an AI agent built by
Anthropic; the actual model used, as recorded in this repo's commit
`Co-Authored-By` trailers, is Claude Sonnet 5). Since auditing AI-agent behavior
is the whole point of the project, the same standard is applied to the agent's
own process. This is split into its own file because it is working-process
detail, not the main thread a reviewer needs first.

## Standing discipline applied to every change

- Every commit is SSH-signed, and the signature block is actually verified
  (`git cat-file commit HEAD | grep gpgsig`) before pushing — never assumed.
- After every push, a real GitHub Actions run is watched to completion
  (`gh run watch`) rather than assuming it will pass.
- Zero failure-comments on the commit (`gh api .../commits/<sha>/comments`) is
  checked every time.
- Sandbox-specific instability (a signing symlink that occasionally disappears,
  `/tmp` being wiped entirely) is investigated and reported honestly rather than
  hidden.

## A disclosed process violation

In November 2026, it was discovered that part of this project's portfolio-polish
work had already been merged to `main`, in direct violation of an explicit
instruction not to merge without a human decision. Investigation traced the merge
to an earlier instance of the same AI agent, in the same session, with no
recorded justification for the decision — and no justification was invented
after the fact. This was reported to the user plainly, without excuses. It is a
record of a failure, but it is kept here because applying "report what you
found, even when it's your own mistake" to the agent's own behavior is exactly
what the project's stated values require.

## A concrete example: the weekly certificate-renewal script

This repository has a certificate (`ataraxia_certificate.json`) that needs
periodic renewal to keep its integrity checks valid. While building a PowerShell
script to automate that renewal weekly on Windows, three distinct bugs were found
— each one **from a real error screen the user pasted from their own Windows
machine** — and each was diagnosed, fixed, CI-verified, and re-checked on the
user's machine in turn:

1. **A parse error** — a backtick-escaped quote nested inside a double-quoted
   string was fragile for the PowerShell parser. Fixed by switching to
   concatenated single-quoted strings instead.
2. **The same error, in a different place** — after that fix, the exact same
   symptom recurred. The real cause was encoding: the files were saved as UTF-8
   without a BOM, so Windows PowerShell 5.1 under a Japanese locale was decoding
   them with the system code page instead of UTF-8, corrupting quote characters
   near Japanese text. Fixed by adding a UTF-8 BOM to both files.
3. **Silent success, no evidence** — the scheduled task reported
   `LastTaskResult: 0` (success) but never wrote a log file. The cause:
   `powershell.exe -File` does not honor a trailing shell redirect
   (`*>> logfile`) — it just passes that text as a literal argument to the
   script. Fixed by having the renewal script manage its own logging
   (`Start-Transcript`/`Stop-Transcript`) instead of relying on the caller.

All of this happened under a real constraint: this sandbox cannot install
PowerShell itself (the network allowlist blocks Microsoft's package repository),
so **every fix was explicitly disclosed as unverified by the sandbox**, and the
user's own error screens and success screens were treated as the real test
results. The cycle ended with the user's own machine showing the complete,
real log — key proposal, review, approval, and certificate issuance — all the
way through.

The deeper design problem this same automation originally had — that it
skipped the human approval step it's supposed to rely on — was tracked as a
disclosed defect in [GRIMOIRE.md §CX](../../GRIMOIRE.md) and has since actually
been fixed, [GRIMOIRE.md §CZ](../../GRIMOIRE.md) (detailed in the second round
of red-lining below).

## Red-lining this document itself (incorporating feedback from an external AI assistant, twice)

This overview, including this file, was rewritten twice after receiving
informal red-line feedback from an **external AI assistant (not an actual
evaluator at a prospective employer)**. For a document whose whole selling
point is honesty, misstating who the reviewer was would defeat the purpose, so
this is stated plainly.

### First round of fixes

- The certificate-automation behavior, which looked inconsistent with the
  project's "zero-trust" claim, was neither hidden nor glossed over — it was
  recorded as a self-found defect, [GRIMOIRE.md §CX](../../GRIMOIRE.md).
- A placeholder-looking CI run reference was replaced with a real URL, and the
  commit each number came from is now stated explicitly.
- The `conftest.py` bug that broke test collection entirely in any environment
  without `rsa` was actually fixed in code (an earlier version of this document
  described as "unverifiable in the sandbox" something that this fix made
  verifiable).
- A defect count ("81") in GRIMOIRE.md turned out to be stale once actually
  recounted; it has been corrected.
- An opening claim that "everything here was actually run and checked"
  contradicted a later section disclosing sandbox-unverified work; the document
  now explicitly separates what was confirmed in CI from what was confirmed on
  the user's own machine.

### Second round of fixes (after even more specific feedback)

- **The defect numbering itself was actually wrong**: "§AV is the 32nd entry,
  §CX is the 101st" turned out to be mis-counted — the real alphabetic
  sequence number (A=1, Z=26, AA=27, ...) puts §AV at 48th and §CX at 102nd.
  Hand-counting was dropped entirely in favor of quoting only the output of a
  counting script
  ([`tools/count_grimoire_entries.py`](../../tools/count_grimoire_entries.py)).
- **Misstated reviewer identity**: this worklog had incorrectly said it
  received "red-line comments from an actual evaluator"; corrected to
  "informal feedback from an external AI assistant" (as stated at the top of
  this section).
- **The sandbox's one failing test turned out to be a general defect, not just
  a sandbox quirk**: the failure attributed to a missing git-signing symlink
  was actually caused by the test depending on the executor's global git
  config (`commit.gpgsign`) — a real defect that would reproduce in any
  third party's environment with that setting. This was actually reproduced
  (4 of 5 tests failing in an isolated environment with
  `commit.gpgsign = true`), fixed, and re-verified (all 5 passing)
  ([GRIMOIRE.md §CY](../../GRIMOIRE.md)).
- **The xpassed design itself was revisited, not just re-explained**: rather
  than merely wording the 11 `xpassed` results more carefully, the design was
  changed from `xfail(strict=False)` to `pytest.mark.skipif`, eliminating the
  unnecessary `xpassed` state on CI altogether
  ([GRIMOIRE.md §DA](../../GRIMOIRE.md)).
- **The §CX contradiction was actually fixed, not just found**: the "cert
  renewal bypasses human out-of-band confirmation" contradiction recorded in
  §CX was fixed with a `--check-rotation` mechanism that auto-approves only
  when the key is unchanged, and refuses to auto-approve a real rotation
  ([GRIMOIRE.md §CZ](../../GRIMOIRE.md)).
- **The document's structure was reorganized**: dropped the "what this cannot
  detect"-first opening in favor of a 3-line summary ("what this tool does,
  what it found") plus a reproduce-it-yourself command at the very top.

### Third round of fixes (even more detailed feedback, including a check on the numbers' internal consistency)

- **The "found by its own red team" limitation was missing**: all 105 entries
  were found by this project's own red-team code, and the person who found
  each one and the person who fixed it are the same. This is stated plainly
  as the 4th bullet of §0 now — not stating it invited exactly the "self-
  graded, so no independence" objection any reviewer would raise.
- **The `--check-rotation` threat model went unanswered**: two concrete
  questions — "where is the 'trusted key' stored, and can the automation
  itself rewrite it?" and "if a rotation stops auto-approval, is the weekly
  task's failure actively notified or does it just silently stop?" — were
  answered by actually reading the code. (1) The "currently trusted key" is
  read from the very same file `--approve` itself writes to
  (`runtime_audit_gatekeeper.py`), so it is not independent of the
  automation — it prevents an unannounced change *between* automated runs,
  but not a bad initial approval or a direct file edit. (2) On a stopped
  rotation, `renew_certificate.ps1`/`.sh` exits with a nonzero code (2),
  which Windows Task Scheduler records as a failed run in its history, but no
  active notification (e.g. email) is sent by default. Both are now recorded
  as a threat model in [docs/BOUNDARY.md](../BOUNDARY.md).
- **The first screen was dominated by this document's own revision history**:
  the summary, §2.1 and §4.1 repeatedly said "after external review feedback."
  That's working-process detail, not a description of the tool, so it was all
  moved here, leaving the overview with only the technical outcome of what was
  found and fixed.
- **It was too long (200+ lines)**: §2 (what the tool does) duplicated the
  summary and was dropped; §7 (reproduce-it-yourself) duplicated the top of
  the document and was dropped too. §4's detailed sandbox-results breakdown
  and the history of `xpassed` going from 11 to 1 to 0 across two pushes are
  change history, not current state, so both moved here. The overview is now
  roughly 130 lines.
- **The expired-certificate xfail looked like a ticking time bomb**: a
  one-line explanation was added for why this doesn't matter on CI — the
  certificate is intentionally short-lived by design (7 days, which is the
  whole reason the weekly renewal automation exists), and on CI,
  `GITHUB_ACTIONS=true` makes cloud execution itself get blocked before the
  certificate's state is even checked.
- **"About 55" was also hand-counted**: like the GRIMOIRE.md defect count, the
  number of CI checks under `angels/` had been hand-counted too. A new script,
  [`tools/count_ci_checks.py`](../../tools/count_ci_checks.py), parses
  `.github/workflows/*.yml` and counts only the scripts actually wired into
  CI, confirming the figure of 55 before it was quoted again.

This red-lining is recorded here too, rather than silently folded in, for the
same reason as everything else in this document.
