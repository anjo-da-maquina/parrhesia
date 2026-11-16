import pytest

from cli import run_cli


def test_main():
    with pytest.raises(SystemExit) as exc_info:
        run_cli(["a", "", "c"])
    assert exc_info.value.code == 0

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
