# 登場人物の差分更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 要約コールの登場人物出力を差分化し、Python 側マージで人物の消失を構造的に防ぐ。

**Architecture:** `NovelSummaryUpdate`(characters を new/updates の差分に置換、他フィールドはローリング維持)を要約コールの response_format にし、`summarizer/merge.py` の純粋関数 `apply_update` で `NovelSummary` に反映する。`summarize_page` の戻り値型は不変なので CLI は無変更。

**Tech Stack:** Python 3.11, pydantic, openai structured output, pytest

**Spec:** `docs/superpowers/specs/2026-08-08-character-delta-update-design.md`

## Global Constraints

- 型ヒント必須(mypy strict)。テスト関数にも `-> None`。
- `git commit` の pre-commit hook が ruff / mypy / pytest を全実行する。
- コミットメッセージは短い命令形。
- LLM API を呼ぶ関数のユニットテストは書かない。純粋関数のみテストする。

---

### Task 1: `NovelSummaryUpdate` 型と `apply_update` マージ関数

**Files:**
- Modify: `src/novel_summarizer/types.py`
- Create: `src/novel_summarizer/summarizer/merge.py`
- Test: `tests/summarizer/test_merge.py`

**Interfaces:**
- Produces: `NovelSummaryUpdate`(fields: `new_characters: list[Character]`, `character_updates: list[Character]`, `plot: list[str]`, `settings: Setting`, `key_scenes: list[str]`, `symbols_motifs: list[str]`, `unresolved_mysteries: list[str]`)
- Produces: `apply_update(previous: NovelSummary | None, update: NovelSummaryUpdate) -> NovelSummary` — Task 3 の `summarize_page` が使う。

- [ ] **Step 1: 失敗するテストを書く**(既存人物保持・新規追加・追記マージ・既知名 new / 未知名 updates の各ケース)
- [ ] **Step 2: 実行して失敗を確認**(`uv run pytest tests/summarizer/test_merge.py -v`)
- [ ] **Step 3: types.py に `NovelSummaryUpdate` を、merge.py に `apply_update` と `_merge_character` / `_merge_unique` を実装**
- [ ] **Step 4: テストが通ることを確認**
- [ ] **Step 5: コミット** `Add NovelSummaryUpdate and character merge logic`

### Task 2: プロンプトと message builder の差分対応

**Files:**
- Modify: `src/novel_summarizer/prompts.py`(`DoSummarizeSystem` / `CharacterChecklist` 書き換え)
- Modify: `src/novel_summarizer/summarizer/messages.py`(既知人物一覧セクション追加)
- Test: `tests/summarizer/test_messages.py`(チェックリスト文言更新、既知一覧テスト追加)

**Interfaces:**
- Consumes: `NovelSummary`(既知人物名の導出元)
- Produces: `build_summarize_user_message` の出力に「既知の人物一覧」セクション(previous_summary があるときのみ)

- [ ] **Step 1: テストを更新・追加して失敗を確認**
- [ ] **Step 2: prompts / messages を実装**
- [ ] **Step 3: テストが通ることを確認**
- [ ] **Step 4: コミット** `Update prompts and message builder for delta output`

### Task 3: `summarize_page` の差分受け取りと適用

**Files:**
- Modify: `src/novel_summarizer/summarizer/__init__.py`

**Interfaces:**
- Consumes: `NovelSummaryUpdate`, `apply_update`
- Produces: `summarize_page` の戻り値型は `tuple[NovelSummary, Cost]` のまま(CLI 無変更)

- [ ] **Step 1: `response_format=NovelSummaryUpdate` に変更し、parsed を `apply_update(previous_summary, update)` で反映して返す。parsed が None の場合は例外(既存の `# type: ignore` 相当の扱いをやめ、明示的に処理)**
- [ ] **Step 2: `make test` で全チェック通過を確認**
- [ ] **Step 3: コミット** `Apply character deltas in summarize_page`
