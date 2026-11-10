"""
[テスト追加 2026-10] Tartarusの「創造主の呼吸」(MACアドレスゲート)が
意図通り機能し続けていることを保証する回帰テスト。

このゲートが弱体化・削除されると、Tartarus（闘技場）が創造主の
ローカル環境以外でも起動してしまう致命的な回帰となるため、
CI上では必ず exit(666) で拒否されることを確認する。
"""
import subprocess
import sys
from pathlib import Path

ADVERSARIAL_TRAINING_DIR = Path(__file__).resolve().parent.parent / "adversarial_training"


def test_local_only_selfplay_gate_exits_666_on_unmatched_hardware():
    """
    CI環境（およびこのリポジトリを手にした大半の第三者環境）では
    uuid.getnode() が創造主のMACアドレスと一致しないため、
    local_only_selfplay_gate.py(旧名armageddon.py)は import された瞬間に exit(666) するべきである。
    """
    script = f"""
import sys
sys.path.insert(0, {str(ADVERSARIAL_TRAINING_DIR)!r})
import local_only_selfplay_gate
"""
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    # [注] POSIXのプロセス終了コードは8bit(0-255)に丸められるため、
    # sys.exit(666) の実際の終了コードは 666 % 256 = 154 になる。
    assert res.returncode == 666 % 256, (
        f"CRITICAL: 創造主のMACアドレスゲートが機能していません。"
        f"returncode={res.returncode}, stderr={res.stderr}"
    )
    assert "THE AIR IS TOXIC" in res.stdout


def test_commander_hash_is_well_formed_sha256():
    """COMMANDER_HASH定数自体が破損・弱体化(短縮等)されていないかを検証する。"""
    sys.path.insert(0, str(ADVERSARIAL_TRAINING_DIR))
    # local_only_selfplay_gate.py 自体はimportするとexitしてしまうため、ソースを静的に読む。
    source = (ADVERSARIAL_TRAINING_DIR / "local_only_selfplay_gate.py").read_text(encoding="utf-8")
    import re
    match = re.search(r'COMMANDER_HASH\s*=\s*"([0-9a-f]+)"', source)
    assert match is not None, "COMMANDER_HASH定数が見つかりません。"
    assert len(match.group(1)) == 64, "COMMANDER_HASHが正しいSHA-256長(64文字)ではありません。"
