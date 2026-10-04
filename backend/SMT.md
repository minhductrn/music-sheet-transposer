# Phase 4D.1: local Sheet Music Transformer benchmark

SMT is **EXPERIMENTAL / BENCHMARK ONLY**, disabled by default (`SMT_ENABLED=false`).
This proof of concept evaluates music-symbol recognition independently of Audiveris.
Audiveris remains the default production provider and retains Vietnamese OCR
(`vie+eng`), MusicXML/MXL handling and existing validation. No fusion, editor work,
fine-tuning, automatic corrections or MusicXML reconstruction is added here.

## Architecture and compatibility

```text
MusicRecognitionService (existing upload checks and temporary workspace)
  ├─ AudiverisProvider → original uncompressed MusicXML → existing validation
  └─ SMTProvider (EXPERIMENTAL / BENCHMARK ONLY; explicit enable required)
       → isolated Python subprocess → native symbolic benchmark evidence
```

Both implement `MusicRecognitionProvider.recognize_result`. Existing bytes-only
custom providers still work. `create_provider(Settings())` selects
`RECOGNITION_PROVIDER`, defaulting to `audiveris`. The HTTP layer uses this factory
and has no engine-specific branches. `evaluate_result` accepts native symbolic
results for the local benchmark. The existing `.recognize`/`.recognize_result`
MusicXML interfaces explicitly reject a symbolic-only result with
`musicxml_unavailable` (HTTP 422); selecting SMT does **not** make the current
frontend preview/transposition flow accept eKern. Use the CLI below for SMT.
Selecting SMT does not enable it. While disabled, a recognition attempt fails with
HTTP 503 and diagnostic code `smt_disabled`, including the required opt-in setting.
The lightweight provider can be constructed without starting its worker, so this
configuration error is reported through the existing structured error interface.
The gate also applies to prepare-only jobs. There is no automatic fallback from
Audiveris to SMT, model download, or SMT worker startup during normal recognition.
Default backend startup and Audiveris recognition require no SMT runtime.

SMT's [official implementation](https://github.com/antoniorv6/SMT) and
[GrandStaff model](https://huggingface.co/antoniorv6/smt-grandstaff) are MIT licensed.
Keep upstream license notices with the downloaded source/model. The model uses
a ConvNeXt image encoder and autoregressive Transformer decoder. These particular
pretrained models are piano-system models, not general vocal-score or Vietnamese
text recognizers. The named GrandStaff checkpoint is the initial clean-print
candidate; [Camera GrandStaff](https://huggingface.co/antoniorv6/smt-camera-grandstaff)
is an explicit alternative, never an automatic second download. The GrandStaff
model card contains inconsistent camera-related metadata; the benchmark records
the actual model ID and immutable checkpoint revision rather than claiming a
domain guarantee from the name.

The working source/checkpoint combination is pinned:

- Official source: `d25acd4373ad868a1e0f1c352d2f5dc8ffa94f54`.
- GrandStaff checkpoint: `2eb5a45c29d63bdf063cd0427175f57675e7da9e`.
- Python 3.11; CPU PyTorch 2.6.0 / torchvision 0.21.0; transformers 4.49.0.

**Do not use current upstream master with these old weights.** During validation,
master `20d8240c47b4a1851e9a5aa5a0ca3d0ddbc16da8` had renamed/refactored decoder
parameters: Transformers initialized missing decoder weights randomly. The worker
rejects any missing, unexpected or mismatched checkpoint weights. The pinned
pre-refactor source loaded this checkpoint completely. Revalidate source and model
together when changing either. No upstream code or checkpoint keys are patched.

## Optional experimental installation on this WSL Ubuntu host

These instructions are retained for deliberate future benchmark work. The Phase
4D.1 benchmark is complete; no further installation, download or inference is
required to use or validate the normal application.

The backend currently uses Python 3.14.4. Leave it and `backend/.venv` unchanged.
Upstream's training requirements include Torch, torchvision, Transformers,
OpenCV, scikit-image, Lightning, datasets and rendering/training libraries. This
worker needs only the inference subset. It uses the same deterministic
RGB → grayscale → tensor conversion as the official inference helper, without
importing its training augmentation module and unnecessary CV dependencies.
PDFium is installed in the worker environment for PDF rendering.

Use a directory **outside the repository**, such as
`~/.local/share/music-sheet-transposer/smt`. Python, upstream source, weights and
caches belong there, not in the backend virtual environment. A temporary
`/tmp/smt-poc-runtime` environment was used for this milestone's real validation;
it is disposable, not deployment configuration.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not
already available. The following commands install a separate managed interpreter;
they do not downgrade system/backend Python. Run from this project's `backend`:

```bash
# Skip the installer if uv is already installed.
curl -LsSf https://astral.sh/uv/0.12.23/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

smt_root="$HOME/.local/share/music-sheet-transposer/smt"
mkdir -p "$smt_root/bin"
UV_PYTHON_INSTALL_DIR="$smt_root/python" UV_PYTHON_BIN_DIR="$smt_root/bin" \
  uv python install 3.11.17
uv venv --python "$smt_root/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11" \
  "$smt_root/.venv"
uv pip install --python "$smt_root/.venv/bin/python" \
  torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "$smt_root/.venv/bin/python" -r smt_worker/requirements.txt

git clone --filter=blob:none https://github.com/antoniorv6/SMT.git "$smt_root/upstream"
git -C "$smt_root/upstream" checkout d25acd4373ad868a1e0f1c352d2f5dc8ffa94f54

export HF_HOME="$smt_root/hf"
# This is the one explicit online model download (about 85.5 MB of weights).
env HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 "$smt_root/.venv/bin/python" - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    "antoniorv6/smt-grandstaff",
    revision="2eb5a45c29d63bdf063cd0427175f57675e7da9e",
    allow_patterns=["config.json", "model.safetensors"],
)
PY

export SMT_WORKER_PYTHON="$smt_root/.venv/bin/python"
export SMT_UPSTREAM_PATH="$smt_root/upstream"
export SMT_MODEL_REFERENCE=antoniorv6/smt-grandstaff
export SMT_MODEL_REVISION=2eb5a45c29d63bdf063cd0427175f57675e7da9e
export SMT_DEVICE=auto
```

The weight downloader is an operator command, never part of inference or tests.
Inference uses `local_files_only=True`, safetensors and offline Hub/Transformers
settings. A missing cache fails explicitly while retaining preprocessing evidence.

`auto` chooses CUDA if Torch reports it available; otherwise CPU. The CPU wheels
above are the verified configuration on this host. Explicit `cuda` fails when
unavailable. For an already configured WSL CUDA environment, install the matching
Torch 2.6.0/torchvision 0.21.0 CUDA wheels using the
[official version instructions](https://pytorch.org/get-started/previous-versions/)
instead of CPU wheels. GPU inference is not required and was not validated here.
The worker records the selected device and uses evaluation/inference mode, a fixed
seed, and a bounded CPU thread count. This does not promise bitwise GPU determinism.

## Configuration

Pydantic reads environment variables before startup; no automatic `.env` loading.
Keep `RECOGNITION_PROVIDER=audiveris` and `SMT_ENABLED=false` for the normal
application. Enabling SMT does not change provider selection. For a deliberate
development experiment, both `SMT_ENABLED=true` and `RECOGNITION_PROVIDER=smt`
are required to select it for HTTP recognition (which still cannot return MusicXML).
For the local benchmark, set `SMT_ENABLED=true` only on the CLI invocation, as below;
`--providers smt` selects the benchmark engine without changing the application default.

| Variable | Default / meaning |
|---|---|
| RECOGNITION_PROVIDER | `audiveris`; `smt` is EXPERIMENTAL / BENCHMARK ONLY |
| SMT_ENABLED | `false`; set `true` explicitly for experimental development/benchmarks |
| SMT_WORKER_PYTHON | Required isolated Python executable path, not a shell command |
| SMT_UPSTREAM_PATH | Required official source checkout; use the pinned revision above |
| SMT_MODEL_REFERENCE | `antoniorv6/smt-grandstaff` |
| SMT_MODEL_REVISION | `2eb5a45c29d63bdf063cd0427175f57675e7da9e` |
| SMT_DEVICE | `auto`, `cpu`, or `cuda` |
| SMT_PDF_DPI | `200`; range 72–600 |
| SMT_STAVES_PER_SYSTEM | `2`; set `1` explicitly for a single-staff benchmark |
| SMT_MAX_SYSTEMS | `64`; maximum 128 |
| SMT_TIMEOUT_SECONDS | `600` for the entire worker job, including preparation/model load |
| SMT_CPU_THREADS | `4`; maximum 32 |
| HF_HOME | The explicitly downloaded model cache, inherited by the worker |

Existing upload/page/pixel/output/artifact limits also apply. For a different model,
set **both** `SMT_MODEL_REFERENCE` and its corresponding immutable
`SMT_MODEL_REVISION`, explicitly download that checkpoint and check source
compatibility. The GrandStaff revision does not belong to Camera GrandStaff.

## Preparation and systems

PDFium renders pages in order at the configured DPI on a white background. Original
page dimensions in points, rendered dimensions and DPI are recorded. Images are
EXIF-oriented, alpha-composited onto white and converted to RGB; original image
dimensions/orientation are retained in service diagnostics. No deskewing, sharpening,
erosion, staff removal or visual note-size inference is performed.

The small segmentation heuristic detects long dark horizontal lines, groups five
approximately equidistant lines into a staff, and groups the explicitly configured
number of staves per system. Crops retain original RGB pixels, modest horizontal
and vertical context, page number and `[left, top, right, bottom]` coordinates in
rendered-page pixels. Systems are ordered by page, top and left. Incomplete staff
groups and no-staff pages fail explicitly; there is no whole-page fallback disguised
as successful system detection.

All proposals carry `segmentation_requires_visual_review`. Skewed/broken/short
staves, multiple columns, tablature and large staff gaps are outside this heuristic.
It can crop lyric lines or annotation context; inspect the retained full page and
every crop. The single-staff setting does not retrain a piano model or make its
predictions reliable. Optional explicit boxes bypass automatic proposals:

```json
[{"page": 1, "bbox": [120, 340, 1560, 560]}]
```

Supply a local JSON file with `--boxes /path/to/boxes.json`. Coordinates must match
the configured DPI; pages are one-based, dimensions must be positive and in bounds,
duplicates are rejected. Manual boxes also require visual review.

Each crop runs independently through the official `SMTModelForCausalLM.predict`.
Only crops exceeding the checkpoint's `maxh=256` / `maxw=3056` bounds are scaled
down, maintaining aspect ratio; original box, inference dimensions and scale are
recorded. No crops are scaled up. Resizing can erase small-head evidence. A token
limit warning marks potentially truncated model output.

## Symbolic evidence and limits of parsing

This checkpoint's vocabulary starts with `**ekern_1.0`, a kern-family format, not
MusicXML. Preserve the exact token list and joined raw string. The readable view
replaces `<b>` with newline, `<t>` with tab and `<s>` with space. Examples include
`8a 8cc` (A4/C5 chord), `4b-` (B-flat4), `4r` (rest), `*clefG2`, `*k[b-]`, `*M2/4`,
barlines, null continuations and spine split/join controls. These examples explain
the parser, not a prediction guaranteed for the benchmark song.

The partial analytical parser reports encoded pitches, exact fractional durations,
chord cells, supported polyphonic onsets, barline rows/labels and clef/key/time/staff
information. Kern accidentals are absolute; a key signature does not implicitly
change an unaltered kern pitch. Only an **encoded** `q` identifies grace semantics;
small image heads never imply grace timing. `Q` groupettos and inconsistent/missing
durations invalidate timing claims instead of borrowing guessed durations. Unsupported
spine operations, eKern extensions and annotations remain visible in raw output and
the unsupported-token list. See the [kern specification](https://www.humdrum.org/rep/kern/).

Coverage is `parsed_cells / total_cells`, a parser coverage ratio, **not OMR accuracy**.
It does not establish source pitches, visual size, voice/staff assignment, timing,
shared stems, ties or lyrics. Onsets after an unsupported timing operation are null.
System transcriptions are not stitched into a guessed whole score: boundary barlines
can repeat, numbered labels can restart, and key/meter context can be missing on later
systems. Aggregate counts have this explicit scope. There is no MusicXML converter.

## Exact Cùng Đem Tin Mừng benchmark

From `backend`, after the setup above, use the installed Audiveris launcher and the
actual OCR directory. On the inspected host the language files live under
`~/.config/AudiverisLtd/audiveris/tessdata`, not the distro's `/usr/share` path:

```bash
export AUDIVERIS_EXECUTABLE=/opt/audiveris/bin/Audiveris
export AUDIVERIS_TESSDATA_PATH="$HOME/.config/AudiverisLtd/audiveris/tessdata"
export SMT_STAVES_PER_SYSTEM=1
export SMT_PDF_DPI=200
export SMT_CPU_THREADS=1
benchmark_root=$(mktemp -d /tmp/smt-benchmark.XXXXXX)

# Inspect the rendered page and all crops before interpreting predictions.
env -u PYTHONPATH SMT_ENABLED=true .venv/bin/python -m app.music.recognition.benchmark \
  --providers smt --prepare-only \
  --source '/mnt/c/Users/dtran/Downloads/BaihatCN/CN25 Thuong Nien - Nam A/cungdemTinMung.pdf' \
  --output "$benchmark_root/prepared"

# Independent results from exactly the same source bytes; no text/music fusion.
env -u PYTHONPATH SMT_ENABLED=true .venv/bin/python -m app.music.recognition.benchmark \
  --source '/mnt/c/Users/dtran/Downloads/BaihatCN/CN25 Thuong Nien - Nam A/cungdemTinMung.pdf' \
  --output "$benchmark_root/results"
```

`--providers smt` or `--providers audiveris` runs one engine. Prepare-only records
`success=false` and `inference_not_run`, although the CLI exits zero when crops were
prepared. A full benchmark exits nonzero if either requested engine fails, while
still writing both independent results. An existing output directory is refused.
The source path above is only an operator example; production code contains no song
path or song-specific corrections.

`benchmark.json` includes source hash/page count, recognition durations, independent
provider successes/diagnostics, Audiveris MusicXML structural metrics and all SMT
systems/raw tokens/parsed events. Audiveris counts measures by part, notes/rests,
chord markers/groups and determinable simultaneous onsets, keys/time signatures and
lyric-linked events. SMT counts supported notes/rests/chord cells/simultaneous rows
and barlines; unsupported tokens and timeline reliability are explicit. MusicXML
layout cannot always establish source system count, so absent layout is reported
as unknown. These measures are structural observations, not a substitute for ground
truth or an accuracy percentage.

Inspect `smt/pages/`, `smt/systems/`, and `smt/transcriptions/*.tokens.json`, `*.txt`,
`*.parsed.json`, plus `audiveris/recognized.musicxml` and any bounded `.omr`. Compare
the first system with the original PDF, aligning events manually to lyric positions:

- “ta”: regular A4 + smaller C5, simultaneous/shared stem.
- “cùng”: regular F4 + smaller A4, simultaneous/shared stem.
- “đem”: regular G4 + smaller upper B4/B-flat4; verify against the key/source.

Check pitch spelling, duration, barline/beat location, chord cell and onset equality.
Inspect any `q`/`Q` prediction separately: a generated grace marker for these timed
chords would be a recognition error, not evidence that the original small note was
grace. SMT has no Vietnamese lyric-location mapping or independent small-note-size
representation in this parser. Do not infer correct stem/size rendering just from
two parsed pitches. Retain the original PDF alongside the benchmark for review.

## Phase 4D.1 Benchmark Decision

**SMT is retained as EXPERIMENTAL / BENCHMARK ONLY. Audiveris remains the default
production OMR engine.** The completed benchmark tested `antoniorv6/smt-grandstaff`
on Cùng Đem Tin Mừng on 2026-10-03. There is no evidence here supporting replacement
of Audiveris with SMT.

The source was one PDF page, SHA-256
`30df9a6988ecc7752c2a89dcd84bcc87b44259b88803e2636f817ede7b15b81a`.
Rendering at 200 DPI produced 1654 × 2339 pixels. The heuristic proposed three
single-staff systems; visual inspection confirmed that the crops included the
musical notation. Some lyric context was clipped, so these are music-symbol
crops, not validated OCR crops.

The whole-score CPU benchmark retained all three crops but hit the 600-second
worker limit before completing its first SMT transcription. This occurred with
both four and one CPU threads. Zero completed outputs is a runtime failure, not
evidence that the source has zero notes. Audiveris, run outside the development
sandbox, completed in about 30 seconds: 51 pitched notes, 17 measures, nine chord
groups and three explicitly laid-out systems. This fresh recognition result differs
from the historical 53-note export; neither count establishes source accuracy.

A separate bounded experiment used an explicit first-two-measure crop,
`[211, 339, 853, 546]` at 200 DPI, and one CPU thread. It completed in about 24
seconds including model loading (about 15 seconds inference). SMT returned nine
pitched tokens, two rests, two chord cells and three barline rows. The parser
understood 69 of 73 cells, but malformed spine structure prevented reliable timing.
The raw output includes duplicated C5 and low-register F2/B-flat2/C2/D2 material;
it contains no A4, F4 or G4. Therefore none of the three target pitch pairs is
recovered in this excerpt. An isolated B-flat4 token cannot establish the “đem”
location without its regular G4 and reliable onset/duration. There are no `q`
grace markers, but the format does not establish independent visual head size.

This is negative evidence for this particular piano-domain checkpoint and input
preparation, not a general comparison of all SMT models. The raw excerpt and
failed whole-score reports remain useful evidence. Successful inference means
bounded output was returned, not that the notation matches the source.
SMT has significant CPU cost in this environment. GPU inference was not evaluated
and is not required for this milestone: faster GPU execution would address
throughput, not the recognition/domain mismatch demonstrated by the completed
excerpt. These results do not generalize to every score or SMT checkpoint.

For reference, the narrower experiment used this command after the setup above;
rerunning it is not required for Phase 4D.1:

```bash
excerpt_root=$(mktemp -d /tmp/smt-excerpt.XXXXXX)
cat > "$excerpt_root/boxes.json" <<'JSON'
[{"page": 1, "bbox": [211, 339, 853, 546]}]
JSON
env -u PYTHONPATH SMT_ENABLED=true .venv/bin/python -m app.music.recognition.benchmark \
  --source '/mnt/c/Users/dtran/Downloads/BaihatCN/CN25 Thuong Nien - Nam A/cungdemTinMung.pdf' \
  --boxes "$excerpt_root/boxes.json" --output "$excerpt_root/results"
```

These coordinates are benchmark documentation only. No song-specific boxes,
corrections or source paths are encoded in production code.

The next recognition work will focus on **Audiveris → .omr + MusicXML evidence →
semantic recovery → musical validation → corrected MusicXML**. SMT is outside this
production path at present. Semantic recovery is a future milestone, not implemented
as part of Phase 4D.1.

## Bounds, cleanup and validation

The worker runs with `-I`, an argument list, no shell, no inherited PYTHONPATH and
offline model loading. A timeout kills/waits for its POSIX process group. It writes
an atomic partial result after preparation and each system, so completed raw
transcriptions survive a later failure or timeout. Provider validation checks JSON
types, model identity, boxes/order, token consistency, image dimensions/formats,
symlinks, record counts and byte limits. Per-provider temporary directories are
always removed. Model weights live in the explicit operator-managed cache.

PNG debug storage is bounded by `RECOGNITION_MAX_ARTIFACT_BYTES` (20 MiB default);
symbolic JSON by `RECOGNITION_MAX_OUTPUT_BYTES` (20 MiB). CLI output, including raw
and parsed copies and Audiveris artifacts, is bounded to 64 MiB total by default
(`--max-debug-bytes`). Storage is local, with no arbitrary server-path download API.
Debug directories remain for operator inspection/removal; no retention daemon is
added. Worker logs are not relayed to clients. OS-level CPU/memory/disk quotas,
production GPU scheduling and persistent model workers remain future work.

Automated tests mock inference and PDFium. They require no Torch, GPU, model download
or internet in the main backend environment. Run all checks:

```bash
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
cd ../frontend
npm run lint
npm run build
git diff --check
```
