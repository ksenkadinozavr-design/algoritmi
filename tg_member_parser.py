#!/usr/bin/env python3
"""Telegram member parser (Telethon).

Exports Telegram chat participants with robust handling of flood waits/retries.
By default keeps only users that have both username and profile photo.
Additionally writes a sorted TXT file with usernames only.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

from telethon import TelegramClient, functions, types
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    RPCError,
    ServerError,
)
from telethon.sessions import StringSession


@dataclass
class Config:
    chat: str
    limit: int | None
    dry_run: bool
    output_format: str
    output: Path
    include_all: bool
    page_size: int
    pause_seconds: float
    max_retries: int
    session_file: str
    use_string_session: bool
    usernames_output: Path | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse Telegram chat participants and export members that have both "
            "username and profile photo."
        )
    )
    parser.add_argument("--chat", required=True, help="@username, id, or t.me link")
    parser.add_argument("--limit", type=int, default=None, help="Max users to inspect")
    parser.add_argument("--dry-run", action="store_true", help="Do not save files")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", dest="output_format")
    parser.add_argument("--output", type=Path, default=Path("members_export.csv"))
    parser.add_argument("--include-all", action="store_true", help="Export all users with flags")
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--pause-seconds", type=float, default=0.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--session", default="telegram.session", help="Path to .session file")
    parser.add_argument(
        "--string-session",
        action="store_true",
        help="Use StringSession from TG_STRING_SESSION env",
    )
    parser.add_argument(
        "--usernames-output",
        type=Path,
        default=None,
        help="TXT file for sorted usernames only (default: <output_stem>_usernames.txt)",
    )
    return parser.parse_args()


def normalize_chat(chat: str) -> str | int:
    value = chat.strip()
    for prefix in ("https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    if value.startswith("t.me/"):
        value = value[5:]
    value = value.strip("/")
    if value.startswith("@"):
        value = value[1:]
    if value.lstrip("-").isdigit():
        try:
            return int(value)
        except ValueError:
            return value
    return value


def load_config(ns: argparse.Namespace) -> Config:
    usernames_output = ns.usernames_output
    if usernames_output is None:
        usernames_output = ns.output.with_name(f"{ns.output.stem}_usernames.txt")

    return Config(
        chat=ns.chat,
        limit=ns.limit,
        dry_run=ns.dry_run,
        output_format=ns.output_format,
        output=ns.output,
        include_all=ns.include_all,
        page_size=max(1, ns.page_size),
        pause_seconds=max(0.0, ns.pause_seconds),
        max_retries=max(0, ns.max_retries),
        session_file=ns.session,
        use_string_session=ns.string_session,
        usernames_output=usernames_output,
    )


def get_credentials() -> tuple[int, str, str | None]:
    api_id_raw = os.getenv("TG_API_ID") or os.getenv("API_ID")
    api_hash = os.getenv("TG_API_HASH") or os.getenv("API_HASH")
    string_session = os.getenv("TG_STRING_SESSION")

    if not api_id_raw or not api_hash:
        raise SystemExit(
            "Missing API credentials. Set TG_API_ID/API_ID and TG_API_HASH/API_HASH in environment."
        )
    try:
        api_id = int(api_id_raw)
    except ValueError as exc:
        raise SystemExit("TG_API_ID/API_ID must be an integer.") from exc
    return api_id, api_hash, string_session


async def with_retries(
    call: Callable[[], Awaitable[Any]],
    *,
    max_retries: int,
    pause_seconds: float,
) -> Any:
    attempt = 0
    while True:
        try:
            return await call()
        except FloodWaitError as exc:
            jitter = random.uniform(0.5, 1.5)
            wait_for = exc.seconds + jitter
            print(f"[WARN] FloodWaitError: waiting {wait_for:.2f}s...")
            await asyncio.sleep(wait_for)
        except (ServerError, OSError, asyncio.TimeoutError, RPCError) as exc:
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(f"Exceeded max retries ({max_retries})") from exc
            sleep_for = pause_seconds + (2 ** min(attempt, 5)) + random.uniform(0.1, 0.9)
            print(f"[WARN] Temporary error ({type(exc).__name__}), retry {attempt}/{max_retries} in {sleep_for:.2f}s")
            await asyncio.sleep(sleep_for)


def to_iso8601(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def user_row(user: types.User, joined_at: datetime | None) -> dict[str, Any]:
    photo_id = getattr(user.photo, "photo_id", None)
    return {
        "user_id": user.id,
        "username": user.username,
        "has_photo": photo_id is not None,
        "photo_id": photo_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_bot": bool(user.bot),
        "is_deleted": bool(user.deleted),
        "date_joined": to_iso8601(joined_at),
    }


async def fetch_channel_members(
    client: TelegramClient,
    channel: types.Channel,
    *,
    limit: int | None,
    page_size: int,
    pause_seconds: float,
    max_retries: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        if limit is not None and len(rows) >= limit:
            break
        current_limit = page_size
        if limit is not None:
            current_limit = min(current_limit, limit - len(rows))
            if current_limit <= 0:
                break

        async def _request() -> Any:
            return await client(
                functions.channels.GetParticipantsRequest(
                    channel=channel,
                    filter=types.ChannelParticipantsSearch(""),
                    offset=offset,
                    limit=current_limit,
                    hash=0,
                )
            )

        result = await with_retries(
            _request,
            max_retries=max_retries,
            pause_seconds=pause_seconds,
        )

        if not result.users:
            break

        participant_by_user_id = {p.user_id: p for p in result.participants if getattr(p, "user_id", None)}
        for user in result.users:
            participant = participant_by_user_id.get(user.id)
            joined_at = getattr(participant, "date", None)
            rows.append(user_row(user, joined_at))

        offset += len(result.users)
        if len(result.users) < current_limit:
            break
        if pause_seconds > 0:
            await asyncio.sleep(pause_seconds)

    return rows


async def fetch_chat_members(
    client: TelegramClient,
    entity: types.TypeChat,
    *,
    limit: int | None,
    page_size: int,
    pause_seconds: float,
    max_retries: int,
) -> list[dict[str, Any]]:
    if isinstance(entity, types.Channel):
        return await fetch_channel_members(
            client,
            entity,
            limit=limit,
            page_size=page_size,
            pause_seconds=pause_seconds,
            max_retries=max_retries,
        )

    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        if limit is not None and len(rows) >= limit:
            break

        current_limit = page_size
        if limit is not None:
            current_limit = min(current_limit, limit - len(rows))
            if current_limit <= 0:
                break

        async def _collect_page() -> list[types.User]:
            page_users: list[types.User] = []
            async for user in client.iter_participants(entity, limit=current_limit, offset=offset):
                page_users.append(user)
            return page_users

        page_users = await with_retries(
            _collect_page,
            max_retries=max_retries,
            pause_seconds=pause_seconds,
        )

        if not page_users:
            break

        for user in page_users:
            participant_obj = getattr(user, "participant", None)
            joined_at = getattr(participant_obj, "date", None)
            rows.append(user_row(user, joined_at))

        offset += len(page_users)
        if len(page_users) < current_limit:
            break
        if pause_seconds > 0:
            await asyncio.sleep(pause_seconds)

    return rows


def apply_filter(rows: Iterable[dict[str, Any]], include_all: bool) -> list[dict[str, Any]]:
    if include_all:
        return list(rows)
    return [r for r in rows if r["username"] and r["has_photo"]]


def save_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "user_id",
        "username",
        "has_photo",
        "photo_id",
        "first_name",
        "last_name",
        "is_bot",
        "is_deleted",
        "date_joined",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def save_usernames_txt(path: Path, rows: list[dict[str, Any]]) -> int:
    usernames = sorted({r["username"] for r in rows if r.get("username")})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for username in usernames:
            f.write(f"{username}\n")
    return len(usernames)


def print_dry_run_summary(all_rows: list[dict[str, Any]], filtered: list[dict[str, Any]]) -> None:
    print("\nDry-run summary")
    print(f"- checked: {len(all_rows)}")
    print(f"- matched filter (username + photo): {sum(1 for r in all_rows if r['username'] and r['has_photo'])}")
    print(f"- would export: {len(filtered)}")

    preview = filtered[:5]
    if preview:
        print("\nPreview rows:")
        for row in preview:
            print(json.dumps(row, ensure_ascii=False))


async def async_main(config: Config) -> int:
    api_id, api_hash, string_session = get_credentials()

    print("[INFO] Security reminder: Telegram session files/string sessions grant full account access. Keep them secret.")

    session_obj: str | StringSession = config.session_file
    if config.use_string_session:
        if not string_session:
            raise SystemExit("--string-session set but TG_STRING_SESSION env var is missing.")
        session_obj = StringSession(string_session)

    client = TelegramClient(
        session=session_obj,
        api_id=api_id,
        api_hash=api_hash,
        request_retries=config.max_retries,
        flood_sleep_threshold=60,
    )

    async with client:
        try:
            entity = await with_retries(
                lambda: client.get_entity(normalize_chat(config.chat)),
                max_retries=config.max_retries,
                pause_seconds=config.pause_seconds,
            )
        except (ChannelPrivateError, ChatAdminRequiredError, InviteHashExpiredError, InviteHashInvalidError) as exc:
            raise SystemExit(
                f"Access error: {type(exc).__name__}. Join the chat and verify account permissions."
            ) from exc

        all_rows = await fetch_chat_members(
            client,
            entity,
            limit=config.limit,
            page_size=config.page_size,
            pause_seconds=config.pause_seconds,
            max_retries=config.max_retries,
        )

    export_rows = apply_filter(all_rows, include_all=config.include_all)

    if config.dry_run:
        print_dry_run_summary(all_rows, export_rows)
        return 0

    if config.output_format == "csv":
        save_csv(config.output, export_rows)
    else:
        save_json(config.output, export_rows)

    usernames_count = save_usernames_txt(config.usernames_output, export_rows)
    print(f"Saved {len(export_rows)} records to: {config.output}")
    print(f"Saved {usernames_count} sorted usernames to: {config.usernames_output}")
    return 0


def main() -> int:
    args = parse_args()
    config = load_config(args)

    try:
        return asyncio.run(async_main(config))
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130
    except RPCError as exc:
        print(f"Telegram RPC error: {type(exc).__name__}: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
