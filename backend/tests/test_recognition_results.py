from base64 import b64decode
from io import BytesIO
from pathlib import Path
import subprocess
from zipfile import ZipFile

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.api.v1.recognize import get_recognition_service
from app.core.config import Settings
from app.main import app
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.errors import RecognitionError
from app.music.recognition.profiles import InputQuality, RecognitionProfile
from app.music.recognition.result import ProviderOutput, RecognitionIssue
from app.music.recognition.service import MusicRecognitionService


MUSICXML = (Path(__file__).parent / 'music/fixtures/simple_score.musicxml').read_bytes()


def image():
    stream = BytesIO()
    Image.new('RGB', (20, 20), 'white').save(stream, format='PNG')
    return stream.getvalue()


def omr():
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        archive.writestr('book.xml', '<book software-version="5.11.0"/>')
    return stream.getvalue()


class ResultProvider:
    def __init__(self):
        self.options = None
        self.workspace = None
        self.result = ProviderOutput(MUSICXML, 'Audiveris', omr(), metadata={'ocr_languages': 'vie+eng'})

    def recognize_result(self, source, output_directory, options):
        self.options = options
        self.workspace = source.parent
        return self.result


@pytest.fixture
def setup_result():
    provider = ResultProvider()
    service = MusicRecognitionService(provider, Settings())
    app.dependency_overrides[get_recognition_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, service, provider
    finally:
        app.dependency_overrides.pop(get_recognition_service, None)


def recognize(client, **data):
    return client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')},
                       data={'response_format': 'json', **data})


def test_json_response_retains_exact_musicxml_and_downloadable_omr(setup_result):
    client, _, provider = setup_result
    response = recognize(client)
    assert response.status_code == 200
    result = response.json()
    assert b64decode(result['musicxml_base64']) == MUSICXML
    assert result['profile'] == 'VOCAL_SONG'
    assert result['provider'] == 'Audiveris'
    assert result['review_required'] is True
    assert result['diagnostics']['counts']['pitched_notes'] > 0
    assert result['diagnostics']['artifact_retained'] is True
    assert result['diagnostics']['provider_metadata']['ocr_languages'] == 'vie+eng'
    assert b64decode(result['omr_artifact']['data_base64']) == provider.result.omr
    assert result['omr_artifact']['filename'] == 'recognized.omr'
    assert len(result['omr_artifact']['sha256']) == 64
    assert result['omr_artifact']['size_bytes'] == len(provider.result.omr)
    assert str(provider.workspace) not in response.text
    assert not provider.workspace.exists()
    assert response.headers['cache-control'] == 'no-store'


def test_legacy_response_still_returns_original_musicxml_with_metadata_headers(setup_result):
    client, _, provider = setup_result
    response = client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')})
    assert response.content == MUSICXML
    assert response.headers['x-recognition-provider'] == 'Audiveris'
    assert response.headers['x-recognition-profile'] == 'VOCAL_SONG'
    assert response.headers['x-recognition-review-required'] == 'true'
    assert not provider.workspace.exists()


@pytest.mark.parametrize('profile', list(RecognitionProfile))
def test_profile_and_quality_reach_provider(setup_result, profile):
    client, _, provider = setup_result
    response = recognize(client, profile=profile.value, input_quality='Standard')
    assert response.status_code == 200
    assert response.json()['profile'] == profile.value
    assert provider.options.profile == profile
    assert provider.options.input_quality == InputQuality.STANDARD


@pytest.mark.parametrize('data', [{'profile': 'UNKNOWN'}, {'input_quality': 'automatic'}, {'response_format': 'html'}])
def test_invalid_form_options_do_not_invoke_provider(setup_result, data):
    client, _, provider = setup_result
    assert recognize(client, **data).status_code == 422
    assert provider.workspace is None


def test_severe_provider_warning_is_exposed_and_requires_review(setup_result):
    client, _, provider = setup_result
    provider.result = ProviderOutput(MUSICXML, 'Audiveris', warnings=(
        RecognitionIssue('provider_rhythm_warning', 'Unresolved rhythm.', 'error'),
    ))
    response = recognize(client)
    assert response.status_code == 200
    assert response.json()['review_required'] is True
    assert response.json()['warnings'][0]['code'] == 'provider_rhythm_warning'


def test_clean_structural_checks_still_require_source_comparison(setup_result):
    client, _, provider = setup_result
    xml = (b'<score-partwise><part id="P1"><measure number="1"><attributes>'
           b'<divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>'
           b'<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration>'
           b'<lyric><text>Chung</text></lyric></note></measure></part></score-partwise>')
    provider.result = ProviderOutput(xml, 'Audiveris')
    result = recognize(client).json()
    assert result['warnings'] == []
    assert result['review_required'] is True


@pytest.mark.parametrize('xml', [b'<broken>', b'<score-partwise/>',
    b'<score-partwise><part><measure/></part></score-partwise>'])
def test_invalid_output_has_structured_diagnostics_and_cleanup(setup_result, xml):
    client, _, provider = setup_result
    provider.result = ProviderOutput(xml, 'Audiveris', omr())
    response = recognize(client)
    assert response.status_code == 502
    assert response.json()['diagnostics'][0]['code'] == 'invalid_musicxml'
    assert not provider.workspace.exists()


def test_missing_vietnamese_is_structured_at_api_boundary(setup_result, tmp_path):
    client, service, _ = setup_result
    (tmp_path / 'eng.traineddata').write_bytes(b'model')
    service.provider = AudiverisProvider(Settings(audiveris_tessdata_path=tmp_path))
    response = recognize(client)
    assert response.status_code == 503
    assert response.json()['diagnostics'][0]['details']['missing_languages'] == ['vie']
    assert str(tmp_path) not in response.text


def test_json_musicxml_handoff_uses_unchanged_transposition_endpoint(setup_result):
    client, _, _ = setup_result
    result = recognize(client).json()
    xml = b64decode(result['musicxml_base64'])
    for semitones in (0, 2):
        response = client.post('/api/v1/transpose/musicxml', files={'file': ('score.musicxml', xml)},
                               data={'semitones': str(semitones)})
        assert response.status_code == 200
        if semitones == 0:
            assert response.content == MUSICXML
        else:
            assert '<fifths>2</fifths>' in response.text


def test_real_adapter_contract_preserves_artifact_and_isolates_engine_state(monkeypatch, tmp_path):
    provider = AudiverisProvider(Settings())
    monkeypatch.setattr(provider, '_check_languages', lambda options: tmp_path)
    workspaces = []
    artifact_bytes = omr()

    class Process:
        def __init__(self, command, **kwargs):
            output = Path(command[command.index('-output') + 1])
            workspaces.append(output.parent)
            (output / 'input.musicxml').write_bytes(MUSICXML)
            (output / 'input.omr').write_bytes(artifact_bytes)
            (output / 'input.log').write_text('WARN /private/input.pdf: unresolved rhythm\nno correct rhythm')
            assert kwargs['env']['TESSDATA_PREFIX'] == str(tmp_path)
            for kind in ('CONFIG', 'DATA', 'CACHE'):
                assert Path(kwargs['env'][f'XDG_{kind}_HOME']).is_relative_to(output.parent)
            assert kwargs['start_new_session'] is True
            assert 'shell' not in kwargs

        def wait(self, timeout):
            return 0

    monkeypatch.setattr(subprocess, 'Popen', Process)
    result = MusicRecognitionService(provider, provider.config).recognize_result(image(), 'score.png', 'image/png')
    assert result.musicxml == MUSICXML
    assert result.omr == artifact_bytes
    assert result.review_required
    assert 'provider_rhythm_warning' in {issue.code for issue in result.warnings}
    assert all('/private' not in issue.message for issue in result.warnings)
    assert all(not path.exists() for path in workspaces)


@pytest.mark.parametrize('artifact', ['missing', 'oversized', 'multiple', 'symlink'])
def test_artifact_limits_and_safe_cleanup(monkeypatch, tmp_path, artifact):
    provider = AudiverisProvider(Settings(recognition_max_artifact_bytes=1000))
    monkeypatch.setattr(provider, '_check_languages', lambda options: tmp_path)
    workspaces = []
    external = tmp_path / 'outside.omr'
    artifact_bytes = omr()
    external.write_bytes(artifact_bytes)

    class Process:
        def __init__(self, command, **kwargs):
            output = Path(command[command.index('-output') + 1])
            workspaces.append(output.parent)
            (output / 'input.musicxml').write_bytes(MUSICXML)
            if artifact == 'oversized':
                (output / 'input.omr').write_bytes(b'x' * 1001)
            elif artifact == 'multiple':
                (output / 'first.omr').write_bytes(artifact_bytes)
                (output / 'second.omr').write_bytes(artifact_bytes)
            elif artifact == 'symlink':
                (output / 'input.omr').symlink_to(external)

        def wait(self, timeout):
            return 0

    monkeypatch.setattr(subprocess, 'Popen', Process)
    service = MusicRecognitionService(provider, provider.config)
    if artifact == 'symlink':
        with pytest.raises(RecognitionError):
            service.recognize_result(image(), 'score.png', 'image/png')
    else:
        result = service.recognize_result(image(), 'score.png', 'image/png')
        assert result.omr is None
        assert any(issue.code.startswith('omr_artifact_') for issue in result.warnings)
    assert external.read_bytes() == artifact_bytes
    assert all(not path.exists() for path in workspaces)
