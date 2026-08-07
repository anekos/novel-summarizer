import os
from collections.abc import Iterator

from openai import OpenAI

import novel_summarizer.prompts as P
from novel_summarizer.summarizer.cost import Cost, cost_from_usage
from novel_summarizer.summarizer.messages import build_summarize_user_message
from novel_summarizer.types import (
    CharacterNames,
    NovelOverview,
    NovelSummary,
    PageChunk,
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY_FOR_NOVEL_SUMMARIZER"))

SUMMARY_MODEL = "gpt-4o-mini"
OVERVIEW_MODEL = "gpt-4o-mini"
EXTRACT_MODEL = "gpt-5-nano"


def summarize(
    chunks: list[PageChunk],
    *,
    model: str = SUMMARY_MODEL,
    extract_model: str = EXTRACT_MODEL,
) -> Iterator[tuple[PageChunk, NovelSummary, Cost, Cost, list[str]]]:
    previous_summary: NovelSummary | None = None

    for chunk in chunks:
        names, extract_cost = extract_character_names(chunk.text, model=extract_model)
        summary, summary_cost = summarize_page(
            chunk.text,
            previous_summary,
            character_names=names,
            model=model,
        )
        yield chunk, summary, summary_cost, extract_cost, names
        previous_summary = summary


def extract_character_names(
    page_content: str,
    *,
    model: str = EXTRACT_MODEL,
) -> tuple[list[str], Cost]:
    """チャンク本文に登場・言及される人物名を列挙する"""
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": P.ExtractCharacterNamesSystem},
            {
                "role": "user",
                "content": P.ExtractCharacterNames.format(content=page_content),
            },
        ],
        response_format=CharacterNames,
    )

    cost = cost_from_usage(completion.usage)
    parsed = completion.choices[0].message.parsed
    names = parsed.names if parsed is not None else []
    return names, cost


def summarize_page(
    page_content: str,
    previous_summary: NovelSummary | None = None,
    *,
    character_names: list[str] | None = None,
    model: str = SUMMARY_MODEL,
) -> tuple[NovelSummary, Cost]:
    """
    ページを要約する（前回の要約があれば統合する）

    Args:
        page_content: 新しいページの内容
        previous_summary: 前回までの要約（初回は None）
        character_names: このページに登場する人物名（チェックリストとして注入）

    Returns:
        更新された要約
    """
    user_message = build_summarize_user_message(
        page_content, previous_summary, character_names
    )

    completion = client.beta.chat.completions.parse(
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

    completion = client.beta.chat.completions.parse(
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
