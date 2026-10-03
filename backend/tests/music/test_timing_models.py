from app.music.models.timing import Backup, Forward


def test_backup_model() -> None:
    backup = Backup(duration=4)

    assert backup.duration == 4


def test_forward_model() -> None:
    forward = Forward(duration=2)

    assert forward.duration == 2