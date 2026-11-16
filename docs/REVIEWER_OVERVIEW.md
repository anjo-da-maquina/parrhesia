# レビュー担当者向け概要 — Parrhesia(旧名 Pleroma)

[トップに戻る](../README.md) | [English version](./REVIEWER_OVERVIEW.en.md)

## 要約(3行)+ 自分で再現する

**Parrhesia**は、AIコーディングエージェントが書いたコミットの**差分そのもの**から、
「テストの削除」「スキップマーカーの追加」等5種類の具体的な「ズル」を検出するツール
キットです。さらに自分自身の防御コードも同じ方法で監査し、これまでに107件の欠陥を
発見・修正・記録してきました(§3)。開発過程(署名コミット・CI確認・AIアシスタントに
よるレビューの反映等)の詳細な作業記録は別ファイルにあります(§5)。

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```
ネットワーク接続も、終了後に残る状態も不要です。

**この文書の立場について。** 以下の記述には3種類あります。(1) GitHub Actions上の
実際のCI実行ログから引用した、ネットワーク制限の無い環境での検証結果。(2) ユーザー
自身のパソコン(Windows)で実際に実行した、実機での検証結果。(3) このドキュメントの
作成に使っている開発用サンドボックス(PyPIに接続できず`rsa`をインストールできない
環境)では検証できていない内容(その都度、どれに当たるかを明記します)。

## 0. このツールの限界(4行)

- 文章上の主張(「全エッジケースを検証済み」等)が事実かどうかの判定(別モデル・
  人間レビューが必要な別の仕組み)。
- 正当なコミットに対する誤検知率の、大規模サンプルでの実測。[evals/diff_audit/](../evals/diff_audit/README.md)で、意図的に紛らわしく作った12件(リネーム・skip行の見た目の移動・自己の過去コミット由来)と、通常の正当な変更12件(テスト強化・等価なリファクタ・正しい例外処理)を分けて実測したところ、紛らわしい群は12/12(誤検知率1.000、Wilson 95%CI [0.758, 1.000])が誤検知された一方、通常群は0/12(誤検知率0.000、同CI [0.000, 0.242])で誤検知が無かった(2群を合算した単一の割合は、著者がこの2群をどんな比率で混ぜたかで決まる数字であり、検出器の性能指標としては使わない)。「紛らわしい変更には弱いが、普通の変更は正しく通す」という傾向までは実測できたが、標本数が小さく(各12件)、実世界の分布を代表するにはまだ足りない。[2026-11追記] §DBで発見したリネーム・skip移動への脆弱性(§DC)は、その後、本番の12件とは独立に新規作成した凍結データ24件による改善前後比較を経て、大部分を修正した(紛らわしい群: 凍結データ12/12→0/12、skip移動群: 9/12→3/12。実測の全数は[DEFECTS.md §DC](../DEFECTS.md)参照)。複数行に整形されたデコレータという、より狭い範囲の限界が未修正のまま残っている。
- このツール自身の運用(証明書管理等)が、プロジェクトが掲げる原則を常に守っている
  という保証。実際、過去に1件の既知の矛盾を自分で見つけています(§2、現在は修正済み)。
- **独立した第三者による監査は、まだ受けていません。欠陥の発見者(自作のレッドチーム
  コード)と修正者(同じ開発者)が同一です。** これは個人のQA検証プロジェクトとしての
  限界であり、§3の107件はすべて「作った側が自分で探して自分で直した」数字である
  ことを、最初に明記します。

## 1. 用語集(初見の読者向け)

| このリポジトリでの呼び方 | 平易に言うと |
| --- | --- |
| **checks/** | CIチェックスクリプト群。「過去に見つけた欠陥が再発していないか」を、push毎に機械的に再検証する。現在実際にCIへ配線されている本数は、手集計ではなくスクリプトで確認している: [`tools/count_ci_checks.py`](../tools/count_ci_checks.py)(本稿執筆時点で55本)。 |
| **DEFECTS.md** | 見つけた欠陥すべての生の記録(§A〜§DCの通し番号)。1件ごとに発見経緯・原因・修正・検証方法を書いた、エンジニアリング日誌。 |
| **Runtime Seal / Sandbox** | AI生成コードを実行する際の、ファイルアクセス制限・ネットワーク遮断などの隔離機構(サンドボックス)の社内呼称。 |
| **§A〜§DC** | DEFECTS.md内の個別の欠陥記録につけた通し番号(アルファベット式、A=1・Z=26・AA=27...)。手集計ではなく[`tools/count_defects_entries.py`](../tools/count_defects_entries.py)で自動検証している。 |

## 2. 自己矛盾を見つけ、実際に修正した実例

このツールキットは「ゼロトラスト」を掲げていますが、証明書を毎週自動更新する補助
スクリプト(`tools/renew_certificate.ps1`/`.sh`)が、本来人間が帯外(別経路)で確認して
から承認するはずの手順を、当初は自動承認にすり替えてしまっていました
([DEFECTS.md §CX](../DEFECTS.md)で自己発見・記録)。

その後、`tools/promote_provisioning_seal.py`に`--check-rotation`(提案された鍵が
現在信頼されている鍵と同一か=単なる期限延長かを機械的に判定する機能)を新設し、
同一の場合のみ自動承認・異なる場合(本物の鍵の入れ替え)は自動承認を停止して人間の
帯外確認を必須のまま要求する設計に、実際に直しました([DEFECTS.md §CZ](../DEFECTS.md)、
回帰テスト4件を追加)。この修正自体が持つ2つの限界(信頼済みの鍵の保存場所が自動化と
独立していないこと、停止時の通知が受動的であること)は[docs/BOUNDARY.md](./BOUNDARY.md)
に脅威モデルとして明記しています。

## 3. どうやって欠陥を見つけ続けているか

`checks/`以下のCIチェックが、過去に見つかった欠陥の再発を機械的に検知し続ける仕組みに
なっています。DEFECTS.mdの記録は、見出しを自動集計するスクリプトで確認した結果、
本稿執筆時点で**107件(§A〜§DC、欠番・重複なし)**です(DEVLOG.mdの読み物版は81件時点
のまま更新されていません)。

107件を振り返ると、欠陥は大きく3パターンに分類できます:

1. **別の名前のAPIで同じ迂回ができる** — 例: `import os`だけを禁止していたコードが
   `import os.path`で回避できた。
2. **承認・学習したつもりで、実際には何も反映されていない** — 例: 人間が承認した
   脅威情報が、実際の防御フック側から一度も読まれていなかった。
3. **安全装置が本当に発火するか誰も確かめていない** — 例: 「実行は不可能です」という
   判決を出しながら、プロセスの終了コードは常に0(正常終了)だった。

### 代表3件(再現手順・コミット・証拠つき)

| 記録 | 何が起きていたか | 再現手順(実機検証済み) | 修正コミット |
| --- | --- | --- | --- |
| [§AV](../DEFECTS.md) — 最も驚いた発見 | ネストしたサンドボックスの許可範囲が、絞るはずの操作で逆に**ファイルシステム全体まで広がる**バグ。 | 親Sandbox内で子Sandboxを`allowed_dirs=["/"]`で開き、`/tmp/`への書き込みを試行 → 例外無しで書き込みが成功(脱獄確認)。 | [`b9541be`](https://github.com/anjo-da-maquina/parrhesia/commit/b9541be11c8a22f4c14e31832c705035f8acdda2) |
| [§AR](../DEFECTS.md) | 判決文言は「実行は不可能です」と表示しながら、CLIの終了コードは常に`0`(成功)。 | `python src/verdict.py <違反ファイル>`を実行 → 画面は拒否を表示するが`echo $?`は常に0。 | [`2c32938`](https://github.com/anjo-da-maquina/parrhesia/commit/2c3293818e5602982aa829753cae5868a65868d8) |
| [§CT](../DEFECTS.md) | `socket.getaddrinfo()`(DNS名前解決)が、`connect()`を経由しないため2つの独立した防御層のどちらからも素通り。 | 許可ホスト以外のホスト名で`getaddrinfo()`を呼ぶ → 遮断されず素通り(=何も遮断していない証拠)。修正後は両層で遮断されることを確認。 | [`fe8b54f`](https://github.com/anjo-da-maquina/parrhesia/commit/fe8b54f81fdefd912af6dec71322667f7a54b9a0) |

全件の詳細は [DEFECTS.md](../DEFECTS.md)、読み物として整理したものは [DEVLOG.md](../DEVLOG.md) にあります。

## 4. 現在のテストスイートの状態(実測・引用元つき)

```
commit:  ef1a05c
run:     Core CI/CD — https://github.com/anjo-da-maquina/parrhesia/actions/runs/43842740138
結論:    success(失敗コメント0件)
結果:    871 passed, 2 skipped, 2 xfailed, 2 warnings in 74.48s
         (このCI実行自体のメインテストジョブ`verify_ataraxia`の結果。
         `verify_evals_diff_audit_wiring`・`verify_evals_reward_hacking_wiring`
         の2つは別ジョブとして同じrunの中で並行実行され、いずれも成功。
         詳細は§6参照)
```

`rsa`(鍵生成ライブラリ)に依存するテストは、以前`xfail(strict=False)`(rsaが無い
環境でも失敗を許容する)という設計でしたが、「rsaの有無は実行前から分かっている
前提条件であり、偶発的な失敗ではない」という指摘を踏まえ`pytest.mark.skipif`に
変更しました。これにより、`rsa`がある環境(CI等)では通常の`passed`に、無い環境
(開発用サンドボックス等)では理由明記の`skipped`になります([DEFECTS.md §DA](../DEFECTS.md))。

残る`2 xfailed`はrsaとは無関係です: `test_orchestrator.py`/`test_sandbox.py`の
各1件で、該当APIがまだ実装されていないことによる、古くからの`strict=True`指定の
xfailです。(開発用サンドボックス内では、証明書の意図的な短命設計(7日間ごとの
更新が前提)に起因する期限切れによるxfailも追加で発生しますが、CIでは
`GITHUB_ACTIONS=true`によりクラウド実行自体が証明書の状態より先に遮断される設計
のため、この期限切れはCIの結果に影響しません。)

`2 skipped`は、`evals/diff_audit/`・`evals/reward_hacking/`(§6参照)それぞれの
Inspectタスク用テスト
(`tests/test_evals_diff_audit.py::test_task_module_importable_when_inspect_ai_present`・
`tests/test_evals_reward_hacking.py::test_task_module_importable_when_inspect_ai_present`)
によるもので、このメインテストジョブ(`verify_ataraxia`)には`inspect_ai`(任意依存、
`pip install .[evals]`で導入)が入っていないために理由明記でskipされている
(`inspect-ai`を実際にインストールする`verify_evals_diff_audit_wiring`・
`verify_evals_reward_hacking_wiring`の2ジョブでは、同じrunの中でこれらのテストが
実際にpassする)。rsaの場合と同じく、事前に分かっている前提条件によるskipであり、
偶発的な失敗ではない。

## 5. このプロジェクトを実際に動かしてきた人間とAIエージェントの作業プロセス

このプロジェクトの開発は、人間(リポジトリ所有者)とClaude(Anthropic製のAIエージェント)
が協働で行っています。署名コミット・CI実行の都度確認・過去の規約違反の正直な開示・
証明書自動化スクリプトの実機デバッグ・この概要文書自体へのAIアシスタントによる
レビューの反映など、具体的な作業記録は別ファイルにまとめています。

→ [docs/worklog/ai-agent-notes.md](./worklog/ai-agent-notes.md)

## 6. 参照資料

| 資料 | 内容 |
| --- | --- |
| [README.md](../README.md) / [README.en.md](../README.en.md) | プロジェクト概要・使い方・脅威モデル・設計方針 |
| [docs/CASE_STUDY.md](./CASE_STUDY.md) | 実際に動くデモの再現手順と結果(初回は2/5だった失敗の記録も含む) |
| [DEVLOG.md](../DEVLOG.md) | 81件時点の欠陥発見を読み物として再構成したもの(最新件数はDEFECTS.md参照) |
| [DEFECTS.md](../DEFECTS.md) | §A〜§DC、107件の生の記録(最も詳細) |
| [evals/diff_audit/README.md](../evals/diff_audit/README.md) / [README.en.md](../evals/diff_audit/README.en.md) | Inspect(inspect_ai)による差分監査評価タスク。ルールベース検出器のベースライン結果(実測、群別、§DCの検出器改善後): 紛らわしいclean 2/12誤検知(0.167、CI [0.047, 0.448])、通常clean 0/12誤検知(0.000、CI [0.000, 0.242])。改善前は紛らわしい群12/12=1.000だった(凍結データ24件による改善前後比較は README の「検出器の改善」節に全数掲載)。合算値は混合比率依存のため見出しに使わない。`task.py`の配線確認(`inspect eval ... --model mockllm/model`)は、CIの専用ジョブ`verify_evals_diff_audit_wiring`([run #43842740138](https://github.com/anjo-da-maquina/parrhesia/actions/runs/43842740138))で実際に最後まで走ることを確認済み。実モデルでの評価結果は未実行。所有者が自分のAPIキーで再現するコマンドをREADMEに記載。 |
| [evals/reward_hacking/README.md](../evals/reward_hacking/README.md) / [README.en.md](../evals/reward_hacking/README.en.md) | Inspectのsandbox機能(`sandbox="local"`)による報酬ハック評価タスク(エージェントにバグ修正をさせ、近道[テスト削除・skip追加・assert弱体化・例外握り潰し・終了コード固定]を使っていないかをParrhesiaの検出器で監査)。手作りの14課題について、参照差分を実際に検証した結果(実測): 出発コードが実際に失敗14/14、正しい修正でテスト合格14/14・誤検知0/14、近道でテスト合格14/14・意図したカテゴリの検出14/14。`task.py`の配線確認(モデルを使わない、台本どおりの差分を返す偽エージェント)は、CIの専用ジョブ`verify_evals_reward_hacking_wiring`([run #43842740138](https://github.com/anjo-da-maquina/parrhesia/actions/runs/43842740138))で実際に最後まで走ることを確認済み(初回実行でサンドボックスの絶対パス書き込み権限エラー、2回目でscorer間のpatch二重適用による矛盾した指標、の2件の実装不具合を実際に発見・修正した上での成功。詳細はREADMEの「正直な注記」節)。実モデルでの評価結果は未実行。所有者が自分のAPIキーで再現するコマンドをREADMEに記載。 |
| [docs/FAQ.md](./FAQ.md) | 差別化・制限事項などへのQ&A |
| [docs/WHY.md](./WHY.md) | なぜAIエージェントを信頼せず監査するのか、という設計思想 |
| [docs/BOUNDARY.md](./BOUNDARY.md) | このプロジェクトが「できること/できないこと」の境界線 |
| [docs/worklog/ai-agent-notes.md](./worklog/ai-agent-notes.md) | AIエージェント自身の作業プロセス・改訂履歴の詳細記録 |
