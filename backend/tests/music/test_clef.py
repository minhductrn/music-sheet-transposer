from app.music.models.clef import Clef, ClefSign


def test_treble_clef() -> None:
    clef = Clef(
        sign=ClefSign.G,
        line=2,
        staff=1,
    )

    assert clef.sign == ClefSign.G
    assert clef.line == 2
    assert clef.staff == 1


def test_bass_clef() -> None:
    clef = Clef(
        sign=ClefSign.F,
        line=4,
        staff=2,
    )

    assert clef.sign == ClefSign.F
    assert clef.line == 4
    assert clef.staff == 2


def test_default_staff_is_one() -> None:
    clef = Clef(
        sign=ClefSign.G,
        line=2,
    )

    assert clef.staff == 1