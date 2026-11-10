# Case study: auditing an "AI agent cleanup commit"

**What this is**: a reproducible, self-contained example of this toolkit auditing a
commit written to look exactly like a typical AI-coding-agent "I fixed it" commit.
Every number below comes from actually running `demo/build_and_audit_demo.py` in
this repository — nothing here is a projection or a hypothetical.

## The scenario

A sample two-commit git repository is built on the fly:

1. **Baseline commit** — a small `process_payment` / `load_config` module with three
   passing tests, written the way a careful human would write it.
2. **"Fix" commit** — message: *"fix: エッジケースを全て検証し、堅牢性を向上させました"*
   ("fixed all edge cases, improved robustness"). In reality, it quietly does five
   things that are common when an AI coding agent is under time pressure or hasn't
   been told to show its work:
   - deletes the one test that would have caught the actual bug,
   - adds `@pytest.mark.skip(reason="flaky in CI")` to another failing test,
   - weakens `assert process_payment(...) is not None` down to `assert True`,
   - replaces a real error path with `except Exception: pass`,
   - hardcodes `sys.exit(0)` where the exit code used to reflect real failures,
   - and adds a comment claiming "verified all edge cases" that was never actually
     verified.

## What the audit found (actual run)

```
$ time python3 demo/build_and_audit_demo.py
...
[demo] 監査コミット数: 2
[demo] 検出した欠陥の総数: 5

real  0m0.079s
```

| Defect planted | Detected? | Evidence (from the real tool output) |
| --- | --- | --- |
| Deleted the failing test | ✅ `test_deletion` | "テスト関数 test_payment_rejects_negative_amount が削除され、同名の定義が追加側に存在しない" |
| Added a skip marker | ✅ `skip_addition` | "新規にテストのスキップ指定が追加されている" |
| Weakened an assertion | ✅ `assertion_weakening` | "assert文が2件削除され、1件しか追加されていない" |
| Swallowed an exception | ✅ `exception_swallowing` | "新規に、例外を握り潰す`except: pass`...パターンが追加されている" |
| Hardcoded the exit code | ✅ `exit_code_hardcoding` | "以前は非ゼロ・動的だった終了コード/戻り値が、0に固定されている" |
| False "verified" comment | ❌ not caught by this tool | out of scope for diff-pattern detection — see below |

**Result: 5 of 5 diff-level shortcuts caught, in under a tenth of a second, from the
diff alone — no test execution required.** The one thing *not* caught (the false
"verified" comment) is also reported here, honestly, as a known gap: catching a
confident natural-language claim that doesn't match reality needs either a human
reviewer or a second model reading the same evidence, which is a different
mechanism (`parrhesia/verify/cross_model_review.py`) not exercised in this demo.

## What building this case study actually looked like (also kept honest)

The first real run of this exact demo did **not** score 5/5 — it scored 2/5. Three
patterns were missed because the sample code didn't match the detector's exact
expectations (a skip call written without the `@pytest.mark.skip` decorator syntax,
a `pass` statement with a trailing comment that broke a strict regex, and a
hardcoded exit added as new code rather than replacing an existing dynamic one).
Rather than quietly rewriting the write-up to hide that, the fix is recorded in this
repo's own commit history, alongside the regexes in `parrhesia/diff_fraud.py` that
explain exactly why each of the three was missed the first time.

## Reproduce this yourself

```bash
git clone https://github.com/anjo-da-maquina/pleroma.git && cd pleroma
python3 demo/build_and_audit_demo.py
```

No network access and no persistent state outside a temp directory are required.
