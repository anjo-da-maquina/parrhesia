#!/usr/bin/env python3
"""DEFECTS.md の欠陥記録(§A, §B, ..., §Z, §AA, ..., §CX)を見出しから
自動集計し、正しいアルファベット式の通し番号と対応させる。

これまで「§AVは32番目」のように手で数えて記述していた箇所が、実際の
欠陥番号の進み方(A=1, ..., Z=26, AA=27, AB=28, ..., AZ=52, BA=53, ...)
と合っていなかったため、二度と手集計で誤らないようにする目的で作成。

このプロジェクトの「## 2.」節(ScanSource/AuditHook/Raphaelの説明)もA/B/Cの
見出しを使っているが、これは欠陥記録ではないため、本スクリプトは
「## 5. 既知の限界」以降に出現する見出しだけを対象とする。
"""
import re
import sys

PATH = "DEFECTS.md"


def letters_to_index(letters: str) -> int:
    """'A'->1, 'Z'->26, 'AA'->27, 'AB'->28, ... の変換(26進数+1)。"""
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def index_to_letters(n: int) -> str:
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(rem + ord("A")) + letters
    return letters


def main():
    with open(PATH, encoding="utf-8") as f:
        lines = f.readlines()

    # 「## 5. 既知の限界」以降だけを対象にする(それより前の「## 2.」節の
    # A/B/C見出しはScanSource/AuditHook/Raphaelの説明であり、欠陥記録ではない)。
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^\\?##\s*5\.", line):
            start = i
            break
    if start is None:
        print("エラー: '## 5.' セクションが見つかりません", file=sys.stderr)
        sys.exit(1)

    body = lines[start:]

    # 2つの見出し形式:
    #   \### A. 本文        (バックスラッシュエスケープ、§無し、初期の記録)
    #   ### §BQ: 本文        (§付き、§BQ以降)
    pattern_plain = re.compile(r"^\\?###\s+([A-Z]+)\.\s")
    pattern_section = re.compile(r"^###\s+§([A-Z]+):\s")

    entries = []  # (letters, line_no, raw_line)
    for i, line in enumerate(body):
        m = pattern_plain.match(line)
        if m:
            entries.append((m.group(1), start + i + 1, line.rstrip()))
            continue
        m = pattern_section.match(line)
        if m:
            entries.append((m.group(1), start + i + 1, line.rstrip()))
            continue

    if not entries:
        print("エラー: 欠陥記録の見出しが1件も見つかりませんでした", file=sys.stderr)
        sys.exit(1)

    print(f"検出した見出し数: {len(entries)}")
    print(f"最初: §{entries[0][0]} (行{entries[0][1]})")
    print(f"最後: §{entries[-1][0]} (行{entries[-1][1]})")
    print()

    # 連番チェック: 期待される次のletterと実際のletterを比較
    gaps = []
    duplicates = []
    seen = set()
    expected_idx = 1
    for letters, line_no, raw in entries:
        idx = letters_to_index(letters)
        if letters in seen:
            duplicates.append((letters, line_no))
        seen.add(letters)
        if idx != expected_idx:
            gaps.append((expected_idx, idx, letters, line_no))
        expected_idx = idx + 1

    if duplicates:
        print("!! 重複した見出しラベル:")
        for letters, line_no in duplicates:
            print(f"   §{letters} (行{line_no})")
        print()

    if gaps:
        print("!! 番号の不連続(欠番または順序崩れ)を検出:")
        for exp_idx, actual_idx, letters, line_no in gaps:
            exp_letters = index_to_letters(exp_idx)
            print(
                f"   期待: §{exp_letters}(通し番号{exp_idx}) -> "
                f"実際: §{letters}(通し番号{actual_idx}) (行{line_no})"
            )
        print()
    else:
        print("番号の欠番・重複なし(A, B, C, ... の順で連続)")
        print()

    total = len(entries)
    last_letters, last_line, _ = entries[-1]
    last_idx = letters_to_index(last_letters)

    print(f"合計エントリ数: {total}")
    print(f"最後のラベル §{last_letters} の通し番号: {last_idx}")
    if total != last_idx:
        print(
            f"!! 注意: 合計エントリ数({total})と最後のラベルの通し番号"
            f"({last_idx})が一致しません。欠番または重複がある可能性があります。"
        )

    # 代表的に知りたいラベルの通し番号を明示
    for target in ["AV", "AR", "CT", "CX", "CC"]:
        idx = letters_to_index(target)
        found = any(l == target for l, _, _ in entries)
        print(f"§{target}: アルファベット式通し番号 = {idx}  (実在: {found})")


if __name__ == "__main__":
    main()
