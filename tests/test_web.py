import pytest

flask = pytest.importorskip("flask")

from music_archiver.web import create_app


def test_index_page_renders() -> None:
    app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert "Song Archiver" in response.get_data(as_text=True)
