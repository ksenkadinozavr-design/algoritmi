from __future__ import annotations

import argparse
from pathlib import Path

from song_archiver.downloader import DownloadError
from song_archiver.orchestrator import process_playlist_file

DEFAULT_PROXY_HOST = "154.218.23.64:62794"
DEFAULT_PROXY_USER = "FajEdqBYN"
DEFAULT_PROXY_PASSWORD = "CDYN99hjD"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Скачивание песен из текстового списка с группировкой и ZIP-архивом"
    )
    parser.add_argument("--input", "-i", help="Путь к txt-файлу со списком песен")
    parser.add_argument("--output", "-o", default="downloads", help="Рабочая директория")
    parser.add_argument("--archive-name", default="songs_archive", help="Имя итогового zip (без .zip)")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.78,
        help="Порог строгой валидации [0..1], выше = строже (в режиме прямых ссылок не используется)",
    )
    parser.add_argument(
        "--proxy",
        default=DEFAULT_PROXY_HOST,
        help="Прокси host:port или полный URL http://user:pass@host:port",
    )
    parser.add_argument("--proxy-user", default=DEFAULT_PROXY_USER, help="Логин для прокси")
    parser.add_argument("--proxy-password", default=DEFAULT_PROXY_PASSWORD, help="Пароль для прокси")
    parser.add_argument("--max-attempts", type=int, default=5, help="Максимум попыток на одну песню")
    parser.add_argument(
        "--search-providers",
        default="scsearch,bandcampsearch,ytsearch",
        help="Провайдеры поиска через yt-dlp (через запятую), например: scsearch,bandcampsearch,ytsearch",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Запустить небольшой интерактивный интерфейс в терминале",
    )
    return parser


def _normalize_path_value(value: str) -> str:
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"\"", "'"}:
        normalized = normalized[1:-1].strip()
    return normalized


def _build_proxy_url(proxy: str | None, user: str | None = None, password: str | None = None) -> str | None:
    if not proxy:
        return None

    proxy = _normalize_path_value(proxy)
    if not proxy:
        return None

    if proxy.startswith("http://") or proxy.startswith("https://"):
        return proxy

    if user and password:
        return f"http://{user}:{password}@{proxy}"

    return f"http://{proxy}"


def run_interactive(args: argparse.Namespace) -> argparse.Namespace:
    print("=== Song Archiver ===")
    if not args.input:
        args.input = _normalize_path_value(input("Путь к txt-файлу: "))
    if args.output == "downloads":
        custom_output = input("Директория для результатов [downloads]: ").strip()
        if custom_output:
            args.output = _normalize_path_value(custom_output)

    custom_proxy = input(f"Прокси [{args.proxy}]: ").strip()
    if custom_proxy:
        args.proxy = _normalize_path_value(custom_proxy)
    custom_proxy_user = input(f"Прокси логин [{args.proxy_user}]: ").strip()
    if custom_proxy_user:
        args.proxy_user = custom_proxy_user
    custom_proxy_password = input("Прокси пароль [скрыт]: ").strip()
    if custom_proxy_password:
        args.proxy_password = custom_proxy_password

    custom_archive = input(f"Имя архива [{args.archive_name}]: ").strip()
    if custom_archive:
        args.archive_name = custom_archive
    return args


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interactive:
        args = run_interactive(args)

    if args.input:
        args.input = _normalize_path_value(args.input)
    if args.output:
        args.output = _normalize_path_value(args.output)

    if not args.input:
        parser.error("Укажите --input путь к файлу")

    proxy_url = _build_proxy_url(args.proxy, args.proxy_user, args.proxy_password)
    search_providers = tuple(p.strip() for p in args.search_providers.split(",") if p.strip())

    try:
        archive = process_playlist_file(
            input_file=Path(args.input),
            workdir=Path(args.output),
            archive_name=args.archive_name,
            min_score=args.min_score,
            proxy_url=proxy_url,
            max_attempts=args.max_attempts,
            search_providers=search_providers,
        )
    except DownloadError as exc:
        print(f"Ошибка: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Неожиданная ошибка: {exc}")
        return 1

    print(f"Готово: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
