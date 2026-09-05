# 人物名列挙パス Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** チャンクごとに人物名だけを列挙する軽量 LLM コールを要約コールの前段に追加し、その結果をチェックリストとして要約コールに注入して人物の抽出漏れを減らす。

**Architecture:** `summarize()` が各チャンクで「列挙コール(`extract_character_names`) → 要約コール(`summarize_page`)」の 2 段階を実行する。列挙は本文のみを入力とし名前リストのみを出力する。message 組み立ては純粋関数 `build_summarize_user_message` に切り出す。列挙モデルは CLI の `--extract-model`(デフォルト `gpt-5-nano`)で指定でき、コストは Extraction バケットとして別集計する。

**Tech Stack:** Python 3.11, pydantic, openai (`client.beta.chat.completions.parse` の structured output), click, pytest

**Spec:** `docs/superpowers/specs/2026-08-08-character-name-extraction-pass-design.md`

## Global Constraints

- 型ヒント必須(mypy `disallow_untyped_defs=true`)。テスト関数にも `-> None` を付ける。
- `git commit` すると pre-commit hook が ruff / mypy / pytest を全て実行する(= コミット成功が検証を兼ねる)。
- コミットメッセージは短い命令形(例: "Add a command")。
- LLM API を実際に呼ぶ関数のユニットテストは書かない(既存方針)。純粋関数のみテストする。
- テストは `tests/summarizer/` のようにモジュール構成をミラーする。

---

### Task 1: message 組み立ての純粋関数 `build_summarize_user_message`

**Files:**
- Create: `src/novel_summarizer/summarizer/messages.py`
- Modify: `src/novel_summarizer/prompts.py`(`CharacterChecklist` を追加)
- Test: `tests/summarizer/test_messages.py`

**Interfaces:**
- Consumes: `novel_summarizer.types.NovelSummary`, `novel_summarizer.prompts`
- Produces: `build_summarize_user_message(page_content: str, previous_summary: NovelSummary | None = None, character_names: list[str] | None = None) -> str` — Task 2 の `summarize_page` がこれを呼ぶ。

- [ ] **Step 1: 失敗するテストを書く**

`tests/summarizer/test_messages.py` を作成(`tests/summarizer/` に `__init__.py` は不要。既存の `tests/` 直下にもない):

```python
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
    for names in (None, []):
        message = build_summarize_user_message("本文", None, names)
        assert "登場していることが確認" not in message
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest tests/summarizer/test_messages.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'novel_summarizer.summarizer.messages'`)

- [ ] **Step 3: プロンプトと実装を書く**

`src/novel_summarizer/prompts.py` の末尾に追加:

```python
CharacterChecklist = """以下の人物は本文に登場していることが確認されています。全員を必ず characters に含めてください:

{names}"""
```

`src/novel_summarizer/summarizer/messages.py` を作成:

```python
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
        message = f"""以下は前回までの要約です:

{summary_json}

---

以下の新しい内容を読んで、上記の要約を更新してください:

{page_content}"""

    if character_names:
        names = "\n".join(f"- {name}" for name in character_names)
        message += "\n\n---\n\n" + P.CharacterChecklist.format(names=names)

    return message
```

- [ ] **Step 4: テストが通ることを確認**

Run: `uv run pytest tests/summarizer/test_messages.py -v`
Expected: 4 件 PASS

- [ ] **Step 5: コミット**

```bash
git add src/novel_summarizer/summarizer/messages.py src/novel_summarizer/prompts.py tests/summarizer/test_messages.py
git commit -m "Add summarize message builder with character checklist"
```

(pre-commit hook が ruff / mypy / pytest を実行する。失敗したら直してから再コミット)

---

### Task 2: 列挙コール `extract_character_names` と `summarize` の 2 段階化

**Files:**
- Modify: `src/novel_summarizer/types.py`(`CharacterNames` を追加)
- Modify: `src/novel_summarizer/prompts.py`(列挙用プロンプトを追加)
- Modify: `src/novel_summarizer/summarizer/__init__.py`

**Interfaces:**
- Consumes: Task 1 の `build_summarize_user_message`
- Produces:
  - `EXTRACT_MODEL: str = "gpt-5-nano"`
  - `extract_character_names(page_content: str, *, model: str = EXTRACT_MODEL) -> tuple[list[str], Cost]`
  - `summarize_page(page_content, previous_summary=None, *, character_names: list[str] | None = None, model: str = SUMMARY_MODEL) -> tuple[NovelSummary, Cost]`
  - `summarize(chunks, *, model: str = SUMMARY_MODEL, extract_model: str = EXTRACT_MODEL) -> Iterator[tuple[PageChunk, NovelSummary, Cost, Cost]]` — 4 要素目が列挙コスト。Task 3 の CLI がこれを消費する。

LLM API を呼ぶコードなのでユニットテストは書かない。検証はコミット時の mypy / ruff と、Task 3 完了後の実 CLI 実行で行う。

- [ ] **Step 1: `CharacterNames` 型を追加**

`src/novel_summarizer/types.py` の `Character` クラスの後に追加:

```python
class CharacterNames(BaseModel):
    """チャンクに登場する人物名の一覧"""

    names: list[str] = Field(
        description=(
            "本文に登場・言及される人物の名前。端役や一度きりの言及も含める。"
            "名前が不明な人物は呼称(例: 駅員、老婆)で表す"
        )
    )
```

- [ ] **Step 2: 列挙用プロンプトを追加**

`src/novel_summarizer/prompts.py` の末尾に追加:

```python
ExtractCharacterNamesSystem = """あなたは小説から登場人物を抽出する専門家です。
- 本文に登場・言及される人物を全員、漏らさず列挙する
- 端役や一度きりの言及も含める
- 名前が不明な人物は呼称(例: 駅員、老婆)で表す
- 同一人物の呼称ゆれは最も代表的な名前ひとつにまとめる"""

ExtractCharacterNames = """以下の本文に登場・言及される人物を全員列挙してください:

{content}"""
```

- [ ] **Step 3: `summarizer/__init__.py` を書き換える**

import に `CharacterNames` と `build_summarize_user_message` を足し、`EXTRACT_MODEL` 定数と `extract_character_names` を追加、`summarize` / `summarize_page` を差し替える:

```python
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
) -> Iterator[tuple[PageChunk, NovelSummary, Cost, Cost]]:
    previous_summary: NovelSummary | None = None

    for chunk in chunks:
        names, extract_cost = extract_character_names(chunk.text, model=extract_model)
        summary, summary_cost = summarize_page(
            chunk.text,
            previous_summary,
            character_names=names,
            model=model,
        )
        yield chunk, summary, summary_cost, extract_cost
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
    ページを要約する(前回の要約があれば統合する)

    Args:
        page_content: 新しいページの内容
        previous_summary: 前回までの要約(初回は None)
        character_names: このページに登場する人物名(チェックリストとして注入)

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
```

`create_overview` は変更しない。`summarize_page` 内の既存の user_message 組み立てコードは削除する(builder に置き換え)。

- [ ] **Step 4: 型チェックとテストが通ることを確認**

Run: `make test`
Expected: pre-commit(ruff / mypy)と pytest が全て PASS

- [ ] **Step 5: コミット**

```bash
git add src/novel_summarizer/types.py src/novel_summarizer/prompts.py src/novel_summarizer/summarizer/__init__.py
git commit -m "Add character name extraction pass before summarization"
```

---

### Task 3: CLI オプション `--extract-model` と Extraction コスト集計

**Files:**
- Modify: `src/novel_summarizer/__init__.py`
- Test: `tests/test_cli_cost.py`(`_log_api_costs` のテストを追加)

**Interfaces:**
- Consumes: Task 2 の `summarize(..., extract_model=...)`(4-tuple を yield)と `EXTRACT_MODEL`
- Produces: CLI オプション `--extract-model`、4 区分のコスト表示(Extraction / Summaries / Overview / Combined)

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_cli_cost.py` の末尾に追加:

```python
def test_log_api_costs_includes_extraction_bucket(
    capsys: CaptureFixture[str],
) -> None:
    from novel_summarizer import _log_api_costs
    from novel_summarizer.logger import WithFileLogger

    summary_cost = Cost(input_tokens=1_000, output_tokens=100)
    overview_cost = Cost(input_tokens=500, output_tokens=50)
    extract_cost = Cost(input_tokens=2_000, output_tokens=20)

    with WithFileLogger(None) as logger:
        _log_api_costs(
            logger,
            summary_cost,
            overview_cost,
            extract_cost,
            summary_model="gpt-4o-mini",
            overview_model="gpt-4o-mini",
            extract_model="gpt-5-nano",
        )

    out = capsys.readouterr().out
    extraction_price = extract_cost.price("gpt-5-nano")
    assert f"Extraction: ${extraction_price:.4f} (model gpt-5-nano)" in out

    total = (
        summary_cost.price("gpt-4o-mini")
        + overview_cost.price("gpt-4o-mini")
        + extraction_price
    )
    assert f"Total: ${total:.4f}" in out
```

ファイル先頭の import に追加:

```python
from pytest import CaptureFixture
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest tests/test_cli_cost.py -v`
Expected: 新テストが FAIL(`_log_api_costs` は現状 `extract_cost` 引数を受け取らない → `TypeError`)

- [ ] **Step 3: CLI を実装する**

`src/novel_summarizer/__init__.py` を修正する。

import を更新:

```python
from novel_summarizer.summarizer import (
    EXTRACT_MODEL,
    OVERVIEW_MODEL,
    SUMMARY_MODEL,
    create_overview,
    summarize,
)
```

`command_summarize` にオプションを追加(`--overview-model` の直後):

```python
@click.option(
    "--extract-model",
    type=str,
    required=False,
    default=EXTRACT_MODEL,
    show_default=True,
    help="OpenAI model ID used for character name extraction.",
)
```

関数シグネチャに `extract_model: str` を追加:

```python
def command_summarize(
    source_text: Path,
    page_header: str,
    chunk_size: int,
    overlap: int,
    dest: Path | None,
    summary_model: str,
    overview_model: str,
    extract_model: str,
) -> None:
```

コストバケットの初期化に追加:

```python
    summary_usage = Cost()
    overview_usage = Cost()
    extract_usage = Cost()
```

要約ループを 4-tuple に変更:

```python
        for chunk, summary, cost, extract_cost in summarize(
            page_chunks, model=summary_model, extract_model=extract_model
        ):
            md = summary_to_markdown(summary)
            final_summary = summary
            summary_usage = summary_usage + cost
            extract_usage = extract_usage + extract_cost
```

(ループ内の残りは変更なし)

`_log_api_costs` の呼び出し 2 箇所(early return 側と正常系側)を更新:

```python
            _log_api_costs(
                logger,
                summary_usage,
                overview_usage,
                extract_usage,
                summary_model=summary_model,
                overview_model=overview_model,
                extract_model=extract_model,
            )
```

`_log_api_costs` 本体を 4 区分に拡張:

```python
def _log_api_costs(
    logger: WithFileLogger,
    summary_cost: Cost,
    overview_cost: Cost,
    extract_cost: Cost,
    *,
    summary_model: str,
    overview_model: str,
    extract_model: str,
) -> None:
    summary_price = _price_for_model(summary_cost, summary_model)
    overview_price = _price_for_model(overview_cost, overview_model)
    extract_price = _price_for_model(extract_cost, extract_model)
    total_usage = summary_cost + overview_cost + extract_cost

    logger.log("=== API Cost Summary ===")
    total_price = _known_total([summary_price, overview_price, extract_price])
    missing_models = [
        model
        for price, model in (
            (summary_price, summary_model),
            (overview_price, overview_model),
            (extract_price, extract_model),
        )
        if price is None
    ]
    if missing_models:
        logger.log(
            f"Total: at least ${total_price:.4f} "
            f"(missing pricing for: {', '.join(missing_models)})"
        )
    else:
        logger.log(f"Total: ${total_price:.4f}")

    _log_usage_detail(
        logger, "Extraction", extract_model, extract_price, extract_cost
    )
    _log_usage_detail(logger, "Summaries", summary_model, summary_price, summary_cost)
    _log_usage_detail(logger, "Overview", overview_model, overview_price, overview_cost)
    _log_usage_detail(
        logger,
        "Combined",
        "aggregate",
        total_price if not missing_models else None,
        total_usage,
    )
```

- [ ] **Step 4: テストが通ることを確認**

Run: `make test`
Expected: 全て PASS

- [ ] **Step 5: コミット**

```bash
git add src/novel_summarizer/__init__.py tests/test_cli_cost.py
git commit -m "Add --extract-model option and extraction cost bucket"
```

---

## 動作確認(実 API)

実装完了後、小さめの原稿で実際に動くことを確認する(API キーが必要):

```bash
uv run novel-summarizer summarize <manuscript.txt> '<page-header-regex>' --dest /tmp/claude-1000/-home-anekos--herdr-worktrees-novel-summarizer-worktree-green-cloud-bb0b/dc139ad7-c893-4d65-ab8c-0d22ed186e60/scratchpad/summary-check --chunk-size 10
```

- ログに `Extraction: $... (model gpt-5-nano)` の行が出ること
- 出力 Markdown の登場人物リストが以前より充実していること(手動確認)
