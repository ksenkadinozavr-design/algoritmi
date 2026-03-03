from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from .downloader import download_archive
from .matcher import SearchError, find_best_match
from .parser import ParseError, parse_song_file


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "dev-secret-change-me"

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/process")
    def process_file():
        uploaded = request.files.get("songs_file")
        if not uploaded or not uploaded.filename:
            flash("Загрузите .txt файл со списком песен", "error")
            return redirect(url_for("index"))

        raw_content = uploaded.read().decode("utf-8", errors="strict")

        try:
            songs = parse_song_file(raw_content)
        except ParseError as exc:
            flash(f"Ошибка формата: {exc}", "error")
            return redirect(url_for("index"))
        except UnicodeDecodeError:
            flash("Файл должен быть в UTF-8", "error")
            return redirect(url_for("index"))

        matches = []
        unresolved = []
        for song in songs:
            try:
                match = find_best_match(song)
            except SearchError as exc:
                flash(str(exc), "error")
                return redirect(url_for("index"))

            matches.append(match)
            if not match.url:
                unresolved.append(match)

        if unresolved:
            unresolved_text = "\n".join(
                f"- [{m.request.group}] {m.request.artist} - {m.request.title} (score={m.score})"
                for m in unresolved
            )
            flash(
                "Не удалось строго сопоставить все треки. Скачивание остановлено:\n"
                + unresolved_text,
                "error",
            )
            return redirect(url_for("index"))

        archive_path = download_archive(matches)
        return send_file(
            archive_path,
            as_attachment=True,
            download_name="songs_archive.zip",
            mimetype="application/zip",
        )

    return app
