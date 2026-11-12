# FAQ

Factual answers only — no claims beyond what's verified elsewhere in this repo (see [`README.en.md`](../README.en.md), [`docs/CASE_STUDY.md`](./CASE_STUDY.md)).

**How is this different from Bandit or Semgrep?**
Bandit and Semgrep scan source code for known vulnerability or anti-patterns at a point in time. This toolkit's detectors (`parrhesia/diff_fraud.py`) operate on the diff between two commits, looking for specific shortcuts an agent takes when "fixing" something (deleting a test, adding a skip marker, swallowing an exception, hardcoding an exit code). The two are complementary — a repo could run both. No accuracy comparison between this toolkit and Bandit/Semgrep on their own turf (static vulnerability detection) has been made, because that's not what this toolkit does.

**Does it use an LLM?**
No. The five detectors in `parrhesia/diff_fraud.py` are plain pattern matches over `git diff` text (AST/regex-level checks on added/removed lines) — deterministic, no model call. `parrhesia/verify/cross_model_review.py` exists as a separate, not-yet-wired-in primitive for a different, harder problem (judging whether a natural-language claim like "verified all edge cases" is true) — see the Limitations section of the README and the Roadmap.

**What's the false-positive rate?**
Measured so far on one thing: `tests/test_parrhesia_selftest.py` confirms zero false positives on one legitimate-change sample (a real, non-shortcut test addition), alongside detecting every known-shortcut sample. That is not the same as a measured false-positive rate over a large corpus of real-world commits — that measurement hasn't been done, and the Roadmap says so rather than implying it has.

**Where does my code or data go?**
Nowhere. The tool reads `git log`/`git show` output locally and writes a report to a local file (or stdout). There is no account, no API key, and no network call site in `parrhesia/` (verified by `git grep` for outbound-request patterns, and by re-running the demo inside a network namespace with no network interface at all — see the README's Design principles section).

**Does it execute the code it's auditing?**
No. It only reads commit metadata and diffs (`git log`/`git show`). It never runs the target repository's code.

**What does it not catch?**
Anything outside the five listed diff patterns; whether the resulting code is semantically correct or secure; and whether a natural-language claim in a comment or commit message is true (that needs a human or a second model reading the same evidence — see `parrhesia/verify/cross_model_review.py`, not yet wired in).

**Can I run it against my own team's repo?**
Yes — `python -m parrhesia.cli audit /path/to/some/other/git/repo` runs it read-only against any local git checkout. See the Quickstart in the README.

**Is this audited by anyone other than you?**
No. All verification described in this repo (detection rate, CI status, network-isolation proof) was performed by the same author/AI-agent pairing that wrote the code. Treat it as "verified by the people who built it," not outside certification — stated explicitly in the README's Limitations section.

**Why is the project's own bug history public (DEFECTS.md)?**
Because the standard this toolkit holds other code to — don't hide a gap behind a report of success — is the standard applied to this project's own development too. See [`docs/WHY.md`](./WHY.md).

**Is this free to use?**
Yes, MIT licensed. See [`LICENSE`](../LICENSE).
