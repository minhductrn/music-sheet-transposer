from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import subprocess

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
import pytest

from app.api.v1.recognize import get_recognition_service
from app.core.config import Settings
from app.main import app
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.service import MusicRecognitionService, RecognitionError
from app.music.recognition.profiles import resolve_profile


MUSICXML = (Path(__file__).parent / 'music/fixtures/simple_score.musicxml').read_bytes()


@pytest.fixture(autouse=True)
def mock_ocr_preflight(monkeypatch, tmp_path):
    # Existing subprocess tests never depend on host-installed language models.
    monkeypatch.setattr(AudiverisProvider, '_check_languages', lambda self, options: tmp_path)


def pdf(pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    if encrypted:
        writer.encrypt('secret')
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def image(format='PNG', size=(20, 20)):
    output = BytesIO()
    Image.new('RGB', size, 'white').save(output, format=format)
    return output.getvalue()


class Provider:
    def __init__(self, result=MUSICXML, error=None):
        self.result = result
        self.error = error
        self.source = None
        self.output = None

    def recognize(self, source, output_directory):
        self.source = source
        self.output = output_directory
        assert source.exists()
        assert output_directory.exists()
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def setup():
    provider = Provider()
    config = Settings()
    service = MusicRecognitionService(provider, config)
    app.dependency_overrides[get_recognition_service] = lambda: service
    with TestClient(app) as client:
        yield client, service, provider
    app.dependency_overrides.pop(get_recognition_service, None)


@pytest.mark.parametrize(('name', 'mime', 'contents'), [
    ('score.pdf', 'application/pdf', pdf()),
    ('score.png', 'image/png', image()),
    ('score.jpg', 'image/jpeg', image('JPEG')),
    ('score.jpeg', 'image/jpeg', image('JPEG')),
    ('score.webp', 'image/webp', image('WEBP')),
    ('SCORE.PNG', 'application/octet-stream', image()),
])
def test_supported_upload_returns_musicxml_and_cleans_workspace(setup, name, mime, contents):
    client, _, provider = setup
    response = client.post('/api/v1/recognize', files={'file': (name, contents, mime)})
    assert response.status_code == 200
    assert response.content == MUSICXML
    assert response.headers['content-type'].startswith('application/vnd.recordare.musicxml+xml')
    assert 'recognized.musicxml' in response.headers['content-disposition']
    assert not provider.source.parent.exists()
    # Recognition output is compatible with the unchanged transposition endpoint.
    transposed = client.post('/api/v1/transpose/musicxml',
                             files={'file': ('recognized.musicxml', response.content)},
                             data={'semitones': '2'})
    assert transposed.status_code == 200
    assert '<fifths>2</fifths>' in transposed.text


@pytest.mark.parametrize(('name', 'mime', 'contents', 'status'), [
    ('score.txt', 'text/plain', b'not music', 415),
    ('score.pdf', 'image/png', pdf(), 415),
    ('score.png', 'image/png', image('JPEG'), 415),
    ('score.pdf', 'application/pdf', b'not a PDF', 422),
    ('score.pdf', 'application/pdf', b'%PDF-1.7\nbroken', 422),
    ('score.png', 'image/png', b'broken', 422),
    ('score.pdf', 'application/pdf', pdf(encrypted=True), 422),
    ('score.pdf', 'application/pdf', b'', 422),
])
def test_invalid_upload_does_not_invoke_provider(setup, name, mime, contents, status):
    client, _, provider = setup
    response = client.post('/api/v1/recognize', files={'file': (name, contents, mime)})
    assert response.status_code == status
    assert isinstance(response.json()['detail'], str)
    assert provider.source is None


@pytest.mark.parametrize(('limit', 'value', 'name', 'mime', 'contents', 'status'), [
    ('recognition_max_upload_bytes', 100, 'score.pdf', 'application/pdf', pdf(), 413),
    ('recognition_max_pages', 1, 'score.pdf', 'application/pdf', pdf(2), 422),
    ('recognition_max_image_pixels', 100, 'score.png', 'image/png', image(), 413),
])
def test_configurable_input_limits(setup, limit, value, name, mime, contents, status):
    client, service, provider = setup
    setattr(service.config, limit, value)
    response = client.post('/api/v1/recognize', files={'file': (name, contents, mime)})
    assert response.status_code == status
    assert provider.source is None


@pytest.mark.parametrize('result', [b'<broken>', b'<score-partwise/>', b'<not-music/>', b''])
def test_bad_provider_output_is_rejected_and_cleaned(setup, result):
    client, _, provider = setup
    provider.result = result
    response = client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')})
    assert response.status_code == 502
    assert not provider.source.parent.exists()


def test_provider_failure_cleanup_and_retry(setup):
    client, _, provider = setup
    provider.error = RecognitionError('Recognition failed.', 502)
    response = client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')})
    assert response.status_code == 502
    assert response.json()['detail'] == 'Recognition failed.'
    assert not provider.source.parent.exists()
    provider.error = None
    assert client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')}).status_code == 200


def test_unexpected_provider_failure_is_sanitized(setup):
    client, _, provider = setup
    provider.error = RuntimeError('private provider details')
    response = client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')})
    assert response.status_code == 502
    assert 'private' not in response.text
    assert not provider.source.parent.exists()


def test_animated_image_is_rejected(setup):
    client, _, provider = setup
    output = BytesIO()
    first = Image.new('RGB', (20, 20), 'white')
    first.save(output, format='PNG', save_all=True,
               append_images=[Image.new('RGB', (20, 20), 'black')])
    response = client.post('/api/v1/recognize', files={'file': ('score.png', output.getvalue(), 'image/png')})
    assert response.status_code == 422
    assert provider.source is None


def test_image_normalization_honors_exif_rotation(tmp_path):
    original = Image.new('RGB', (20, 10), 'white')
    metadata = Image.Exif()
    metadata[274] = 6
    contents = BytesIO()
    original.save(contents, format='JPEG', exif=metadata)
    service = MusicRecognitionService(Provider(), Settings())
    source = service._prepare_image(contents.getvalue(), 'JPEG', tmp_path)
    with Image.open(source) as normalized:
        assert normalized.size == (10, 20)


def test_zero_page_pdf_is_rejected(setup):
    client, _, provider = setup
    response = client.post('/api/v1/recognize', files={'file': ('score.pdf', pdf(0), 'application/pdf')})
    assert response.status_code == 422
    assert provider.source is None


def test_busy_provider_returns_503(setup):
    client, service, provider = setup
    service._slot.acquire()
    try:
        response = client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')})
        assert response.status_code == 503
        assert provider.source is None
    finally:
        service._slot.release()


def test_provider_output_limit(setup):
    client, service, provider = setup
    service.config.recognition_max_output_bytes = 10
    response = client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')})
    assert response.status_code == 502
    assert not provider.source.parent.exists()


def test_missing_audiveris_is_reported(setup):
    client, service, _ = setup
    service.provider = AudiverisProvider(Settings(audiveris_executable='/nonexistent/audiveris'))
    response = client.post('/api/v1/recognize', files={'file': ('score.png', image(), 'image/png')})
    assert response.status_code == 503
    assert 'unavailable' in response.json()['detail']


def test_audiveris_command_and_mxl_output(monkeypatch, tmp_path):
    source = tmp_path / 'input.pdf'
    source.write_bytes(pdf())
    output = tmp_path / 'output'
    output.mkdir()
    with ZipFile(output / 'score.mxl', 'w') as archive:
        archive.writestr('META-INF/container.xml', '''<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <rootfiles><rootfile full-path="score.xml" media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>''')
        archive.writestr('score.xml', MUSICXML)

    class Process:
        def __init__(self, command, **kwargs):
            assert command == AudiverisProvider(Settings()).build_command(source, output, resolve_profile(Settings()))
            assert '-save' in command
            assert kwargs['start_new_session'] is True
            assert 'shell' not in kwargs

        def wait(self, timeout):
            assert timeout == 120
            return 0

    monkeypatch.setattr(subprocess, 'Popen', Process)
    assert AudiverisProvider(Settings()).recognize(source, output) == MUSICXML


def test_audiveris_timeout_kills_process_group(monkeypatch, tmp_path):
    import app.music.recognition.audiveris as adapter

    killed = []

    class Process:
        pid = 1234

        def wait(self, timeout=None):
            if timeout:
                raise subprocess.TimeoutExpired('audiveris', timeout)
            return -9

    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: Process())
    monkeypatch.setattr(adapter.os, 'killpg', lambda pid, signal: killed.append(pid))
    with pytest.raises(RecognitionError) as error:
        AudiverisProvider(Settings()).recognize(tmp_path / 'input.pdf', tmp_path)
    assert error.value.status_code == 504
    assert killed == [1234]


@pytest.mark.parametrize('code', [0, 1])
def test_audiveris_failure_or_missing_export(monkeypatch, tmp_path, code):
    class Process:
        def wait(self, timeout):
            return code
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: Process())
    with pytest.raises(RecognitionError) as error:
        AudiverisProvider(Settings()).recognize(tmp_path / 'input.pdf', tmp_path)
    assert error.value.status_code == 502


def test_mxl_member_limit(tmp_path):
    path = tmp_path / 'score.mxl'
    from zipfile import ZIP_DEFLATED
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as archive:
        archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="score.xml"/></rootfiles></container>')
        archive.writestr('score.xml', b'x' * 2000)
    with pytest.raises(RecognitionError):
        AudiverisProvider(Settings(recognition_max_output_bytes=1000))._read_score(path)


def test_mxl_manifest_entities_are_rejected_even_in_utf16(tmp_path):
    path = tmp_path / 'score.mxl'
    with ZipFile(path, 'w') as archive:
        archive.writestr('META-INF/container.xml',
                        ('<?xml version="1.0" encoding="UTF-16"?>'
                         '<!DOCTYPE container [<!ENTITY name "score.xml">]>'
                         '<container><rootfiles><rootfile full-path="&name;"/>'
                         '</rootfiles></container>').encode('utf-16'))
    with pytest.raises(RecognitionError):
        AudiverisProvider(Settings())._read_score(path)
