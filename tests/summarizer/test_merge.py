from novel_summarizer.summarizer.merge import apply_update
from novel_summarizer.types import (
    Character,
    NovelSummary,
    NovelSummaryUpdate,
    Setting,
)


def _character(name: str, **kwargs: list[str]) -> Character:
    return Character(
        name=name,
        features=kwargs.get("features", []),
        relationships=kwargs.get("relationships", []),
        events=kwargs.get("events", []),
    )


def _update(
    new_characters: list[Character] | None = None,
    character_updates: list[Character] | None = None,
) -> NovelSummaryUpdate:
    return NovelSummaryUpdate(
        new_characters=new_characters or [],
        character_updates=character_updates or [],
        plot=["新しいあらすじ"],
        settings=Setting(time_period="現代", locations=["東京"]),
        key_scenes=[],
        symbols_motifs=[],
        unresolved_mysteries=[],
    )


def _previous(*characters: Character) -> NovelSummary:
    return NovelSummary(
        characters=list(characters),
        plot=["古いあらすじ"],
        settings=Setting(time_period="現代", locations=["東京"]),
        key_scenes=[],
        symbols_motifs=[],
        unresolved_mysteries=[],
    )


def test_existing_characters_survive_even_if_absent_from_update() -> None:
    previous = _previous(_character("太郎"), _character("花子"))

    result = apply_update(previous, _update())

    assert [c.name for c in result.characters] == ["太郎", "花子"]


def test_new_characters_are_added() -> None:
    previous = _previous(_character("太郎"))

    result = apply_update(previous, _update(new_characters=[_character("次郎")]))

    assert [c.name for c in result.characters] == ["太郎", "次郎"]


def test_first_chunk_works_without_previous_summary() -> None:
    result = apply_update(None, _update(new_characters=[_character("太郎")]))

    assert [c.name for c in result.characters] == ["太郎"]
    assert result.plot == ["新しいあらすじ"]


def test_character_updates_append_without_duplicates() -> None:
    previous = _previous(
        _character("太郎", features=["青年"], events=["旅に出た"]),
    )
    update = _update(
        character_updates=[
            _character("太郎", features=["青年", "剣士"], events=["帰郷した"]),
        ]
    )

    result = apply_update(previous, update)

    taro = result.characters[0]
    assert taro.features == ["青年", "剣士"]
    assert taro.events == ["旅に出た", "帰郷した"]


def test_known_name_in_new_characters_merges_instead_of_overwriting() -> None:
    previous = _previous(_character("太郎", features=["青年"]))
    update = _update(new_characters=[_character("太郎", features=["剣士"])])

    result = apply_update(previous, update)

    assert len(result.characters) == 1
    assert result.characters[0].features == ["青年", "剣士"]


def test_unknown_name_in_character_updates_is_added_as_new() -> None:
    previous = _previous(_character("太郎"))
    update = _update(character_updates=[_character("謎の老人", features=["白髪"])])

    result = apply_update(previous, update)

    assert [c.name for c in result.characters] == ["太郎", "謎の老人"]


def test_rolling_fields_come_from_update() -> None:
    previous = _previous(_character("太郎"))

    result = apply_update(previous, _update())

    assert result.plot == ["新しいあらすじ"]
