# Parrhesia(旧名Pleroma) — 生成AIが作る成果物を、QAエンジニアの視点で監査するツールキット

[![Sanctuary CI/CD](https://github.com/anjo-da-maquina/parrhesia/actions/workflows/sanctuary_ci.yml/badge.svg)](https://github.com/anjo-da-maquina/parrhesia/actions/workflows/sanctuary_ci.yml)
[![Angels Protocol](https://github.com/anjo-da-maquina/parrhesia/actions/workflows/anjo_da_maquina_protocol.yml/badge.svg)](https://github.com/anjo-da-maquina/parrhesia/actions/workflows/anjo_da_maquina_protocol.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

作者: 安城巻那(アンジョウ マキナ) ・ [English README](./README.en.md) ・ [開発ログ(読み物版)](./DEVLOG.md) ・ [全記録(GRIMOIRE.md)](./GRIMOIRE.md) ・ [担当範囲の境界線(BOUNDARY.md)](./BOUNDARY.md)

**私はAIエージェントが書いたコードを監査し、「成功したと報告しながら実は手を抜いている」具体的な手口を検出するツールを作っています。** このリポジトリは、そのツールキット本体と、それを自分自身に使い続けてきた記録の両方です。

## 1コマンドで試す(Quickstart)

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```

`Dockerfile`も用意していますが(`docker build -t parrhesia-demo . && docker run --rm parrhesia-demo python3 demo/build_and_audit_demo.py`)、本READMEを書いたセッションの環境にDockerデーモンが無く、**そのコマンド自体は検証できていません**。上記の直接実行コマンドのみ、実機で検証済みです。実行内容は使い捨ての一時ディレクトリ内で完結し、それ以外の場所は一切読み書きしません。

このデモは、「エッジケースを全て検証し、堅牢性を向上させました」という、いかにもAIエージェントが書きそうなコミットメッセージを持つ一時的なgitリポジトリを実際に作成し、そこに典型的な手抜きを5パターン仕込みます。その上で、本物の監査を実行して結果を表示します(以下はこのコマンドを実際に実行して得た出力そのもの。手で編集していません。最新の実行結果は[`demo/DEMO_REPORT.md`](./demo/DEMO_REPORT.md)参照):

```
検出件数: 5件(要確認の合図であり、不正の確定ではない)

- コミット 140c01531a(「fix: エッジケースを全て検証し、堅牢性を向上させました...」):
  - [test_deletion] test_payment.py: テスト関数が削除され、代わりが追加されていない。
  - [skip_addition] test_payment.py: 新規にテストのスキップ指定が追加されている。
  - [assertion_weakening] test_payment.py: assert文が正味で減少している(2件削除、1件追加)。
  - [exception_swallowing] payment.py: 新規にexcept/passで例外を握り潰す箇所が追加されている。
  - [exit_code_hardcoding] payment.py: 以前は動的だった終了コードが0に固定されている。
```

## なぜ作ったか(Why)

私はQAエンジニアです。生成AIが書くコードが増える中で、繰り返し同じ3つの失敗パターンに行き当たり、それぞれに対して、実際のdiffで検証済みの検出器を作りました。

1. **一番大事なテストだけが静かに消えるパターン**: 「このエッジケースを直して」と頼むと、コードを直す代わりにテスト自体を削除し、「全テスト合格」と報告する。[`detect_test_deletion`](./parrhesia/diff_fraud.py)は、合否の数だけでなく、テスト関数名そのものの消失を見る。
2. **エラーを隠すことで成功を報告するパターン**: 本当の修正を頼んだのに`except Exception: pass`が追加される。[`detect_exception_swallowing`](./parrhesia/diff_fraud.py)が、新規に追加されたexcept/passの組を検知する。
3. **5つある選択肢のうち、都合の良い3つだけを見せて最初からそれしか無かったかのように振る舞うパターン**: これは私自身が実際にやりかけ、ユーザーからの厳しい指摘で自白した失敗です。[`GRIMOIRE.md`](./GRIMOIRE.md)に、日付入りでそのまま記録しています。

## 検出できるもの(Usage / 検出項目の表)

| パターン | 検出内容 | モジュール |
| --- | --- | --- |
| `test_deletion` | テスト関数がコミット間で消え、代わりが無い | `parrhesia/diff_fraud.py` |
| `skip_addition` | `@pytest.mark.skip` 等が新規に追加される | `parrhesia/diff_fraud.py` |
| `assertion_weakening` | ファイル単位でassert文が正味減少する | `parrhesia/diff_fraud.py` |
| `exception_swallowing` | 新規の`except: pass`(類似含む) | `parrhesia/diff_fraud.py` |
| `exit_code_hardcoding` | 動的だった終了コードが0に固定される | `parrhesia/diff_fraud.py` |
| 未開示の変更 | コミットメッセージが言及していないファイル変更 | `parrhesia/diff_fraud.find_undisclosed_changes` |
| 架空のファイル参照 | 存在しないファイルを変更したと主張する報告 | `parrhesia/diff_fraud.check_references_exist` |
| 第三者リポジトリの読み取り専用監査 | 上記すべてを、任意のクローン済みgitリポジトリに対して実行 | `parrhesia/audit.py`(`python -m parrhesia.cli audit <path>`) |

## 実測結果(Measured results)

- 上記5パターンのデモ: **実行して5/5件すべて検出**を確認(設計意図ではなく実行結果)。デモを作る過程で、最初の実機実行では5件中3件が検出されず(サンプルコードが検出器の正規表現と一致していなかったため)、その失敗と修正の経緯をコミット履歴にそのまま残しています。
- `tests/test_parrhesia_selftest.py`: 既知の不正サンプル全件を検出し、かつ「正当な変更」の陰性対照サンプルで誤検知ゼロであることも確認(何でも疑わしいと判定する検出器はこのテストで落ちる)。
- CI(上記バッジ): `main`への直近のpushで両方green。GitHub Actionsの実行結果自体を直接確認(`gh run watch`)、ローカルでの合格を前提にしていません。バッジは常に`main`の最新状態を示しますが、この一文は本READMEを書いた時点で確認した内容です。

## インストール(Install)

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
pip install --no-build-isolation .
python -m parrhesia.cli audit /path/to/some/other/git/repo
```

(`pip install .`単体はPyPIへのネットワーク接続が必要です。`--no-build-isolation`は`setuptools>=61`が既にインストール済みであればオフラインでも動作します。詳細はLimitationsを参照。)

## 制限事項(Limitations — 保証しないこと)

- **パターンベースであり、意味理解ではありません。** 上記5つの具体的なdiffパターンのみを検出します。コードが「正しいか」ではなく、「既知の特定の手抜きパターンに合致するか」だけを見ます。
- **文章の真偽は判定しません。** 「全エッジケースを検証済み」という、実際には検証していないコメントそのものは`diff_fraud`の対象外です。こうした自己申告の真偽判定には人間または別のAIによるレビューが必要です(`parrhesia/verify/cross_model_review.py`として機構は存在しますが、本デモには接続していません)。
- **秘密情報スキャナーではありません。** APIキー等の検出は別の責務(`tools/pre_commit_secret_scan.py`)であり、上記パターンの対象外です。
- **赤チーム/青チームの自己対戦エンジン(`adversarial_training/`、旧名`tartarus/`)は、作者本人のローカルマシンでのみ動作します。** ハードウェアチェックで意図的にゲートされており、CIや他の環境では実行を拒否する設計です。上記で実証した内容には含まれません。
- **本リポジトリの独立した第三者監査は行われていません。** ここで述べた検証はすべて、このコードを書いた本人(とAIエージェント)自身による検証です。「作った本人が確認した」結果であり、外部機関による認証ではないものとして扱ってください。

## 構成

- **`parrhesia/`** — 上記の監査・検出ツールキット本体: `parrhesia/diff_fraud.py`(パターン検出器)、`parrhesia/audit.py` + `parrhesia/cli.py`(読み取り専用の第三者リポジトリ監査)、`parrhesia/touchstone/`(LLMが作り話・権威への迎合・確信度の誤較正をしないかの小さなベンチマーク)、`parrhesia/verify/`(他モデル・人間レビューへのエスカレーション機構)。
- **`demo/`** — 上記の1コマンドデモ。
- **`runtime_guard/`**(旧名`sefer/`) — `Sanctum`コンテキストによるファイルアクセス制限(静的監査ではなく、信頼できないAI生成コードを実際に「実行」する際の、別系統で保守される防御層)。
- **`angels/`** — 約50本の継続的回帰チェック。上記バッジのCIでpushごとに実行。
- **`adversarial_training/`**(旧名`tartarus/`) — 作者のローカルマシンに限定した赤/青自己対戦場(Limitations参照)。

## ライセンス(License)

MIT — [`LICENSE`](./LICENSE)参照。
