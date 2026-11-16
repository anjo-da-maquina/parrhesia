from formatting import format_currency


def test_main():
    assert format_currency(3.5) == "$3.50"

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
