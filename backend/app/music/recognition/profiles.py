"""Score presets configure one provider; they are not separate OMR engines."""

from dataclasses import dataclass, replace
from enum import StrEnum

from app.core.config import Settings


class RecognitionProfile(StrEnum):
    VOCAL_SONG = "VOCAL_SONG"
    SATB = "SATB"
    PIANO = "PIANO"
    GENERAL = "GENERAL"
    ORCHESTRAL = "ORCHESTRAL"


class InputQuality(StrEnum):
    SYNTHETIC = "Synthetic"
    STANDARD = "Standard"
    POOR = "Poor"


@dataclass(frozen=True)
class ProfileOptions:
    profile: RecognitionProfile
    input_quality: InputQuality
    ocr_languages: str
    lyrics: bool
    chord_names: bool
    fingerings: bool = False
    tremolos: bool = False

    def constants(self) -> dict[str, str]:
        switches = {
            "lyrics": self.lyrics, "chordNames": self.chord_names,
            "fingerings": self.fingerings, "tremolos": self.tremolos,
            # These are deliberately explicit, overriding persisted defaults.
            "smallHeads": False, "smallBeams": False, "crossHeads": False,
            "frets": False, "pluckings": False, "partialWholeRests": False,
            "drumNotation": False, "oneLineStaves": False,
            "fourStringTablatures": False, "sixStringTablatures": False,
            "fiveLineStaves": True,
            "keepGrayImages": True,
        }
        return {
            "org.audiveris.omr.sheet.Profiles.defaultQuality": self.input_quality.value,
            "org.audiveris.omr.text.Language.defaultSpecification": self.ocr_languages,
            **{f"org.audiveris.omr.sheet.ProcessingSwitches.{key}": str(value).lower()
               for key, value in switches.items()},
        }


_PROFILES = {
    RecognitionProfile.VOCAL_SONG: ProfileOptions(
        RecognitionProfile.VOCAL_SONG, InputQuality.SYNTHETIC, "vie+eng", True, True,
    ),
    RecognitionProfile.SATB: ProfileOptions(
        RecognitionProfile.SATB, InputQuality.STANDARD, "vie+eng", True, False,
    ),
    RecognitionProfile.PIANO: ProfileOptions(
        RecognitionProfile.PIANO, InputQuality.STANDARD, "eng", False, False, fingerings=True,
    ),
    RecognitionProfile.GENERAL: ProfileOptions(
        RecognitionProfile.GENERAL, InputQuality.STANDARD, "eng", True, True,
    ),
    RecognitionProfile.ORCHESTRAL: ProfileOptions(
        RecognitionProfile.ORCHESTRAL, InputQuality.STANDARD, "eng", False, False, tremolos=True,
    ),
}


def resolve_profile(
    config: Settings, profile: RecognitionProfile | None = None,
    input_quality: InputQuality | None = None,
) -> ProfileOptions:
    preset = _PROFILES[RecognitionProfile(profile or config.recognition_default_profile)]
    return replace(
        preset,
        input_quality=InputQuality(input_quality or config.audiveris_input_quality or preset.input_quality),
        ocr_languages=config.audiveris_ocr_languages or preset.ocr_languages,
    )
