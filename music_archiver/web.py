from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from song_archiver.downloader import DownloadError
from song_archiver.orchestrator import process_playlist_file
from song_archiver.parser import ParseError
from main import _build_proxy_url


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "song-archiver-dev-key"
    app.config["ARCHIVE_ROOT"] = Path("web_downloads")

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.post("/build")
    def build_archive():
        songs_text = request.form.get("songs_text", "").strip()
        min_score_raw = request.form.get("min_score", "0.78").strip()
        archive_name = request.form.get("archive_name", "songs_archive").strip() or "songs_archive"
        proxy = request.form.get("proxy", "").strip()
        proxy_user = request.form.get("proxy_user", "").strip()
        proxy_password = request.form.get("proxy_password", "").strip()

        if not songs_text:
            flash("Добавьте список песен в поле текста.", "error")
            return redirect(url_for("index"))

        try:
            min_score = float(min_score_raw)
        except ValueError:
            flash("Min score должен быть числом от 0 до 1.", "error")
            return redirect(url_for("index"))

        if not 0 <= min_score <= 1:
            flash("Min score должен быть в диапазоне 0..1.", "error")
            return redirect(url_for("index"))

        app.config["ARCHIVE_ROOT"].mkdir(parents=True, exist_ok=True)

        try:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
                tmp.write(songs_text)
                input_file = Path(tmp.name)

            archive_path = process_playlist_file(
                input_file=input_file,
                workdir=app.config["ARCHIVE_ROOT"],
                archive_name=archive_name,
                min_score=min_score,
                proxy_url=_build_proxy_url(proxy, proxy_user, proxy_password),
            )
        except (ParseError, DownloadError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        finally:
            if "input_file" in locals() and input_file.exists():
                input_file.unlink()

        return send_file(archive_path, as_attachment=True)

    return app


app = create_app()
