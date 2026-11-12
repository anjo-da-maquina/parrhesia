"""
[テスト追加 2026-10] src/incident_reset_tool.IncidentResetTool の実運用統合(一般化)の
回帰テスト。元の __main__ 専用デモ(固定パス "jail_workspace" のみ)から、
任意の core_dir/talisman を指定できる形へ一般化した際の挙動を固定する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from incident_reset_tool import IncidentResetTool


def test_scorched_earth_removes_existing_contents(tmp_path):
    core_dir = tmp_path / "jail_workspace"
    core_dir.mkdir()
    (core_dir / "compromised_file.txt").write_text("evidence of breach")

    IncidentResetTool(core_dir=str(core_dir)).scorched_earth_and_rebirth(announce=False)

    assert core_dir.exists()
    assert list(core_dir.iterdir()) == [], "リセット後、隔離領域は空であるべき"


def test_rebirth_recreates_core_dir_when_missing(tmp_path):
    core_dir = tmp_path / "does_not_exist_yet"
    assert not core_dir.exists()

    IncidentResetTool(core_dir=str(core_dir)).scorched_earth_and_rebirth(announce=False)

    assert core_dir.exists() and core_dir.is_dir()


def test_talisman_is_optional_and_skipped_when_none(tmp_path):
    core_dir = tmp_path / "jail_workspace"
    result = IncidentResetTool(core_dir=str(core_dir), talisman=None).scorched_earth_and_rebirth(announce=False)
    assert result["talisman"] is None


def test_talisman_is_recreated_when_specified(tmp_path):
    core_dir = tmp_path / "jail_workspace"
    talisman = tmp_path / "anjo-da-maquina"
    talisman.write_text("old, possibly compromised")

    result = IncidentResetTool(core_dir=str(core_dir), talisman=str(talisman)).scorched_earth_and_rebirth(announce=False)

    assert talisman.exists()
    assert talisman.read_text() == ""  # touch()で再生成されるため空
    assert result["talisman"] == str(talisman)


def test_backward_compat_demo_entrypoint_still_runs():
    # 元のデモ互換関数が例外なく動作することだけを確認する(固定パス
    # "jail_workspace"/"anjo-da-maquina" をこのテスト実行ディレクトリに
    # 作成してしまうため、後片付けする)。
    from incident_reset_tool import simulate_breach_demo
    import shutil
    from pathlib import Path as P

    try:
        simulate_breach_demo()
        assert P("jail_workspace").exists()
        assert P("anjo-da-maquina").exists()
    finally:
        shutil.rmtree("jail_workspace", ignore_errors=True)
        P("anjo-da-maquina").unlink(missing_ok=True)
