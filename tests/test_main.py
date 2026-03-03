from main import (
    DEFAULT_PROXY_HOST,
    DEFAULT_PROXY_PASSWORD,
    DEFAULT_PROXY_USER,
    _build_proxy_url,
    _normalize_path_value,
    build_parser,
)


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


def test_parser_defaults_use_configured_proxy() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.proxy == DEFAULT_PROXY_HOST
    assert args.proxy_user == DEFAULT_PROXY_USER
    assert args.proxy_password == DEFAULT_PROXY_PASSWORD
    assert args.max_attempts == 5
    assert args.search_providers == "scsearch,bandcampsearch,ytsearch"
