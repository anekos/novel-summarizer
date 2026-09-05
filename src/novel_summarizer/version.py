import json
from importlib.metadata import PackageNotFoundError
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
    # build_info.json は make install が生成する。開発時の実行では存在しない
    try:
        raw = (files("novel_summarizer") / "build_info.json").read_text("utf-8")
        info = json.loads(raw)
    except (OSError, ValueError):
        return "commit unknown"

    commit = str(info.get("commit", ""))[:12] or "unknown"
    if info.get("dirty"):
        commit += "-dirty"

    built_at = info.get("built_at")
    if built_at:
        return f"commit {commit}, built {built_at}"
    return f"commit {commit}"
