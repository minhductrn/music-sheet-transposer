# Phase 4C: Audiveris recognition and review

PDF/image → validated upload → recognition profile → Audiveris subprocess →
retain bounded OMR artifact + decode MusicXML → structural/timing validation →
OSMD preview and review → existing preservation-based transposition.

Audiveris remains the only production OMR provider. Java/native dependencies stay
outside Python. No paid service, automatic language download, or guessed musical
repair is part of this workflow. The preservation transposer, internal music models,
parser/exporter, JSON transpose API, and MusicXML transpose API are unchanged.

## Install Audiveris outside the virtual environment

For WSL Ubuntu x86_64, use the official Linux Ubuntu x86_64 `.deb` from the
[Audiveris 5.11.0 release](https://github.com/Audiveris/audiveris/releases/tag/5.11.0).
Follow the [official binary installation guide](https://audiveris.github.io/audiveris/_pages/tutorials/install/binaries/).
Download the appropriate Ubuntu variant to a user downloads directory, verify it
against the release information, and install that local package with:

```bash
sudo apt install ./Audiveris-5.11.0-ubuntu24.04-x86_64.deb
/opt/audiveris/bin/Audiveris -version
```

The official installer includes its own JRE. A source build of 5.11.0 needs Java 25;
the existing inspected WSL system Java 25 is compatible. The observed Ubuntu 26.04
installation already launches Audiveris 5.11.0, but native library compatibility
must still be verified on every target machine. Do not downgrade Python or install
Audiveris in `backend/.venv`. Do not reinstall a working Audiveris unnecessarily.

```bash
export AUDIVERIS_EXECUTABLE=/opt/audiveris/bin/Audiveris
```

This setting is a single executable path, not a shell command with arguments.
Application logic defaults to `audiveris` and contains no machine-specific launcher
path. The adapter is intended for Linux/WSL with POSIX process-group termination.

## Vietnamese OCR

`VOCAL_SONG` and `SATB` default to **vie+eng**. Other profiles default to `eng`.
Install language data explicitly; the backend never downloads models. On Ubuntu:

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
export AUDIVERIS_TESSDATA_PATH=/usr/share/tesseract-ocr/5/tessdata
export TESSDATA_PREFIX="$AUDIVERIS_TESSDATA_PATH"
export AUDIVERIS_OCR_LANGUAGES=vie+eng

test -s "$AUDIVERIS_TESSDATA_PATH/vie.traineddata"
test -s "$AUDIVERIS_TESSDATA_PATH/eng.traineddata"
tesseract --tessdata-dir "$AUDIVERIS_TESSDATA_PATH" --list-langs
```

The distro model directory can differ; use the actual directory reported by the
installed package. Models must be compatible with Audiveris's bundled Tesseract.
See [Tesseract installation](https://tesseract-ocr.github.io/tessdoc/Installation.html).
For controlled deployment, pin the installed model versions separately.

Resolution order is `AUDIVERIS_TESSDATA_PATH`, inherited `TESSDATA_PREFIX`, then
Audiveris's Linux default `${XDG_CONFIG_HOME:-$HOME/.config}/AudiverisLtd/audiveris/tessdata`.
The adapter checks readable, nonempty files for every requested language on each
recognition, then passes that exact absolute directory as the subprocess's
`TESSDATA_PREFIX`. Missing data returns HTTP 503 with `missing_ocr_languages` and
`missing_languages` diagnostics before OMR starts. File presence cannot prove model
integrity; native initialization failures in available logs also return an explicit
OCR error. The system Tesseract CLI is a deployment smoke test, not a backend dependency.
[Audiveris 5.11.0 directory resolution](https://github.com/Audiveris/audiveris/blob/5.11.0/app/src/main/java/org/audiveris/omr/text/tesseract/TesseractOCR.java).

## Recognition profiles

| Profile | Default input quality | OCR | Lyrics | Chord names | Additional recognition |
|---|---|---|---|---|---|
| VOCAL_SONG (default) | Synthetic | vie+eng | On | On | Conservative uncommon symbols |
| SATB | Standard | vie+eng | On | Off | Conservative uncommon symbols |
| PIANO | Standard | eng | Off | Off | Fingerings |
| GENERAL | Standard | eng | On | On | Conservative uncommon symbols |
| ORCHESTRAL | Standard | eng | Off | Off | Tremolos |

Presets configure one shared provider. All explicitly disable `smallHeads` and
`smallBeams`. Gray images are retained in OMR projects for future correction work.
`Synthetic` is suitable for clean digital scores; it is not automatic PDF-quality
detection. Choose `Standard` for scanned PDFs/photos and `Poor` for poor scans using
the UI/API source-quality override. Request quality overrides server quality,
which overrides the profile default. OCR languages can be overridden globally by
`AUDIVERIS_OCR_LANGUAGES`; codes are a validated `+`-separated language specification.

The adapter uses verified 5.11.0 constants:

```text
org.audiveris.omr.sheet.Profiles.defaultQuality=Synthetic
org.audiveris.omr.text.Language.defaultSpecification=vie+eng
org.audiveris.omr.sheet.ProcessingSwitches.lyrics=true
org.audiveris.omr.sheet.ProcessingSwitches.chordNames=true
org.audiveris.omr.sheet.ProcessingSwitches.smallHeads=false
org.audiveris.omr.sheet.ProcessingSwitches.smallBeams=false
```

It invokes one argument-list subprocess with `-batch -transcribe -export -save`,
profile `-constant` arguments, `-output <workspace/output> -- <workspace/input>`.
No shell is used. Audiveris's XDG config/data/cache directories are isolated inside
the workspace, so personal persisted switches cannot silently override the preset
or leave application-created caches outside it. The external OCR models are read
through the explicitly resolved directory.

## Result contract, API compatibility, and artifacts

`MusicRecognitionService.recognize_result(...)` returns `RecognitionResult`:
original uncompressed MusicXML bytes, provider, profile, structured warnings,
diagnostics, `review_required`, and optional OMR bytes. The previous `.recognize(...)`
bytes-only interface and bytes-only test/custom providers remain supported.

`POST /api/v1/recognize` accepts multipart:

- `file`: PDF, PNG, JPG/JPEG, WEBP.
- `profile`: VOCAL_SONG / SATB / PIANO / GENERAL / ORCHESTRAL (server default if omitted).
- `input_quality`: Synthetic / Standard / Poor (optional).
- `response_format`: `musicxml` (default) or `json`.

The default still returns original MusicXML with its previous content type and
attachment filename. Provider/profile/review state is available in
`X-Recognition-Provider`, `X-Recognition-Profile`, `X-Recognition-Review-Required`.
JSON mode supplies `musicxml_base64` (exact bytes), `provider`, `profile`,
`review_required`, `warnings`, `diagnostics`, and nullable `omr_artifact`.
The artifact has a fixed download filename, size, SHA-256, media type, and
`data_base64`; it is not a filesystem path or an arbitrary file-download endpoint.
Errors retain a string `detail` for existing clients and add structured `diagnostics`.
Responses use `Cache-Control: no-store`.

The frontend requests JSON, shows Recognized Sheet Music, provider/profile/review
status and diagnostic messages, retains OSMD, and offers MusicXML/OMR downloads.
Transposition submits the recognized MusicXML bytes to the existing endpoint.

An `.omr` is Audiveris's editable project with images and recognition interpretations;
MusicXML is the exported musical document and can omit interpretations. One bounded
OMR project is read into memory before workspace cleanup. Missing/multiple/oversized
projects generate a warning; unsafe output paths fail recognition. Artifacts are
available only in the current response/browser session unless downloaded. There is
no permanent server artifact store, public directory, correction endpoint, or automatic
reprocessing. Downloaded OMR is opaque provider data and may contain its original
temporary input reference; source PDFs should also be retained for future full reruns.

Temporary upload/output/runtime workspaces are removed after success or failure.
A timeout kills the launcher/JVM process group before cleanup. One recognition runs
per backend worker; a concurrent request receives 503. Raw provider logs and server
paths are not included in diagnostic messages. Only bounded log tails are inspected;
missing/truncated logs explicitly report uncertainty.

## MXL stays inside the provider boundary

One XML/MusicXML/MXL score export is accepted. Multiple exports are rejected.
MXL decoding retains the existing safety checks: ZIP integrity/CRC, safe relative
paths, duplicate names, file types, encryption/compression, member count, combined
uncompressed size, and `META-INF/container.xml` rootfile references. Members are
read in memory, never extracted to filesystem paths. Legacy MXL without `mimetype`
is accepted; when present its prescribed placement/type/content are checked.
The recognition service and transposition endpoint receive ordinary XML regardless
of the engine's original format.

## Validation and review

Validation never rewrites musical content. It rejects malformed/entity-bearing XML,
wrong score roots, missing parts/measures, invalid pitch representations, and wholly
note-free output. It counts pitches/rests/unpitched notes, chords, grace/cue notes,
lyrics and voices. It evaluates ordered notes, chords, backup/forward events and
inherited divisions/time signatures using exact fractions. Empty measures, invalid
or missing timing, orphan chord notes, determinable duration mismatches, missing
expected lyrics, and available provider warning/error logs generate diagnostics.
Explicit implicit pickup measures are allowed to be shorter; unmarked pickups are
reported for review. Different simultaneous staff meters or mid-measure meter changes
are not guessed.

Every OMR result currently requires manual source comparison, even if these checks
find no issues. Passing structural checks is not proof that pitches, text, ties,
polyphony, note sizes or page coverage match the original. This is not full MusicXML
schema validation and cannot detect every rhythm omission masked by another voice.

## Small heads: known limitation and future correction boundary

Real Cung Dem Tin Mung runs on Audiveris 5.11.0 established:

- Baseline: 53 exported notes; simultaneous small-head size information absent.
- Small heads/beams enabled: four actual small-head interpretations in two small
  chords, zero exported as small/grace/cue, and only 49 exported notes.
- The regular G4 at “đem” was also classified small; the whole B4/G4 chord was omitted.
  Measures 2 and 6 became shorter, other chord tones disappeared, and ties regressed.

Audiveris `SmallChordInter` handling can exclude small chords from rhythmic voices
and treat linked small chords as grace material. Therefore these switches are not
globally enabled. A small head is not evidence of grace timing. OSMD cannot restore
size/pitches/onsets absent from the export; CSS/global note scaling cannot fix this.

A future selective-size correction must preserve pitch, octave, exact onset and
duration, voice, staff, chord membership, shared stem/beam and ties while storing
visual size independently. The extension boundary is the retained OMR plus original
MusicXML in `RecognitionResult`; corrections should be explicit, reviewable edits
before transposition. No automatic reconstruction or notation editor is implemented.
Mixed-size simultaneous chord rendering must be tested separately in OSMD 2.1.2;
its cue rendering selects scaling using the first graphical chord note.

## Settings

Environment settings are read by Pydantic Settings before FastAPI starts (no automatic `.env` load).

| Variable | Default |
|---|---|
| AUDIVERIS_EXECUTABLE | audiveris |
| RECOGNITION_DEFAULT_PROFILE | VOCAL_SONG |
| AUDIVERIS_OCR_LANGUAGES | Profile default |
| AUDIVERIS_INPUT_QUALITY | Profile default |
| AUDIVERIS_TESSDATA_PATH | Environment/Audiveris default |
| RECOGNITION_MAX_UPLOAD_BYTES | 20971520 |
| RECOGNITION_MAX_PAGES | 10 |
| RECOGNITION_MAX_IMAGE_PIXELS | 40000000 |
| RECOGNITION_MAX_OUTPUT_BYTES | 20971520 |
| RECOGNITION_MAX_ARCHIVE_MEMBERS | 128 |
| RECOGNITION_MAX_ARTIFACT_BYTES | 20971520 |
| RECOGNITION_MAX_LOG_BYTES | 131072 |
| RECOGNITION_MAX_DIAGNOSTICS | 100 (maximum 500) |
| RECOGNITION_TIMEOUT_SECONDS | 120 |

## Real-world validation still required

First complete the OCR checks above. Then run a CLI smoke test on a clean digital
church-song PDF, into a fresh directory:

```bash
omr_smoke_output=$(mktemp -d /tmp/audiveris-profile-smoke.XXXXXX)
/opt/audiveris/bin/Audiveris -batch -transcribe -export -save \
  -constant org.audiveris.omr.sheet.Profiles.defaultQuality=Synthetic \
  -constant org.audiveris.omr.text.Language.defaultSpecification=vie+eng \
  -constant org.audiveris.omr.sheet.ProcessingSwitches.lyrics=true \
  -constant org.audiveris.omr.sheet.ProcessingSwitches.chordNames=true \
  -constant org.audiveris.omr.sheet.ProcessingSwitches.smallHeads=false \
  -constant org.audiveris.omr.sheet.ProcessingSwitches.smallBeams=false \
  -output "$omr_smoke_output" -- /absolute/path/to/church-song.pdf
```

This CLI smoke command uses the operator's normal Audiveris configuration; the API
additionally applies the full conservative preset and isolated XDG directories.
Inspect logs for actual OCR initialization and Vietnamese text. Open the OMR project
in Audiveris and compare the original PDF with the export, especially “ta”, “cùng”,
“đem”, their onsets/durations/chords and the ties previously found to regress.

Start FastAPI with the exported environment above:

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload
```

Use the frontend to import the PDF with Vocal song / clean digital score; verify
profile/provider/review status, diagnostics, accented Vietnamese lyrics/chord names,
and both artifact downloads. Confirm short/empty measures are reported. Open the
OMR download in Audiveris for correction diagnostics. Transpose by 0 and ±2, preview,
download and compare timing/chords/ties against the recognized document and source.
Repeat using scanned PDF/images with Standard quality, and representative SATB,
piano and orchestral scores. Test a known-correct duration-bearing mixed-size chord
MusicXML separately in unchanged OSMD. Record failures rather than treating successful
export/rendering as recognition accuracy.

## Automated validation and remaining limits

Tests mock native recognition and cover profiles/languages, command construction,
MXL, artifact bounds, cleanup, diagnostics, API formats, and transpose handoff.
Run from `backend` with its `.venv`; if the shell adds ROS packages, isolate them:

```bash
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
```

Frontend checks: `npm run lint` and `npm run build` in `frontend`; then `git diff --check`.
No additional runtime Python package is required by this milestone.

Native recognition accuracy and Vietnamese OCR quality still require the manual
benchmark above. OCR preflight checks files rather than initializing bundled native
Tesseract. Log inspection is bounded and version-sensitive. Async jobs, persistence,
full source/OMR comparison, automatic accuracy scoring, selective note correction,
and OS CPU/memory/disk quotas are deferred. Multipart parsing can spool uploads before
endpoint checks, so production ingress still needs body limits. HTTP/proxy timeouts
must accommodate recognition. JSON/base64 artifacts increase bounded memory/network
usage; omitted or oversized artifacts cannot be recovered after workspace cleanup.
