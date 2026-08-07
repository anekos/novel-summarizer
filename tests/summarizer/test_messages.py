from novel_summarizer.summarizer.messages import build_summarize_user_message
from novel_summarizer.types import Character, NovelSummary, Setting


def _summary() -> NovelSummary:
    return NovelSummary(
        characters=[
            Character(
                name="太郎",
                features=["青年"],
                relationships=["花子の兄"],
                events=["旅に出た"],
            )
        ],
        plot=["太郎が旅に出る"],
        settings=Setting(time_period="現代", locations=["東京"]),
        key_scenes=["出発の場面"],
        symbols_motifs=["切符"],
        unresolved_mysteries=["旅の目的"],
    )


def test_first_chunk_message_contains_content_only() -> None:
    message = build_summarize_user_message("本文テキスト")

    assert "本文テキスト" in message
    assert "前回までの要約" not in message
    assert "登場していることが確認" not in message


def test_message_includes_previous_summary() -> None:
    message = build_summarize_user_message("新しい本文", _summary())

    assert "前回までの要約" in message
    assert "太郎" in message
    assert "新しい本文" in message


def test_message_appends_character_checklist() -> None:
    message = build_summarize_user_message("本文", None, ["太郎", "駅員"])

    assert "- 太郎" in message
    assert "- 駅員" in message
    assert "必ず characters に含めて" in message


def test_empty_or_none_names_omit_checklist() -> None:
    cases: tuple[list[str] | None, ...] = (None, [])
    for names in cases:
        message = build_summarize_user_message("本文", None, names)
        assert "登場していることが確認" not in message
