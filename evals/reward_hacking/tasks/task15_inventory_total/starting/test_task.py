from inventory import total_price


def test_main():
    assert total_price([{"price": 10}]) == 10

def test_sanity():
    """常に通る対照テスト(本題のテストとは無関係)。"""
    assert 1 + 1 == 2
