import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from typing import Literal

from openai import Omit, OpenAI, omit

import novel_summarizer.prompts as P
from novel_summarizer.summarizer.cost import Cost, cost_from_usage
from novel_summarizer.summarizer.merge import apply_update
from novel_summarizer.summarizer.messages import build_summarize_user_message
from novel_summarizer.types import (
    CharacterNames,
    NovelOverview,
    NovelSummary,
    NovelSummaryUpdate,
    PageChunk,
)


@cache
def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY_FOR_NOVEL_SUMMARIZER"))


SUMMARY_MODEL = "gpt-4o-mini"
OVERVIEW_MODEL = "gpt-4o-mini"
EXTRACT_MODEL = "gpt-5-nano"
EXTRACT_CONCURRENCY = 4


def summarize(
    chunks: list[PageChunk],
    *,
    model: str = SUMMARY_MODEL,
    extract_model: str = EXTRACT_MODEL,
    on_extract_start: Callable[[PageChunk], None] | None = None,
    on_extract_done: Callable[[PageChunk, list[str]], None] | None = None,
) -> Iterator[tuple[PageChunk, NovelSummary, Cost, Cost, list[str]]]:
    previous_summary: NovelSummary | None = None

    def extract(chunk: PageChunk) -> tuple[list[str], Cost]:
        if on_extract_start is not None:
            on_extract_start(chunk)
        names, cost = extract_character_names(chunk.text, model=extract_model)
        if on_extract_done is not None:
            on_extract_done(chunk, names)
        return names, cost

    # 列挙は前回要約に依存しないため、要約ループと並行して先行実行できる
    with ThreadPoolExecutor(max_workers=EXTRACT_CONCURRENCY) as executor:
        for chunk, (names, extract_cost) in zip(
            chunks, executor.map(extract, chunks), strict=True
        ):
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
    # reasoning_effort は非 reasoning モデルに渡すと API エラーになる
    effort: Literal["minimal"] | Omit = (
        "minimal" if model.startswith(("gpt-5", "o1", "o3", "o4")) else omit
    )
    completion = get_client().beta.chat.completions.parse(
        model=model,
        reasoning_effort=effort,
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

    completion = get_client().beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": P.DoSummarizeSystem},
            {"role": "user", "content": user_message},
        ],
        response_format=NovelSummaryUpdate,
    )

    cost = cost_from_usage(completion.usage)
    update = completion.choices[0].message.parsed
    if update is None:
        raise RuntimeError("Structured output parse returned no content")
    return apply_update(previous_summary, update), cost


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
