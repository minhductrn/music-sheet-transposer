from app.music.recognition.result import RecognitionIssue


class RecognitionError(Exception):
    def __init__(
        self, message: str, status_code: int = 422,
        diagnostics: tuple[RecognitionIssue, ...] = (),
    ):
        super().__init__(message)
        self.status_code = status_code
        self.diagnostics = diagnostics
