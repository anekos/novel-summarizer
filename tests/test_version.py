import re

from novel_summarizer.version import version_string


def test_version_string_format() -> None:
    line = version_string()
    assert re.fullmatch(
        r"novel-summarizer \S+ \(commit [0-9a-f]{12}(-dirty)?(, built \S+)?\)"
        r"|novel-summarizer \S+ \(commit unknown\)",
        line,
    ), line
