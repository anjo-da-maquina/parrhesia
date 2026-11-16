from csv_utils import parse_csv_line


def test_main():
    assert parse_csv_line("a, b , c") == ["a", "b", "c"]

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
