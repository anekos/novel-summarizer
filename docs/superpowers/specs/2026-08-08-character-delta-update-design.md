# 登場人物の差分更新 — 設計

日付: 2026-08-08

## 問題

人物名列挙パス(前設計)で抽出漏れは改善したが、今度は一度記録された登場人物が
後続チャンクの要約で消える事象が確認された。

原因: 要約コールがチャンクごとに `characters` の全リストを再出力する構造のため、
モデルが再掲し忘れた人物は永久に失われる。チェックリストは「そのチャンクに登場する
人物」しか守らないので、過去チャンクのみに登場した人物は保護されない。

## 方針

登場人物をモデルに再出力させず、差分だけを出させて Python 側でマージする。
一度登録された人物はコードの構造上消えなくなる。

- 出力スキーマの `characters` を廃止し、`new_characters`(初登場)と
  `character_updates`(既存人物への追記。新規判明分のみ)に置き換える。
- Python 側で名前をキーに dict 管理し、リスト項目は重複を除いて append する。
- 呼称ゆれによる二重登録を防ぐため、既知の人物名一覧をプロンプトに明示し
  「一覧にある名前は new_characters に入れない」と指示する。
- `plot` / `settings` / `key_scenes` / `symbols_motifs` / `unresolved_mysteries` は
  従来通りローリング(全出力)のまま。同じ症状が出たら同じ手当てをする。

## 変更内容

### `types.py`

```python
class NovelSummaryUpdate(BaseModel):
    """1チャンク分の要約更新(登場人物は差分)"""

    new_characters: list[Character]      # 既知一覧にいない初登場の人物
    character_updates: list[Character]   # 既知人物への追記(新規判明分のみ)
    plot: list[str]                      # 以下は従来通り全体を出力
    settings: Setting
    key_scenes: list[str]
    symbols_motifs: list[str]
    unresolved_mysteries: list[str]
```

`NovelSummary` は最終成果物・ローカル状態として存続する。

### `summarizer/merge.py`(新規)

純粋関数のみ:

- `apply_update(previous: NovelSummary | None, update: NovelSummaryUpdate) -> NovelSummary`
  - 既存人物は必ず保持。`new_characters` / `character_updates` を名前キーでマージ。
  - 既知名が `new_characters` に来た場合も上書きせずマージする。
  - 未知名が `character_updates` に来た場合は新規人物として追加する。
  - features / relationships / events は順序を保って重複排除 append。

### `prompts.py`

- `DoSummarizeSystem` を差分出力の指示に書き換える。
- `CharacterChecklist` を new_characters / character_updates の語彙に合わせて書き換える。

### `summarizer/messages.py`

- 前回要約がある場合、既知の人物名一覧セクションを user message に追加する。

### `summarizer/__init__.py`

- `summarize_page` の `response_format` を `NovelSummaryUpdate` に変更し、
  受け取った差分を `apply_update` で `NovelSummary` に反映して返す。
  戻り値の型は変わらないため CLI は無変更。

## テスト

- `merge.py`: 既存人物が update に現れなくても保持されること(核心)、新規追加、
  追記マージ(重複排除・順序維持)、既知名の new_characters・未知名の
  character_updates の扱い。
- `messages.py`: 既知人物一覧セクションの有無。チェックリスト文言の更新に伴う
  既存テストの修正。

## 効果

- 人物の消失が構造的に不可能になる。
- 出力トークンが全リスト再出力から差分のみになり、コスト・時間はむしろ減る。

## 懸念と対応

- 人物ごとの features/events が単調増加して雑多になる可能性 → まず様子見。
  必要になったら最終段に人物整理パスを追加する(本設計のスコープ外)。
