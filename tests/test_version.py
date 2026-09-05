import json
import re
from importlib.metadata import Distribution
from unittest.mock import patch

from novel_summarizer.version import _direct_url_description, version_string


def test_version_string_format() -> None:
    line = version_string()
    assert re.fullmatch(
        r"novel-summarizer \S+ \(commit [0-9a-f]{12}(-dirty)?(, built \S+)?\)"
        r"|novel-summarizer \S+ \(commit unknown\)",
        line,
    ), line


class FakeDistribution:
    def __init__(self, direct_url: str | None):
        self._direct_url = direct_url

    def read_text(self, name: str) -> str | None:
        assert name == "direct_url.json"
        return self._direct_url


def _with_direct_url(direct_url: str | None) -> str | None:
    with patch.object(
        Distribution, "from_name", return_value=FakeDistribution(direct_url)
    ):
        return _direct_url_description()


def test_direct_url_with_vcs_info() -> None:
    direct_url = json.dumps(
        {
            "url": "git+https://example.com/x.git",
            "vcs_info": {"vcs": "git", "commit_id": "abcdef0123456789" + "0" * 24},
        }
    )
    assert _with_direct_url(direct_url) == "commit abcdef012345"


def test_direct_url_local_path_has_no_commit() -> None:
    direct_url = json.dumps({"url": "file:///somewhere", "dir_info": {}})
    assert _with_direct_url(direct_url) is None


def test_direct_url_missing() -> None:
    assert _with_direct_url(None) is None
