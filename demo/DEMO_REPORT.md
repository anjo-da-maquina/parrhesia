# デモ監査レポート(実行結果・自動生成)

このファイルは `demo/build_and_audit_demo.py` を実行するたびに
上書きされます。下記は、このスクリプトが実際に作った
使い捨てリポジトリ(人間が書いた正常なコミット→AIが仕込んだ
5つの欠陥を含むコミット)に対して、`parrhesia.audit` を
実際に実行して得た、本物の出力です(決め打ちではありません)。

## 仕込んだ欠陥(5種)と検出結果

| # | 欠陥 | parrhesia.diff_fraudのパターンID | このレポートで検出されたか |
| - | --- | --- | --- |
| 1 | 失敗テストの丸ごと削除 | `test_deletion` | 検出 |
| 2 | flakyを理由にしたskip追加 | `skip_addition` | 検出 |
| 3 | 例外のexcept:passによる握り潰し | `exception_swallowing` | 検出 |
| 4 | assertionの`assert True`への弱化 | `assertion_weakening` | 検出 |
| 5 | 終了コードの常時成功ハードコード | `exit_code_hardcoding` | 検出 |

## 既知の限界(正直な注記)

- 「確認済み: 全てのエッジケースを検証し...」という、検証して
  いないのに検証済みと主張するコメント自体は、本デモの
  `parrhesia.diff_fraud` の検出対象**外**です(diffの構造的パターンのみを見る設計のため)。
  この種の『言葉だけの自己申告』を検出するのは、
  `parrhesia.verify.cross_model_review` / `human_spotcheck`
  の役割であり、本デモでは呼び出していません。
- 秘密情報(APIキー等)のスキャンは別モジュール
  (`tools/pre_commit_secret_scan.py`)の責務であり、本デモの
  範囲外です。

## parrhesia.audit の実際の出力(そのまま)

```
# Parrhesia 第三者リポジトリ監査レポート

対象: /tmp/parrhesia_portfolio_demo_wpnv_3lt/sample_ai_repo
検査したコミット数: 2

## 1. コミット履行の整合性(diff_fraud 5パターン検出)

検出件数: 5件(要確認の合図であり、不正の確定ではない)

- コミット 4127345979(「fix: エッジケースを全て検証し、堅牢性を向上させました(実際には5つの欠陥を仕込んだ、AIの手抜きの典型例)」):
  - [test_deletion] test_payment.py: テスト関数 test_payment_rejects_negative_amount が削除され、同名の定義が追加側に存在しない。
  - [skip_addition] test_payment.py: 新規にテストのスキップ指定が追加されている。
  - [assertion_weakening] test_payment.py: assert文が2件削除され、1件しか追加されていない(net減少)。
  - [exception_swallowing] payment.py: 新規に、例外を握り潰す`except: pass`(またはこれに類する)パターンが追加されている。
  - [exit_code_hardcoding] payment.py: 以前は非ゼロ・動的だった終了コード/戻り値が、0に固定されている。

## 2. AIDD契約遵守の痕跡

Parrhesia形式の行動記録・契約の痕跡は見つかりませんでした。これは対象リポジトリがParrhesiaを導入していないだけの可能性が高く、それ自体を不正の証拠として扱ってはならない。

```
