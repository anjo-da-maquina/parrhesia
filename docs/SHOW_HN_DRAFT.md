# Show HN 投稿 下書き

公開はユーザー自身が行う(このファイルは下書きのみ)。投稿先: https://news.ycombinator.com/submit

## タイトル

```
Show HN: Parrhesia – catch what your coding agent skipped, hid, or faked
```

## 本文(200語以内)

```
I'm a QA engineer. I kept seeing AI coding agents report "all tests passing"
on commits that actually deleted the failing test, swallowed an exception,
or hardcoded an exit code instead of fixing the bug.

I built a small, local-first tool that audits a git diff for exactly five of
these shortcuts (deleted test, new skip marker, weakened assertion, swallowed
exception, hardcoded exit code) — read-only, no network, no account.

Demo: it builds a fake "AI cleanup commit" with all five shortcuts planted,
then audits it. Caught 5/5, in ~0.1s, from the diff alone. I re-ran the same
demo inside a Linux network namespace with no network interface at all
(stricter than Docker's --network none) to confirm nothing phones home — it
still works.

The first real run of this exact demo only caught 2/5, because the sample
code didn't match my regexes. That failure and the fix are still in this
repo's commit history, not smoothed over — the whole point of the project is
not hiding the parts that didn't work the first time.

It's pattern-based, not semantic — it won't tell you if your code is
correct, only whether one of these five specific shortcuts was taken.
Limitations and what it doesn't catch are in the README.

https://github.com/anjo-da-maquina/parrhesia
```

## 投稿前チェック(本人用)

- [ ] タイトルは実際に動くものの説明になっているか(誇張なし)
- [ ] 本文の数値(5/5、0.1秒等)は最新のREADME/DEMO_REPORT.mdと一致しているか
- [ ] リンク先リポジトリが公開(public)設定になっているか
- [ ] 投稿後、最初の数件のコメントに「どう違うのか」系の質問が来る前提で、docs/FAQ.mdを読み返しておく
