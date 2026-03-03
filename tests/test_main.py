from main import _normalize_path_value


def test_normalize_path_value_strips_wrapping_double_quotes() -> None:
    assert _normalize_path_value('"C:/Users/test/songs.txt"') == "C:/Users/test/songs.txt"


def test_normalize_path_value_strips_wrapping_single_quotes() -> None:
    assert _normalize_path_value("'C:/Users/test/songs.txt'") == "C:/Users/test/songs.txt"


def test_normalize_path_value_keeps_inner_quotes() -> None:
    assert _normalize_path_value('C:/Music/Best "Hits"/songs.txt') == 'C:/Music/Best "Hits"/songs.txt'
