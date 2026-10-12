"""Advisory music checks are read-only and separate from technical integrity."""
from dataclasses import replace

MUSIC_CODES = frozenset({
    "measure_overfilled", "voice_underfilled", "measure_duration_mismatch", "voice_overlap",
    "chord_duration", "complex_meter", "unknown_meter", "empty_measure",
    "tie_pitch_mismatch", "tie_voice_staff", "tie_timing", "tie_duplicate", "tie_unresolved",
})


def category(issue):
    return "MUSIC_WARNING" if issue.code in MUSIC_CODES else "TECHNICAL_ERROR" if issue.severity == "ERROR" else "INFORMATION"


def classify(issues):
    # Keep codes, locations and messages for scoped source confirmations.
    return [replace(issue, severity="WARNING") if issue.code in MUSIC_CODES else issue for issue in issues]
