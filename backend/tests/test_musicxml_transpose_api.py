from pathlib import Path
import xml.etree.ElementTree as ET

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


def test_musicxml_endpoint_preserves_notation() -> None:
    contents = b'''<score-partwise><part id="P1"><measure number="1">
      <direction><direction-type><words>Keep me</words></direction-type></direction>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration>
      <dot/><notations><articulations><accent/></articulations></notations>
      <lyric><text>Keep me too</text></lyric></note></measure></part></score-partwise>'''
    response = client.post('/api/v1/transpose/musicxml',
                           files={'file': ('score.musicxml', contents)},
                           data={'semitones': '1'})
    assert response.status_code == 200
    root = ET.fromstring(response.content)
    assert root.findtext('.//pitch/step') == 'C'
    assert root.findtext('.//pitch/octave') == '5'
    assert root.find('.//dot') is not None
    assert root.find('.//notations/articulations/accent') is not None
    assert root.findtext('.//direction/direction-type/words') == 'Keep me'
    assert root.findtext('.//lyric/text') == 'Keep me too'


def test_musicxml_endpoint_zero_is_byte_preserving() -> None:
    contents = FIXTURE.read_bytes()
    response = client.post('/api/v1/transpose/musicxml',
                           files={'file': ('score.musicxml', contents)},
                           data={'semitones': '0'})
    assert response.status_code == 200
    assert response.content == contents


def test_musicxml_endpoint_rejects_invalid_xml() -> None:
    response = client.post('/api/v1/transpose/musicxml',
                           files={'file': ('score.musicxml', b'<broken>')},
                           data={'semitones': '2'})
    assert response.status_code == 422
    assert 'detail' in response.json()
