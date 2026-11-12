#!/usr/bin/env python3
"""`checks/`配下の回帰チェックスクリプトが、実際にCIワークフローへ
何本配線されているかを自動集計する。

評価者向け概要で「約55本」と書いていた数字が、DEFECTS.mdの欠陥件数と
同様に手集計・推測であってはならないという指摘を受けて作成した。
`.github/workflows/*.yml`内で実際に`python checks/<name>.py`として
実行されているステップだけを数える(`checks/_common.py`のような
共有ヘルパーは、チェックそのものではないため対象外)。
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def main():
    pattern = re.compile(r"checks/(\w+)\.py")
    found = set()
    for wf in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        for m in pattern.finditer(text):
            found.add(m.group(1))

    print(f"CIワークフロー内で実際に実行されているchecks/配下のスクリプト数: {len(found)}")
    for name in sorted(found):
        print(f"  - checks/{name}.py")

    # 参考: checks/配下に実在するが、CIに一度も配線されていないファイルがあれば警告する
    angels_dir = REPO_ROOT / "checks"
    on_disk = {
        p.stem for p in angels_dir.glob("*.py")
        if p.stem not in ("__init__", "_common")
    }
    unwired = on_disk - found
    if unwired:
        print()
        print("!! 注意: checks/配下に存在するが、CIに配線されていないファイル:")
        for name in sorted(unwired):
            print(f"  - checks/{name}.py")


if __name__ == "__main__":
    main()
