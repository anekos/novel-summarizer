import os
from collections.abc import Iterator

from openai import OpenAI

import novel_summarizer.prompts as P
from novel_summarizer.types import NovelOverview, NovelSummary, PageChunk

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY_FOR_NOVEL_SUMMARIZER"))


def summarize(chunks: list[PageChunk]) -> Iterator[tuple[PageChunk, NovelSummary]]:
    previous_summary: NovelSummary | None = None

    for chunk in chunks:
        summary = summarize_page(chunks[0].text, previous_summary)
        yield chunk, summary
        previous_summary = summary


def summarize_page(
    page_content: str, previous_summary: NovelSummary | None = None
) -> NovelSummary:
    """
    ページを要約する（前回の要約があれば統合する）

    Args:
        page_content: 新しいページの内容
        previous_summary: 前回までの要約（初回は None）

    Returns:
        更新された要約
    """
    if previous_summary is None:
        user_message = f"以下の内容を要約してください:\n\n{page_content}"
    else:
        user_message = f"""以下は前回までの要約です:

{previous_summary.model_dump_json(indent=2, ensure_ascii=False)}

---

以下の新しい内容を読んで、上記の要約を更新してください:

{page_content}"""

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": P.DoSummarizeSystem},
            {"role": "user", "content": user_message},
        ],
        response_format=NovelSummary,
    )

    return completion.choices[0].message.parsed  # type: ignore


def create_overview(
    final_summary: NovelSummary, title: str | None = None
) -> NovelOverview:
    """
    最終的な要約から作品全体の概要を生成する

    Args:
        final_summary: 全ページを読み終わった後の NovelSummary
        title: 作品タイトル（わかっている場合）

    Returns:
        作品全体の概要
    """

    user_message = ""

    if title is not None:
        user_message += f"タイトル: {title}\n"

    summary = final_summary.model_dump_json(indent=2, ensure_ascii=False)
    user_message += P.CreateOverview.format(summary=summary)

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": P.CreateOverviewSystem,
            },
            {"role": "user", "content": user_message},
        ],
        response_format=NovelOverview,
    )

    return completion.choices[0].message.parsed  # type: ignore
