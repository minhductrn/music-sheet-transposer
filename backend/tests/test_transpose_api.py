from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_transpose_endpoint() -> None:
    response = client.post(
        "/api/v1/transpose",
        json={
            "score": {
                "title": "API Transposition Test",
                "parts": [
                    {
                        "id": "P1",
                        "name": "Piano",
                        "measures": [
                            {
                                "number": 1,
                                "key_signature": {
                                    "fifths": 0,
                                    "mode": "major",
                                },
                                "notes": [
                                    {
                                        "pitch": {
                                            "step": "C",
                                            "octave": 4,
                                            "alter": 0.0,
                                        },
                                        "duration": 1,
                                        "note_type": "quarter",
                                        "is_rest": False,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            "semitones": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()
    measure = data["score"]["parts"][0]["measures"][0]

    assert measure["key_signature"]["fifths"] == 2

    pitch = measure["notes"][0]["pitch"]

    assert pitch["step"] == "D"
    assert pitch["octave"] == 4
    assert pitch["alter"] == 0.0


def test_transpose_endpoint_rejects_invalid_request() -> None:
    response = client.post(
        "/api/v1/transpose",
        json={
            "score": {
                "title": "Invalid Test",
                "parts": [],
            }
        },
    )

    assert response.status_code == 422