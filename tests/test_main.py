from main import _build_proxy_url, _normalize_path_value


def test_normalize_path_value_strips_wrapping_double_quotes() -> None:
    assert _normalize_path_value('"C:/Users/test/songs.txt"') == "C:/Users/test/songs.txt"


def test_normalize_path_value_strips_wrapping_single_quotes() -> None:
    assert _normalize_path_value("'C:/Users/test/songs.txt'") == "C:/Users/test/songs.txt"


def test_normalize_path_value_keeps_inner_quotes() -> None:
    assert _normalize_path_value('C:/Music/Best "Hits"/songs.txt') == 'C:/Music/Best "Hits"/songs.txt'


def test_build_proxy_url_with_credentials() -> None:
    assert _build_proxy_url("154.218.23.64:62794", "user", "pass") == "http://user:pass@154.218.23.64:62794"


def test_build_proxy_url_without_credentials() -> None:
    assert _build_proxy_url("154.218.23.64:62794") == "http://154.218.23.64:62794"
