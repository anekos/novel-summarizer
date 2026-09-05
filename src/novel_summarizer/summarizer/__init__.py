import os
from collections.abc import Iterator
from functools import cache

from openai import OpenAI

import novel_summarizer.prompts as P
from novel_summarizer.summarizer.cost import Cost, cost_from_usage
from novel_summarizer.types import NovelOverview, NovelSummary, PageChunk


@cache
def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY_FOR_NOVEL_SUMMARIZER"))


SUMMARY_MODEL = "gpt-4o-mini"
OVERVIEW_MODEL = "gpt-4o-mini"


def summarize(
    chunks: list[PageChunk],
    *,
    model: str = SUMMARY_MODEL,
) -> Iterator[tuple[PageChunk, NovelSummary, Cost]]:
    previous_summary: NovelSummary | None = None

    for chunk in chunks:
        summary, cost = summarize_page(chunk.text, previous_summary, model=model)
        yield chunk, summary, cost
        previous_summary = summary


def summarize_page(
    page_content: str,
    previous_summary: NovelSummary | None = None,
    *,
    model: str = SUMMARY_MODEL,
) -> tuple[NovelSummary, Cost]:
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

    completion = get_client().beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": P.DoSummarizeSystem},
            {"role": "user", "content": user_message},
        ],
        response_format=NovelSummary,
    )

    cost = cost_from_usage(completion.usage)
    return completion.choices[0].message.parsed, cost  # type: ignore


def create_overview(
    final_summary: NovelSummary,
    title: str | None = None,
    *,
    model: str = OVERVIEW_MODEL,
) -> tuple[NovelOverview, Cost]:
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

    completion = get_client().beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": P.CreateOverviewSystem,
            },
            {"role": "user", "content": user_message},
        ],
        response_format=NovelOverview,
    )

    cost = cost_from_usage(completion.usage)
    return completion.choices[0].message.parsed, cost  # type: ignore
