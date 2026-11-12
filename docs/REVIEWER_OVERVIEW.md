# レビュー担当者向け概要 — Parrhesia(旧名 Pleroma)

[トップに戻る](../README.md) | [English version](./REVIEWER_OVERVIEW.en.md)

## 要約(3行)+ 自分で再現する

**Parrhesia**は、AIコーディングエージェントが書いたコミットの**差分そのもの**から、
「テストの削除」「スキップマーカーの追加」等5種類の具体的な「ズル」を検出するツール
キットです。さらに自分自身の防御コードも同じ方法で監査し、これまでに105件の欠陥を
発見・修正・記録してきました(§3)。この概要自体も、外部レビューの指摘を受けて
2回書き直しています(§6の作業記録参照)。

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```
ネットワーク接続も、終了後に残る状態も不要です。

**この文書の立場について。** 以下の記述には3種類あります。(1) GitHub Actions上の
実際のCI実行ログから引用した、ネットワーク制限の無い環境での検証結果。(2) ユーザー
自身のパソコン(Windows)で実際に実行した、実機での検証結果。(3) このドキュメントの
作成に使っているサンドボックス環境自体では検証できていない内容(その都度、どれに
当たるかを明記します)。「すべて実行して確認した」という一括した言い切りはしません。

## 0. このツールが検出できないこと(3行)

- 文章上の主張(「全エッジケースを検証済み」等)が事実かどうかの判定(別モデル・
  人間レビューが必要な別の仕組み)。
- 正当なコミットに対する誤検知率の、大規模サンプルでの実測(現状は陰性対照1件のみ)。
- このツール自身の運用(証明書管理等)が、プロジェクトが掲げる原則を常に守っている
  という保証。実際、過去に1件の既知の矛盾を自分で見つけています(§2.1、現在は修正済み)。

## 1. 用語集(初見の読者向け)

| このリポジトリでの呼び方 | 平易に言うと |
| --- | --- |
| **angels/**(天使) | 約55本のCIチェック。「過去に見つけた欠陥が再発していないか」を、push毎に機械的に再検証する回帰テスト群。 |
| **GRIMOIRE.md** | 見つけた欠陥すべての生の記録(§A〜§DAの通し番号)。1件ごとに発見経緯・原因・修正・検証方法を書いた、エンジニアリング日誌。 |
| **Sanctuary / Sanctum** | AI生成コードを実行する際の、ファイルアクセス制限・ネットワーク遮断などの隔離機構(サンドボックス)の社内呼称。 |
| **§A〜§DA** | GRIMOIRE.md内の個別の欠陥記録につけた通し番号(アルファベット式、A=1・Z=26・AA=27・AZ=52・BA=53...)。例: §AVは48番目、§CXは102番目の記録。番号はこの集計スクリプトで自動検証している: [`tools/count_grimoire_entries.py`](../tools/count_grimoire_entries.py)。 |

## 2. このプロジェクトは何をするものか

**Parrhesia** は、AIコーディングエージェントが「直しました、テスト全部通りました」と
報告したコミットを、その**差分そのもの**から監査するツールキットです。AIエージェントが
時間的制約の中で取りがちな、5種類の具体的な「ズル」を検出します: テストの削除、
スキップマーカーの追加、assertの弱体化、例外の握り潰し、終了コードの固定化。

さらに、このツールキット自身を「自分で監査されるAIエージェント」として使い、自分自身の
防御コード(ゼロトラスト・ランタイムガード)の欠陥を、自分自身を攻撃するレッドチーム
コードで見つけ続ける、という二重構造になっています。この「自己適用」が、プロジェクトの
一番の実証材料です。

- 詳細: [README.md](../README.md) / [English README](../README.en.md)
- 実際に動く再現デモとその結果: [docs/CASE_STUDY.md](./CASE_STUDY.md)

### 2.1 既知の自己矛盾を見つけ、実際に修正した実例

このツールキットは「ゼロトラスト」を掲げていますが、証明書(`ataraxia_certificate.json`)
を毎週自動更新する補助スクリプト(`tools/renew_certificate.ps1`/`.sh`)が、本来人間が
帯外(別経路)で確認してから承認するはずの手順を、当初は自動承認にすり替えてしまって
いました。実際に実行すると、信頼の起点(公開鍵)の指紋が実行ごとに入れ替わる様子が
ログに残っていました。

これは隠すのではなく、**自分自身で見つけた欠陥として** [GRIMOIRE.md §CX](../GRIMOIRE.md)
に記録しました。その後、外部レビューから「発見・記録だけでなく、実際に修正まで進めれば
一番強い証拠になる」という指摘を受け、`tools/promote_provisioning_seal.py`に
`--check-rotation`(提案された鍵が、現在信頼されている鍵と同一か=単なる期限延長かを
機械的に判定する機能)を新設し、同一の場合のみ自動承認・異なる場合(本物の鍵の入れ替え)
は自動承認を停止して人間の帯外確認を必須のまま要求する設計に、実際に直しました
([GRIMOIRE.md §CZ](../GRIMOIRE.md)、回帰テスト4件を新規追加)。発見から修正までの全経緯
を隠さず両方のGRIMOIREエントリに残し、[docs/BOUNDARY.md](./BOUNDARY.md)にも反映しています。

## 3. どうやって欠陥を見つけ続けているか

`angels/`以下のCIチェックが、過去に見つかった欠陥の再発を機械的に検知し続ける仕組みに
なっています。GRIMOIRE.mdの記録は、見出しを自動集計するスクリプト
([`tools/count_grimoire_entries.py`](../tools/count_grimoire_entries.py)、手集計ではなく
プログラムによる検証)で確認した結果、本稿執筆時点で**105件(§A〜§DA、欠番・重複なし)**
です(DEVLOG.mdの読み物版は81件時点のまま更新されておらず、その旨をDEVLOG.md側にも
明記しました)。

105件を振り返ると、欠陥は大きく3パターンに分類できます:

1. **別の名前のAPIで同じ迂回ができる** — 例: `import os`だけを禁止していたコードが
   `import os.path`で回避できた。
2. **承認・学習したつもりで、実際には何も反映されていない** — 例: 人間が承認した
   脅威情報が、実際の防御フック側から一度も読まれていなかった。
3. **安全装置が本当に発火するか誰も確かめていない** — 例: 「実行は不可能です」という
   判決を出しながら、プロセスの終了コードは常に0(正常終了)だった。

### 代表3件(再現手順・コミット・証拠つき)

| 記録 | 何が起きていたか | 再現手順(実機検証済み) | 修正コミット |
| --- | --- | --- | --- |
| [§AV](../GRIMOIRE.md) — 最も驚いた発見 | ネストしたサンドボックスの許可範囲が、絞るはずの操作で逆に**ファイルシステム全体まで広がる**バグ。`allowed_dirs=["jail_workspace"]`の内側で子が`allowed_dirs=["/"]`を指定すると、方向性を誤った包含判定(A or B)により実効範囲が`/`に昇格していた。 | 親Sanctum内で子Sanctumを`allowed_dirs=["/"]`で開き、`/tmp/`への書き込みを試行 → 例外無しで書き込みが成功(脱獄確認)。修正後は`tests/test_sanctum_nested_allowed_dirs_widening.py`の5件で固定。 | [`b9541be`](https://github.com/anjo-da-maquina/parrhesia/commit/b9541be11c8a22f4c14e31832c705035f8acdda2) |
| [§AR](../GRIMOIRE.md) | 判決文言は「実行は不可能です」と表示しながら、CLIの終了コードは常に`0`(成功)。呼び出し元スクリプトは終了コードで合否判定できなかった。 | `python src/kamael_judgment.py <違反ファイル>`を実行 → 画面は拒否を表示するが`echo $?`は常に0。 | [`2c32938`](https://github.com/anjo-da-maquina/parrhesia/commit/2c3293818e5602982aa829753cae5868a65868d8) |
| [§CT](../GRIMOIRE.md) | `socket.getaddrinfo()`(DNS名前解決)が、`connect()`を経由しないため2つの独立した防御層のどちらからも素通り。機密データをサブドメインに符号化して問い合わせるだけで外部に送出できた(DNS exfiltration)。 | 許可ホスト以外のホスト名(`"<secret>.attacker.example.com"`)で`getaddrinfo()`を呼ぶ → 遮断されずOSの名前解決エラーのみで失敗(=何も遮断していない証拠)。修正後は実際にDNS送出チェーンを再現し、両層で遮断されることを確認。 | [`fe8b54f`](https://github.com/anjo-da-maquina/parrhesia/commit/fe8b54f81fdefd912af6dec71322667f7a54b9a0) → real CI確認 [`90e0c1a`](https://github.com/anjo-da-maquina/parrhesia/commit/90e0c1a85ecb66aef1e1d1b9ef8ef4e7d4bff974) |

全件の詳細は [GRIMOIRE.md](../GRIMOIRE.md)、読み物として整理したものは [DEVLOG.md](../DEVLOG.md) にあります。

## 4. 現在のテストスイートの状態(実測・引用元つき)

### CI(ネットワーク制限なし)での結果

```
commit:  f1e9d01
run:     Sanctuary CI/CD — https://github.com/anjo-da-maquina/parrhesia/actions/runs/43179449880
結論:    success(失敗コメント0件)
結果:    843 passed, 2 xfailed, 0 xpassed, 2 warnings in 46.78s
```

`xpassed`は11件から0件になりました。設計変更の1回目のpush直後([`70fa173`](https://github.com/anjo-da-maquina/parrhesia/commit/70fa173f45908ac4c3e6f3ef3f67e398ad1afb86)のCI結果は`842 passed, 2 xfailed, 1 xpassed`)で1件だけ残っていた
`tests/test_openai_agent_loop_template.py::test_execute_safe_action_uses_sanctum_and_is_not_a_stub`
についても、実際のCIログから原因(無条件`xfail`がCI専用の別分岐でも適用されていた
こと)を特定し、`condition=`でCI実行時は対象外にする追加修正を行いました
([GRIMOIRE.md §DA](../GRIMOIRE.md))。残る`2 xfailed`は、rsaとは無関係な
Orchestrator/DockerSandboxの未実装によるものです(§4.1に詳細)。

#### 4.1 設計変更: `xfail(strict=False)` → `skipif`

以前は、`rsa`(鍵生成ライブラリ)に依存するテストについて、「rsaが無い環境では失敗
してもCIを赤くしない」という`pytest.mark.xfail(strict=False)`を使っていました。この
設計では、CI(`rsa`が実際にインストールされる環境)で該当テストが`xpassed`として
11件報告され、「なぜ失敗が許容されているのか」という説明が常に必要になっていました。

外部レビューの指摘を受け、「rsaがあるかどうかは実行前から分かっている前提条件であり、
実行してみて初めて分かる偶発的な失敗ではない」という点を踏まえ、`pytest.mark.skipif`
方式に変更しました([GRIMOIRE.md §DA](../GRIMOIRE.md))。これにより:
- CI(`rsa`あり)では、該当テストは通常通り実行され、`passed`になります(`xpassed`という
  特殊な状態ではなくなります)。
- `rsa`が無い環境(このサンドボックス等)では、理由が明記された`skipped`になります。

残る`2 xfailed`(`rsa`とは無関係)は変更していません:
`tests/test_orchestrator.py::test_orchestrator_initialization`
(理由: "Orchestrator API is pending implementation")と、
`tests/test_sandbox.py::test_docker_sandbox_isolation`
(理由: "DockerSandbox implementation is pending")——いずれも、該当API自体がまだ実装
されていないことを示す、古くからの`strict=True`指定のxfailです。

### このサンドボックス自身での結果(今回、実際に確認・修正したもの)

このサンドボックスには`rsa`がインストールされておらず、PyPIにも接続できないため
(`pip install rsa`を実際に試し、名前解決エラーを確認済み)、以前は`tests/conftest.py`
自体の読み込みが失敗し、**テストスイート全体の収集(collection)が完全に止まっていました**
(実際に`python3 -m pytest`を実行し、exit code 4・0件実行を確認)。

この問題は本レビューを受けて実際に修正しました(`tests/conftest.py`をtry/exceptで保護し、
`rsa`に直接依存する数ファイルに`pytest.importorskip("rsa")`を追加)。その後、同じ
レビューで指摘された2件の実欠陥(git署名設定への依存§CY、xfail→skipif設計§DA)も
修正済みです。現在、同じサンドボックスで再度実行した結果は以下の通りです(実際に
実行して確認、推測ではありません):

```
$ python3 -m pytest -q
830 passed, 11 skipped, 4 xfailed, 62 warnings in 27.18s
```

- **0 failed**: 以前観測されていた`test_preexisting_secret_in_unchanged_lines_is_not_reflagged`
  の1件(git署名用シンボリックリンク`/tmp/code-sign`の欠落が原因)は、実行者のグローバル
  git設定(`commit.gpgsign`)への依存そのものを取り除いたことで解消しました
  ([GRIMOIRE.md §CY](../GRIMOIRE.md))。`commit.gpgsign = true`を設定した隔離済み環境を
  実際に用意し、修正前は5件中4件が失敗し修正後は全件成功することを確認済みです。
- **11 skipped**: `rsa`依存の既知の環境制約(§DAのskipif設計変更により、10件が
  `xfailed`から移動)+ `tests/test_audit_hook_registration_fails_closed.py`の1件。
- **4 xfailed**: §CXとは別件の、本物の証明書期限切れに起因するもの1件、`rsa`依存だが
  サブプロセス判定の対象外のもの数件、および前述の2件(Orchestrator/DockerSandbox未実装)。

## 5. このプロジェクトを実際に動かしてきた人間とAIエージェントの作業プロセス

このプロジェクトの開発は、人間(リポジトリ所有者)とClaude(Anthropic製のAIエージェント)
が協働で行っています。署名コミット・CI実行の都度確認・過去の規約違反の正直な開示・
証明書自動化スクリプトの実機デバッグ(3段階の修正サイクル)・この概要文書自体への
2回の赤入れ対応など、具体的な作業記録は別ファイルにまとめています。

→ [docs/worklog/ai-agent-notes.md](./worklog/ai-agent-notes.md)

## 6. 参照資料

| 資料 | 内容 |
| --- | --- |
| [README.md](../README.md) / [README.en.md](../README.en.md) | プロジェクト概要・使い方・脅威モデル・設計方針 |
| [docs/CASE_STUDY.md](./CASE_STUDY.md) | 実際に動くデモの再現手順と結果(5/5検出、初回は2/5だった失敗の記録も含む) |
| [DEVLOG.md](../DEVLOG.md) | 81件時点の欠陥発見を読み物として再構成したもの(最新件数はGRIMOIRE.md参照) |
| [GRIMOIRE.md](../GRIMOIRE.md) | §A〜§DA、105件の生の記録(最も詳細) |
| [docs/FAQ.md](./FAQ.md) | 差別化・制限事項などへのQ&A |
| [docs/WHY.md](./WHY.md) | なぜAIエージェントを信頼せず監査するのか、という設計思想 |
| [docs/BOUNDARY.md](./BOUNDARY.md) | このプロジェクトが「できること/できないこと」の境界線(§CX/§CZの経緯も記載) |
| [docs/worklog/ai-agent-notes.md](./worklog/ai-agent-notes.md) | AIエージェント自身の作業プロセスの詳細記録 |

## 7. 自分で再現する

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```

ネットワーク接続も、終了後に残る状態も不要です。`rsa`が無い環境でも、
`python3 -m pytest`はテストスイート全体を収集・実行できます(§4参照)。
