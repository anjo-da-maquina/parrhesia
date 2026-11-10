# Outreach materials (English)

Everything below is built only on what was actually demonstrated in [Phase 1](../README.en.md)
and the [case study](./CASE_STUDY.md) — no capability is claimed here that wasn't run and
verified in this repository.

## 90-second pitch

> I'm a QA engineer who got tired of AI coding agents reporting "fixed, all tests
> passing" on commits that quietly deleted the failing test instead of fixing the
> bug. So I built a small toolkit that audits a git diff for exactly that kind of
> shortcut — test deletion, new skip markers, weakened assertions, swallowed
> exceptions, hardcoded exit codes — and runs it read-only against any cloned repo.
> I proved it against a sample commit built to look like a typical AI "cleanup"
> commit: it caught all five planted shortcuts, in under a tenth of a second, from
> the diff alone. The first time I ran that exact demo, it only caught two of five —
> that failure, and the fix, is still sitting in the commit history, because the
> whole point of this project is not hiding the parts that didn't work the first
> time. If your team is shipping a lot of AI-generated code and wants a second pair
> of eyes that doesn't get tired or take the agent's word for it, that's what I do.

## Social posts (LinkedIn / X)

**Post 1 — the finding**
> Built a demo today: a fake "AI cleanup commit" with 5 classic shortcuts baked in
> (deleted test, new skip marker, weakened assertion, swallowed exception, hardcoded
> exit code). My audit tool caught 5/5 — from the diff alone, no test run needed, in
> 0.08s. First run only caught 2/5 though, and that failure is still in the git
> history. Repo: github.com/anjo-da-maquina/parrhesia

**Post 2 — the problem**
> The failure mode I keep seeing in AI-generated code isn't "the code is wrong" —
> it's "the test that would have caught it quietly disappeared, and the commit
> message says everything passed." Built a small detector for exactly that pattern.
> It's pattern-based, not magic — here's what it actually does and doesn't catch:
> github.com/anjo-da-maquina/parrhesia

**Post 3 — the offer**
> If your team ships AI-generated code and wants someone to audit the diffs for the
> specific ways agents cut corners (not a generic linter pass) — that's what I do as
> a QA engineer. One command, read-only, runs against any git repo you give it.
> Happy to run it against a real PR of yours as a sample. github.com/anjo-da-maquina/parrhesia

## Fixed-price service listing (Upwork / Contra style)

**Title**: Audit of AI-generated code — 48h, fixed price

**What you get**:
- A read-only audit of up to 50 commits in a git repo you provide (or a specific PR),
  run with the open-source tool in this repo (`parrhesia/audit.py`).
- Detection of 5 concrete shortcut patterns: deleted tests, new skip markers,
  weakened assertions, swallowed exceptions, hardcoded exit codes — plus undisclosed
  file changes and commit messages that reference files that don't exist.
- A written report (Markdown) listing every finding with the exact commit, file, and
  evidence line — not a vague severity score.
- One round of follow-up questions about the findings.

**What's out of scope** (stated up front, not discovered mid-engagement):
- Secret/credential scanning (a different tool; can be quoted separately).
- Semantic correctness review ("is this code right") — this is shortcut-pattern
  detection, not a full code review.
- Judging whether a natural-language claim in a comment or PR description is true —
  that needs a human or a second model reading the same evidence, which is a
  separate, slower engagement, not part of the 48h fixed price.
- Any code execution of the target repo — the audit is read-only (git log/show only).

**Fixed price. Delivered in 48h from receiving repo access.**

## Proposal templates (3 variants, ≤150 words each)

**Variant A — direct**
> Hi — I audit AI-generated code for the specific shortcuts agents take under time
> pressure: deleted tests, new skip markers, weakened assertions, swallowed
> exceptions, hardcoded exit codes. I built the tool myself and can show you it
> catching all five in a live demo before you commit to anything
> (github.com/anjo-da-maquina/parrhesia — the demo runs in under a second, no setup).
> For your project, I'd run a read-only audit of your recent commits or a specific
> PR and hand back a report with exact evidence, not a vague score. Happy to run it
> against one of your real PRs for free first, so you can judge the output before
> paying for anything. 48h turnaround once I have repo access. Let me know if that's
> useful.

**Variant B — QA-background-led**
> I'm a QA engineer, not a generic developer-for-hire — my background is in finding
> the gap between "looks like it works" and "actually works." I built an
> open-source tool specifically for auditing AI-generated commits (it's linked in my
> profile, with a reproducible demo). I'd like to run it read-only against your repo
> and hand back a concrete findings report in 48h, fixed price. If it finds nothing,
> you'll have a clean bill of health with evidence, not just my opinion. If you'd
> rather see it work first, I'm glad to run the public demo live on a call.

**Variant C — short/skimmable**
> I audit AI-generated code for 5 specific shortcut patterns (deleted tests, skip
> markers, weakened assertions, swallowed exceptions, hardcoded exit codes) using a
> tool I built myself — demo here: github.com/anjo-da-maquina/parrhesia. Read-only,
> 48h, fixed price, written report with exact evidence per finding. Can run it
> against one of your real PRs first so you see real output before deciding.

## Differentiation from existing tools (facts only)

Bandit and Semgrep scan source code for known vulnerability or anti-patterns at a
point in time; they don't look at *what changed between two commits* or at the
specific shortcuts an AI coding agent takes when asked to fix something (deleting
the test instead of fixing the bug, adding a skip marker, swallowing an exception
newly introduced in that diff). This toolkit's `parrhesia/diff_fraud.py` detectors
operate on the diff itself, comparing added/removed lines across a commit boundary,
which is a different question than "does this file contain a dangerous pattern."
The two approaches are complementary, not competing: a repo could reasonably run
Bandit/Semgrep for static vulnerability scanning *and* this toolkit for commit-level
shortcut detection. No claim is made here about detection accuracy or coverage
relative to Bandit or Semgrep on their own turf (static vulnerability detection) —
that comparison hasn't been run and isn't claimed.
