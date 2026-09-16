from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

FIXTURE = (
    Path(__file__).parent
    / "music"
    / "fixtures"
    / "simple_score.musicxml"
)


def test_transpose_musicxml_endpoint() -> None:
    with FIXTURE.open("rb") as musicxml_file:
        response = client.post(
            "/api/v1/transpose/musicxml",
            files={
                "file": (
                    "simple_score.musicxml",
                    musicxml_file,
                    "application/vnd.recordare.musicxml+xml",
                )
            },
            data={
                "semitones": "2",
            },
        )

    assert response.status_code == 200

    assert response.headers["content-type"].startswith(
        "application/vnd.recordare.musicxml+xml"
    )

    assert (
        'filename="transposed.musicxml"'
        in response.headers["content-disposition"]
    )

    xml = response.text

    assert "<fifths>2</fifths>" in xml
    assert "<step>D</step>" in xml
    assert "<octave>4</octave>" in xml
    