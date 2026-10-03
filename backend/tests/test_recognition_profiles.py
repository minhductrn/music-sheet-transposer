from pathlib import Path
import subprocess

import pytest

from app.core.config import Settings
from app.music.recognition.audiveris import AudiverisProvider
from app.music.recognition.errors import RecognitionError
from app.music.recognition.profiles import InputQuality, RecognitionProfile, resolve_profile


@pytest.mark.parametrize(('name', 'languages', 'lyrics', 'chords'), [
    ('VOCAL_SONG', 'vie+eng', True, True), ('SATB', 'vie+eng', True, False),
    ('PIANO', 'eng', False, False), ('GENERAL', 'eng', True, True),
    ('ORCHESTRAL', 'eng', False, False),
])
def test_profile_selection(name, languages, lyrics, chords):
    options = resolve_profile(Settings(), RecognitionProfile(name))
    assert options.profile.value == name
    assert (options.ocr_languages, options.lyrics, options.chord_names) == (languages, lyrics, chords)
    constants = options.constants()
    assert constants['org.audiveris.omr.sheet.ProcessingSwitches.smallHeads'] == 'false'
    assert constants['org.audiveris.omr.sheet.ProcessingSwitches.smallBeams'] == 'false'


def test_vocal_default_is_conservative_and_configurable():
    options = resolve_profile(Settings())
    assert options.profile == RecognitionProfile.VOCAL_SONG
    assert options.input_quality == InputQuality.SYNTHETIC
    assert not options.fingerings and not options.tremolos
    constants = options.constants()
    for key in ('crossHeads', 'frets', 'pluckings', 'drumNotation'):
        assert constants[f'org.audiveris.omr.sheet.ProcessingSwitches.{key}'] == 'false'
    override = resolve_profile(Settings(audiveris_ocr_languages='vie+eng+fra', audiveris_input_quality='Standard'))
    assert override.ocr_languages == 'vie+eng+fra'
    assert override.input_quality == InputQuality.STANDARD
    assert resolve_profile(Settings(audiveris_input_quality='Poor'), input_quality=InputQuality.STANDARD).input_quality == InputQuality.STANDARD


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv('AUDIVERIS_EXECUTABLE', '/opt/audiveris/bin/Audiveris')
    monkeypatch.setenv('AUDIVERIS_OCR_LANGUAGES', 'vie+eng')
    monkeypatch.setenv('RECOGNITION_DEFAULT_PROFILE', 'SATB')
    config = Settings()
    assert config.audiveris_executable == '/opt/audiveris/bin/Audiveris'
    assert resolve_profile(config).profile == RecognitionProfile.SATB
    assert resolve_profile(config).ocr_languages == 'vie+eng'


@pytest.mark.parametrize('languages', ['vie; rm -rf /', '', 'vie eng', '../eng', 'vie+'])
def test_invalid_language_configuration_rejected(languages):
    with pytest.raises(ValueError):
        Settings(audiveris_ocr_languages=languages)


def test_command_uses_verified_constants_and_single_executable(tmp_path):
    config = Settings(audiveris_executable='/opt/audiveris/bin/Audiveris')
    options = resolve_profile(config)
    command = AudiverisProvider(config).build_command(tmp_path / 'input.pdf', tmp_path / 'output', options)
    assert command[:5] == ['/opt/audiveris/bin/Audiveris', '-batch', '-transcribe', '-export', '-save']
    assert command[-4:] == ['-output', str(tmp_path / 'output'), '--', str(tmp_path / 'input.pdf')]
    pairs = [command[index + 1] for index, value in enumerate(command) if value == '-constant']
    assert 'org.audiveris.omr.sheet.Profiles.defaultQuality=Synthetic' in pairs
    assert 'org.audiveris.omr.text.Language.defaultSpecification=vie+eng' in pairs
    assert 'org.audiveris.omr.sheet.ProcessingSwitches.lyrics=true' in pairs
    assert 'org.audiveris.omr.sheet.ProcessingSwitches.chordNames=true' in pairs
    assert 'org.audiveris.omr.sheet.ProcessingSwitches.smallHeads=false' in pairs
    assert 'org.audiveris.omr.sheet.ProcessingSwitches.smallBeams=false' in pairs
    assert 'org.audiveris.omr.sheet.ProcessingSwitches.keepGrayImages=true' in pairs


@pytest.mark.parametrize(('available', 'missing'), [
    ([], ['vie', 'eng']), (['eng'], ['vie']), (['vie'], ['eng']),
])
def test_missing_languages_stop_recognition_before_subprocess(monkeypatch, tmp_path, available, missing):
    for language in available:
        (tmp_path / f'{language}.traineddata').write_bytes(b'model-placeholder')
    provider = AudiverisProvider(Settings(audiveris_tessdata_path=tmp_path))
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('OMR must not start'))
    with pytest.raises(RecognitionError) as exc:
        provider.recognize_result(tmp_path / 'input.pdf', tmp_path, resolve_profile(provider.config))
    assert exc.value.status_code == 503
    assert exc.value.diagnostics[0].code == 'missing_ocr_languages'
    assert exc.value.diagnostics[0].details['missing_languages'] == missing
    assert str(tmp_path) not in str(exc.value)


def test_empty_language_file_is_missing(tmp_path):
    (tmp_path / 'vie.traineddata').write_bytes(b'')
    (tmp_path / 'eng.traineddata').write_bytes(b'model')
    provider = AudiverisProvider(Settings(audiveris_tessdata_path=tmp_path))
    with pytest.raises(RecognitionError) as exc:
        provider._check_languages(resolve_profile(provider.config))
    assert exc.value.diagnostics[0].details['missing_languages'] == ['vie']


def test_model_directory_is_shared_with_audiveris_environment(monkeypatch, tmp_path):
    for language in ('vie', 'eng'):
        (tmp_path / f'{language}.traineddata').write_bytes(b'model')
    monkeypatch.setenv('TESSDATA_PREFIX', str(tmp_path))
    provider = AudiverisProvider(Settings())
    assert provider._check_languages(resolve_profile(provider.config)) == tmp_path.resolve()


def test_explicit_directory_overrides_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('TESSDATA_PREFIX', '/nonexistent/data')
    for language in ('vie', 'eng'):
        (tmp_path / f'{language}.traineddata').write_bytes(b'model')
    provider = AudiverisProvider(Settings(audiveris_tessdata_path=tmp_path))
    assert provider._check_languages(resolve_profile(provider.config)) == tmp_path.resolve()


def test_default_audiveris_xdg_model_directory(monkeypatch, tmp_path):
    monkeypatch.delenv('TESSDATA_PREFIX', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    directory = tmp_path / 'AudiverisLtd/audiveris/tessdata'
    directory.mkdir(parents=True)
    for language in ('vie', 'eng'):
        (directory / f'{language}.traineddata').write_bytes(b'model')
    provider = AudiverisProvider(Settings())
    assert provider._check_languages(resolve_profile(provider.config)) == directory


@pytest.mark.parametrize('message', [
    'No language is available', 'Could not initialize TessBaseAPI',
    'Failed loading language vie', 'Error opening data file /private/model',
    "Missing support for 'vie' language(s)", 'The collection of supported languages is empty',
])
def test_native_ocr_initialization_failure_is_structured_and_sanitized(tmp_path, message):
    (tmp_path / 'input.log').write_text(message)
    with pytest.raises(RecognitionError) as exc:
        AudiverisProvider(Settings())._log_diagnostics(tmp_path)
    assert exc.value.status_code == 503
    assert exc.value.diagnostics[0].code == 'ocr_initialization_failed'
    assert '/private' not in str(exc.value)


def test_severe_provider_warnings_and_bounded_log_inspection(tmp_path):
    (tmp_path / 'input.log').write_text('private path /tmp/score.pdf\n WARN problem\nMeasure#16 no correct rhythm')
    issues = AudiverisProvider(Settings())._log_diagnostics(tmp_path)
    assert {issue.code for issue in issues} == {'provider_warning', 'provider_rhythm_warning'}
    assert all('/tmp/score.pdf' not in issue.message for issue in issues)
    limited = AudiverisProvider(Settings(recognition_max_log_bytes=20))._log_diagnostics(tmp_path)
    assert 'provider_logs_truncated' in {issue.code for issue in limited}


def test_runtime_logs_are_checked_for_ocr_failure(tmp_path):
    output = tmp_path / 'output'
    output.mkdir()
    runtime = tmp_path / 'runtime/cache/AudiverisLtd/audiveris/log'
    runtime.mkdir(parents=True)
    (runtime / 'engine.log').write_text("Missing support for 'vie' language(s)")
    with pytest.raises(RecognitionError) as exc:
        AudiverisProvider(Settings())._log_diagnostics(output, tmp_path / 'runtime')
    assert exc.value.diagnostics[0].code == 'ocr_initialization_failed'


def test_unavailable_logs_report_uncertainty(tmp_path):
    issues = AudiverisProvider(Settings())._log_diagnostics(tmp_path)
    assert issues[0].code == 'provider_logs_unavailable'


def test_provider_error_is_reported_without_raw_log_text(tmp_path):
    (tmp_path / 'engine.log').write_text('ERROR failed to read /private/score.pdf')
    issues = AudiverisProvider(Settings())._log_diagnostics(tmp_path)
    assert issues[0].code == 'provider_error'
    assert issues[0].severity == 'error'
    assert '/private' not in issues[0].message
