import novel_summarizer.prompts as P
from novel_summarizer.types import NovelSummary


def build_summarize_user_message(
    page_content: str,
    previous_summary: NovelSummary | None = None,
    character_names: list[str] | None = None,
) -> str:
    """要約コールに渡す user message を組み立てる"""
    if previous_summary is None:
        message = f"以下の内容を要約してください:\n\n{page_content}"
    else:
        summary_json = previous_summary.model_dump_json(indent=2, ensure_ascii=False)
        known_names = "\n".join(f"- {c.name}" for c in previous_summary.characters)
        message = f"""以下は前回までの要約です:

{summary_json}

---

{P.KnownCharacters.format(names=known_names)}

---

以下の新しい内容を読んで、上記の要約を更新してください:

{page_content}"""

    if character_names:
        names = "\n".join(f"- {name}" for name in character_names)
        message += "\n\n---\n\n" + P.CharacterChecklist.format(names=names)

    return message
