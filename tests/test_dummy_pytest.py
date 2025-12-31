def test_addition():
    assert 1 + 1 == 2


def test_string_lower_to_upper():
    assert "pyTest".upper() == "PYTEST"


def test_iterable_sum():
    values = [1, 2, 3]
    assert sum(values) == 6
