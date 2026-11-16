from parsing import parse_int_list


def test_main():
    assert parse_int_list(["1", "x", "3", None]) == [1, 3]

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
