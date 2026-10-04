from fractions import Fraction

import pytest

from app.music.recognition.symbolic import parse_symbolic, transcription_text


def test_actual_model_delimiters_and_ekern_header():
    raw = "<bos>**ekern_1.0<t>**ekern_1.0<b>*clefG2<t>*clefF4<b>4c<s>4e<t>4C<b>*-<t>*-<eos>"
    parsed = parse_symbolic(raw)
    assert parsed["metrics"]["notes"] == 3
    assert parsed["metrics"]["chord_groups"] == 1
    assert parsed["metrics"]["simultaneous_events"] == 1
    assert parsed["parsing"]["coverage"] == 1
    assert parsed["parsing"]["timeline_reliable"] is True
    assert parsed["events"][0]["onset_quarters"] == parsed["events"][2]["onset_quarters"] == "0"
    assert len(parsed["clefs"]) == 2
    assert transcription_text(raw).startswith("**ekern_1.0\t**ekern_1.0\n")


@pytest.mark.parametrize(("token", "step", "octave", "alter", "duration"), [
    ("4c", "C", 4, 0, "1"), ("8.cc#", "C", 5, 1, "3/4"),
    ("2BB--", "B", 2, -2, "2"), ("16..Fn", "F", 3, 0, "7/16"),
    ("3g", "G", 4, 0, "4/3"), ("0C", "C", 3, 0, "8"),
    ("00C", "C", 3, 0, "16"), ("3%2a", "A", 4, 0, "8/3"),
])
def test_pitch_and_exact_encoded_duration(token, step, octave, alter, duration):
    event = parse_symbolic("**kern\n" + token)["events"][0]
    assert event["pitch"] == {"step": step, "octave": octave, "alter": alter}
    assert Fraction(event["duration_quarters"]) == Fraction(duration)


def test_small_chord_pitches_remain_simultaneous_and_are_not_assumed_grace():
    parsed = parse_symbolic("**ekern_1.0\n*M2/4\n=1\n8a 8cc\n8f 8a\n4g 4b-\n=2\n*-")
    assert parsed["metrics"]["notes"] == 6
    assert parsed["metrics"]["chord_groups"] == 3
    assert parsed["metrics"]["grace_notes"] == 0
    events = parsed["events"]
    assert [e["pitch"] for e in events[:2]] == [
        {"step": "A", "octave": 4, "alter": 0}, {"step": "C", "octave": 5, "alter": 0}]
    assert [e["onset_quarters"] for e in events] == ["0", "0", "1/2", "1/2", "1", "1"]
    assert [e["beat"] for e in events] == ["1", "1", "3/2", "3/2", "2", "2"]
    assert all(not event["grace"] for event in events)


def test_key_is_reported_but_kern_accidentals_are_absolute():
    parsed = parse_symbolic("**kern\n*k[b-]\n4b\n4b-\n4bn\n4r\n=2")
    assert [e["pitch"]["alter"] for e in parsed["events"][:3]] == [0, -1, 0]
    assert parsed["keys"][0]["value"] == "*k[b-]"
    assert parsed["metrics"]["rests"] == 1
    assert parsed["metrics"]["barline_rows"] == 1


def test_polyphony_null_continuations_and_spine_split_join():
    parsed = parse_symbolic("**kern\n*^\n2c\t4e\n.\t4f\n*v\t*v\n4g\n*-")
    assert parsed["parsing"]["timeline_reliable"] is True
    assert [e["onset_quarters"] for e in parsed["events"]] == ["0", "0", "1", "2"]
    assert parsed["metrics"]["simultaneous_events"] == 1


def test_grace_requires_encoded_q_and_consumes_no_metric_time():
    parsed = parse_symbolic("**kern\ncq\n4d\n4e")
    assert [e["onset_quarters"] for e in parsed["events"]] == ["0", "0", "1"]
    assert parsed["metrics"]["grace_notes"] == 1


def test_mixed_grace_and_metric_spines_do_not_claim_reliable_timing():
    parsed = parse_symbolic("**kern\t**kern\ncq\t4e")
    assert parsed["parsing"]["timeline_reliable"] is False
    assert all(event["onset_quarters"] is None for event in parsed["events"])
    assert parsed["parsing"]["unsupported_tokens"][-1]["reason"] == "mixed_grace_and_metric_record"


@pytest.mark.parametrize("unsupported", ["unknown", "4cXYZ", "*x", "*staff+1", "16cQ", "4c 8e"])
def test_partial_parsing_retains_unsupported_tokens(unsupported):
    raw = "**kern\n4c\n" + unsupported + "\n4d"
    parsed = parse_symbolic(raw)
    assert parsed["metrics"]["notes"] >= 2
    assert parsed["parsing"]["coverage"] < 1
    assert parsed["parsing"]["unsupported_tokens"]
    assert unsupported in parsed["text"]


@pytest.mark.parametrize("raw", ["4c", "**kern\n.\n4d", "**kern\n4c\t4e", "**kern\n4c 8e\n4g"])
def test_ambiguous_timing_is_never_fabricated(raw):
    parsed = parse_symbolic(raw)
    assert parsed["parsing"]["timeline_reliable"] is False
    assert all(event["onset_quarters"] is None for event in parsed["events"])


def test_empty_and_hostile_duration_text_is_bounded():
    assert parse_symbolic("")["parsing"]["coverage"] == 0
    parsed = parse_symbolic("**kern\n" + "9" * 5000 + "c\n4d")
    assert parsed["parsing"]["timeline_reliable"] is False
    assert parsed["events"][-1]["duration_quarters"] == "1"
