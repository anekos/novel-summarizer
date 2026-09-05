from novel_summarizer.types import Character, NovelSummary, NovelSummaryUpdate


def apply_update(
    previous: NovelSummary | None, update: NovelSummaryUpdate
) -> NovelSummary:
    """差分を前回までの要約に反映する。一度登録された人物は決して消えない"""
    characters: dict[str, Character] = (
        {c.name: c for c in previous.characters} if previous is not None else {}
    )

    for character in [*update.new_characters, *update.character_updates]:
        existing = characters.get(character.name)
        if existing is None:
            characters[character.name] = character
        else:
            characters[character.name] = _merge_character(existing, character)

    return NovelSummary(
        characters=list(characters.values()),
        plot=update.plot,
        settings=update.settings,
        key_scenes=update.key_scenes,
        symbols_motifs=update.symbols_motifs,
        unresolved_mysteries=update.unresolved_mysteries,
    )


def _merge_character(existing: Character, addition: Character) -> Character:
    return Character(
        name=existing.name,
        aliases=_merge_unique(existing.aliases, addition.aliases),
        features=_merge_unique(existing.features, addition.features),
        relationships=_merge_unique(existing.relationships, addition.relationships),
        events=_merge_unique(existing.events, addition.events),
    )


def _merge_unique(base: list[str], additions: list[str]) -> list[str]:
    merged = list(base)
    for item in additions:
        if item not in merged:
            merged.append(item)
    return merged
