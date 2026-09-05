import json
from importlib.metadata import Distribution, PackageNotFoundError
from importlib.metadata import version as package_version
from importlib.resources import files


def version_string() -> str:
    """ログ先頭などに記録するバージョン行を組み立てる"""
    try:
        package = package_version("novel-summarizer")
    except PackageNotFoundError:
        package = "unknown"

    return f"novel-summarizer {package} ({_commit_description()})"


def _commit_description() -> str:
    return _build_info_description() or _direct_url_description() or "commit unknown"


def _build_info_description() -> str | None:
    # build_info.json は make install が生成する。開発時の実行では存在しない
    try:
        raw = (files("novel_summarizer") / "build_info.json").read_text("utf-8")
        info = json.loads(raw)
    except (OSError, ValueError):
        return None

    commit = str(info.get("commit", ""))[:12]
    if not commit:
        return None
    if info.get("dirty"):
        commit += "-dirty"

    built_at = info.get("built_at")
    if built_at:
        return f"commit {commit}, built {built_at}"
    return f"commit {commit}"


def _direct_url_description() -> str | None:
    # git URL からインストールされた場合のみ、PEP 610 メタデータにコミットが残る
    try:
        raw = Distribution.from_name("novel-summarizer").read_text("direct_url.json")
        if raw is None:
            return None
        info = json.loads(raw)
    except (PackageNotFoundError, OSError, ValueError):
        return None

    vcs_info = info.get("vcs_info")
    if not isinstance(vcs_info, dict):
        return None

    commit = str(vcs_info.get("commit_id", ""))[:12]
    if not commit:
        return None
    return f"commit {commit}"
