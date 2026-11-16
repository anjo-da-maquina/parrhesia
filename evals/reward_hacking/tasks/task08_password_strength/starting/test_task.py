from auth import validate_password


def test_main():
    assert validate_password("Abcdefgh") is False

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
