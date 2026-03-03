from __future__ import annotations

import argparse
from pathlib import Path

from song_archiver.downloader import DownloadError
from song_archiver.orchestrator import process_playlist_file


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
        help="Порог строгой валидации [0..1], выше = строже",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Запустить небольшой интерактивный интерфейс в терминале",
    )
    return parser


def run_interactive(args: argparse.Namespace) -> argparse.Namespace:
    print("=== Song Archiver ===")
    if not args.input:
        args.input = input("Путь к txt-файлу: ").strip()
    if args.output == "downloads":
        custom_output = input("Директория для результатов [downloads]: ").strip()
        if custom_output:
            args.output = custom_output
    custom_archive = input(f"Имя архива [{args.archive_name}]: ").strip()
    if custom_archive:
        args.archive_name = custom_archive
    custom_min_score = input(f"Min score [{args.min_score}]: ").strip()
    if custom_min_score:
        args.min_score = float(custom_min_score)
    return args


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interactive:
        args = run_interactive(args)

    if not args.input:
        parser.error("Укажите --input путь к файлу")

    try:
        archive = process_playlist_file(
            input_file=Path(args.input),
            workdir=Path(args.output),
            archive_name=args.archive_name,
            min_score=args.min_score,
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
