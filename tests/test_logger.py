from pathlib import Path

from pytest import CaptureFixture

from novel_summarizer.logger import WithFileLogger


def test_with_file_logger_writes_console_and_file(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    log_path = tmp_path / "run.log"

    with WithFileLogger(log_path):
        print("hello world")

    captured = capsys.readouterr()

    assert "hello world" in captured.out
    assert log_path.read_text() == "hello world\n"
