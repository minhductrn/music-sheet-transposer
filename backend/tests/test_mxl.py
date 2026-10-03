from io import BytesIO
from pathlib import Path
import stat
import struct
import subprocess
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.api.v1.recognize import get_recognition_service
from app.core.config import Settings
from app.main import app
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.mxl import read_mxl
from app.music.recognition.service import MusicRecognitionService, RecognitionError


MUSICXML = (Path(__file__).parent / 'music/fixtures/simple_score.musicxml').read_bytes()
MIME = 'application/vnd.recordare.musicxml+xml'
MXL_MIME = b'application/vnd.recordare.musicxml'
MANIFEST_PATH = 'META-INF/container.xml'


def manifest(path='score.musicxml', mime=MIME):
    media_type = f' media-type="{mime}"' if mime is not None else ''
    return f'<container><rootfiles><rootfile full-path="{path}"{media_type}/></rootfiles></container>'.encode()


def write_archive(path, entries=None, compression=ZIP_DEFLATED):
    if entries is None:
        entries = [(MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML)]
    with ZipFile(path, 'w', compression=compression) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return path


def decode(path, **kwargs):
    return read_mxl(path, max_bytes=kwargs.get('max_bytes', 100_000),
                    max_members=kwargs.get('max_members', 128))


@pytest.mark.parametrize('compression', [ZIP_DEFLATED, ZIP_STORED])
@pytest.mark.parametrize('namespace', ['', ' xmlns="urn:oasis:names:tc:opendocument:xmlns:container"'])
@pytest.mark.parametrize('mime', [MIME, None])
def test_valid_archives_return_original_xml(tmp_path, compression, namespace, mime):
    contents = manifest('scores/full score.musicxml', mime).replace(b'<container>', f'<container{namespace}>'.encode())
    path = write_archive(tmp_path / 'score.mxl', [
        ('META-INF/', b''), (MANIFEST_PATH, contents),
        ('scores/', b''), ('scores/full score.musicxml', MUSICXML),
    ], compression)
    assert decode(path) == MUSICXML
    assert sorted(p.name for p in tmp_path.iterdir()) == ['score.mxl']


def test_modern_mimetype_supported(tmp_path):
    mimetype = ZipInfo('mimetype')
    mimetype.compress_type = ZIP_STORED
    path = write_archive(tmp_path / 'score.mxl', [
        (mimetype, MXL_MIME), (MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML),
    ])
    assert decode(path) == MUSICXML


def test_first_rootfile_is_primary_with_parts_and_alternate_renditions(tmp_path):
    contents = f'''<container><rootfiles>
    <rootfile full-path="score.musicxml" media-type="{MIME}"/>
    <rootfile full-path="part.musicxml" media-type="{MIME}"/>
    <rootfile full-path="score.pdf" media-type="application/pdf"/>
    </rootfiles></container>'''.encode()
    path = write_archive(tmp_path / 'score.mxl', [
        (MANIFEST_PATH, contents), ('score.musicxml', MUSICXML),
        ('part.musicxml', b'<score-partwise/>'), ('score.pdf', b'PDF alternate'),
    ])
    assert decode(path) == MUSICXML


@pytest.mark.parametrize('contents', [
    b'<broken>', b'<wrong><rootfiles><rootfile full-path="score.musicxml"/></rootfiles></wrong>',
    b'<container/>', b'<container><rootfiles/></container>',
    b'<container><rootfiles/><rootfiles/></container>',
    b'<container><rootfiles><wrong full-path="score.musicxml"/></rootfiles></container>',
    b'<container><rootfiles><rootfile/></rootfiles></container>',
    b'<container><rootfiles><rootfile full-path="score.musicxml"><child/></rootfile></rootfiles></container>',
    b'<container>unexpected<rootfiles><rootfile full-path="score.musicxml"/></rootfiles></container>',
    b'<container><rootfiles>unexpected<rootfile full-path="score.musicxml"/></rootfiles></container>',
    b'<container xmlns="urn:unknown"><rootfiles><rootfile full-path="score.musicxml"/></rootfiles></container>',
    b'<!DOCTYPE container [<!ENTITY path "score.musicxml">]><container><rootfiles><rootfile full-path="&path;"/></rootfiles></container>',
    manifest('missing.musicxml'), manifest('META-INF/container.xml'), manifest('mimetype'),
    manifest('score.musicxml', 'application/pdf'),
    b'<container><rootfiles><rootfile full-path="score.musicxml"/><rootfile full-path="score.musicxml"/></rootfiles></container>',
])
def test_invalid_manifest_rejected(tmp_path, contents):
    path = write_archive(tmp_path / 'score.mxl', [(MANIFEST_PATH, contents), ('score.musicxml', MUSICXML)])
    with pytest.raises(RecognitionError) as error:
        decode(path)
    assert error.value.status_code == 502


@pytest.mark.parametrize('name', [
    '../outside.musicxml', '/absolute.musicxml', 'C:/score.musicxml',
    'folder\\score.musicxml', 'folder/../score.musicxml', './score.musicxml',
    'folder//score.musicxml', 'https://host/score.musicxml', 'bad\nname.musicxml',
])
def test_unsafe_zip_names_rejected_even_for_unused_members(tmp_path, name):
    path = write_archive(tmp_path / 'score.mxl', [
        (MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML), (name, b'unsafe'),
    ])
    with pytest.raises(RecognitionError):
        decode(path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['score.mxl']


@pytest.mark.parametrize('name', ['../score.musicxml', '/score.musicxml', 'folder\\score.musicxml', ''])
def test_unsafe_manifest_reference_rejected(tmp_path, name):
    path = write_archive(tmp_path / 'score.mxl', [(MANIFEST_PATH, manifest(name)), ('score.musicxml', MUSICXML)])
    with pytest.raises(RecognitionError):
        decode(path)


@pytest.mark.parametrize('mode', [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR])
def test_special_zip_entries_rejected(tmp_path, mode):
    entry = ZipInfo('unsafe')
    entry.create_system = 3
    entry.external_attr = (mode | 0o777) << 16
    path = write_archive(tmp_path / 'score.mxl', [
        (MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML), (entry, b'target'),
    ])
    with pytest.raises(RecognitionError):
        decode(path)


def test_duplicate_member_rejected(tmp_path):
    with pytest.warns(UserWarning, match='Duplicate name'):
        path = write_archive(tmp_path / 'score.mxl', [
            (MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML), ('score.musicxml', b'different'),
        ])
    with pytest.raises(RecognitionError):
        decode(path)


def test_conflicting_file_directory_rejected(tmp_path):
    path = write_archive(tmp_path / 'score.mxl', [
        (MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML),
        ('folder', b'file'), ('folder/child', b'child'),
    ])
    with pytest.raises(RecognitionError):
        decode(path)


def test_missing_manifest_rejected(tmp_path):
    path = write_archive(tmp_path / 'score.mxl', [('score.musicxml', MUSICXML)])
    with pytest.raises(RecognitionError):
        decode(path)


@pytest.mark.parametrize('contents', [b'not a ZIP', b'PK\x03\x04truncated', b''])
def test_non_zip_or_truncated_archive_rejected(tmp_path, contents):
    path = tmp_path / 'score.mxl'
    path.write_bytes(contents)
    with pytest.raises(RecognitionError):
        decode(path)


def test_self_extracting_archive_prefix_rejected(tmp_path):
    path = write_archive(tmp_path / 'score.mxl')
    path.write_bytes(b'prefix' + path.read_bytes())
    with pytest.raises(RecognitionError):
        decode(path)


@pytest.mark.parametrize(('data', 'compression', 'extra', 'first'), [
    (b'wrong/type', ZIP_STORED, b'', True),
    (MXL_MIME + b'\n', ZIP_STORED, b'', True),
    (MXL_MIME, ZIP_DEFLATED, b'', True),
    (MXL_MIME, ZIP_STORED, b'\x01\x00\x00\x00', True),
    (MXL_MIME, ZIP_STORED, b'', False),
])
def test_invalid_mimetype_rejected(tmp_path, data, compression, extra, first):
    entry = ZipInfo('mimetype')
    entry.compress_type = compression
    entry.extra = extra
    entries = [(MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML)]
    entries.insert(0 if first else len(entries), (entry, data))
    path = write_archive(tmp_path / 'score.mxl', entries)
    with pytest.raises(RecognitionError):
        decode(path)


def test_unsupported_zip_compression_rejected(tmp_path):
    path = write_archive(tmp_path / 'score.mxl', compression=ZIP_BZIP2)
    with pytest.raises(RecognitionError):
        decode(path)


def test_encrypted_member_flag_rejected(tmp_path):
    path = write_archive(tmp_path / 'score.mxl')
    contents = bytearray(path.read_bytes())
    offset = contents.index(b'PK\x01\x02')
    flags = struct.unpack_from('<H', contents, offset + 8)[0]
    struct.pack_into('<H', contents, offset + 8, flags | 1)
    path.write_bytes(contents)
    with pytest.raises(RecognitionError):
        decode(path)


def corrupt_member(path, name):
    with ZipFile(path) as archive:
        offset = archive.getinfo(name).header_offset
    contents = bytearray(path.read_bytes())
    name_size, extra_size = struct.unpack_from('<HH', contents, offset + 26)
    contents[offset + 30 + name_size + extra_size] ^= 1
    path.write_bytes(contents)


@pytest.mark.parametrize('name', ['score.musicxml', 'attachment.bin'])
def test_corrupt_crc_rejected_in_primary_or_unused_member(tmp_path, name):
    path = write_archive(tmp_path / 'score.mxl', [
        (MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML), ('attachment.bin', b'bytes'),
    ], ZIP_STORED)
    corrupt_member(path, name)
    with pytest.raises(RecognitionError):
        decode(path)


def test_configurable_member_count_limit(tmp_path):
    path = write_archive(tmp_path / 'score.mxl')
    with pytest.raises(RecognitionError):
        decode(path, max_members=1)


def test_combined_uncompressed_size_limit(tmp_path):
    path = write_archive(tmp_path / 'score.mxl', [
        (MANIFEST_PATH, manifest()), ('score.musicxml', MUSICXML), ('attachment.bin', b'x' * 50_000),
    ])
    assert path.stat().st_size < 10_000
    with pytest.raises(RecognitionError):
        decode(path, max_bytes=10_000)


def test_manifest_limit(tmp_path):
    path = write_archive(tmp_path / 'score.mxl', [
        (MANIFEST_PATH, manifest() + b' ' * 70_000), ('score.musicxml', MUSICXML),
    ])
    with pytest.raises(RecognitionError):
        decode(path)


@pytest.mark.parametrize('score', [MUSICXML, b'<broken>', b'<score-partwise/>', b'unsafe-archive'])
def test_mxl_recognition_api_handoff_and_cleanup(monkeypatch, score):
    provider = AudiverisProvider(Settings())
    monkeypatch.setattr(provider, '_check_languages', lambda options: Path('/mock/tessdata'))
    service = MusicRecognitionService(provider, provider.config)
    workspaces = []

    class Process:
        def __init__(self, command, **kwargs):
            output = Path(command[command.index('-output') + 1])
            workspaces.append(output.parent)
            entries = [
                (MANIFEST_PATH, manifest()), ('score.musicxml', score),
            ]
            if score == b'unsafe-archive':
                entries.append(('../outside.musicxml', MUSICXML))
            write_archive(output / 'recognized.mxl', entries)

        def wait(self, timeout):
            return 0

    monkeypatch.setattr(subprocess, 'Popen', Process)
    app.dependency_overrides[get_recognition_service] = lambda: service
    image = BytesIO()
    Image.new('RGB', (20, 20), 'white').save(image, format='PNG')
    try:
        with TestClient(app) as client:
            response = client.post('/api/v1/recognize', files={
                'file': ('score.png', image.getvalue(), 'image/png'),
            })
            if score == MUSICXML:
                assert response.status_code == 200
                assert response.content == MUSICXML
                assert response.headers['content-type'].startswith(MIME)
                transposed = client.post('/api/v1/transpose/musicxml',
                                         files={'file': ('score.musicxml', response.content)},
                                         data={'semitones': '2'})
                assert transposed.status_code == 200
                assert '<fifths>2</fifths>' in transposed.text
            else:
                assert response.status_code == 502
                assert 'detail' in response.json()
    finally:
        app.dependency_overrides.pop(get_recognition_service, None)
    assert workspaces
    assert all(not workspace.exists() for workspace in workspaces)
