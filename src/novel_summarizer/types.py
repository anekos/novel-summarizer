from pydantic import BaseModel, Field


class Page(BaseModel):
    text: str
    number: int


class PageChunk(BaseModel):
    text: str
    start_page: int
    end_page: int


class Character(BaseModel):
    """登場人物"""

    name: str = Field(description="登場人物の名前(フルネームまたは呼称)")
    aliases: list[str] = Field(
        default_factory=list,
        description="作中で使われる愛称(ニックネーム)や別名。あだ名、通称、旧姓、偽名、肩書きによる呼ばれ方など",
    )
    features: list[str] = Field(
        description="外見、服装、性格、立場、職業などの特徴。些細な描写も含める"
    )
    relationships: list[str] = Field(
        description="他の登場人物との関係性。家族関係、友人関係、上下関係など"
    )
    events: list[str] = Field(
        description="この人物に関連する出来事。行動、発言、体験したことなど"
    )


class CharacterNames(BaseModel):
    """チャンクに登場する人物名の一覧"""

    names: list[str] = Field(
        description=(
            "本文に登場・言及される人物の名前。端役や一度きりの言及も含める。"
            "名前が不明な人物は呼称(例: 駅員、老婆)で表す"
        )
    )


class Setting(BaseModel):
    """舞台設定"""

    time_period: str = Field(description="時代背景(例: 明治時代、現代、2024年など)")
    locations: list[str] = Field(description="物語の舞台となる場所")


class NovelSummary(BaseModel):
    """小説要約"""

    characters: list[Character] = Field(
        description="登場人物の一覧。些細な登場でも漏らさず全て含める"
    )
    plot: list[str] = Field(description="あらすじ。物語の出来事を時系列順に並べる")
    settings: Setting = Field(description="時代設定と場所。物語の舞台となる時代や地域")
    key_scenes: list[str] = Field(
        description="物語の転換点となる重要なシーン。クライマックスや印象的な場面"
    )
    symbols_motifs: list[str] = Field(
        description="繰り返し登場する象徴的な要素やモチーフ(小道具、色、言葉など)"
    )
    unresolved_mysteries: list[str] = Field(
        description="まだ明かされていない謎や伏線。読み進める中で解決されたら削除される"
    )


class NovelSummaryUpdate(BaseModel):
    """1チャンク分の要約更新(登場人物は差分のみ)"""

    new_characters: list[Character] = Field(
        description=(
            "このチャンクで初めて登場した人物。"
            "既知の人物一覧にある名前は含めない。些細な登場でも漏らさず含める"
        )
    )
    character_updates: list[Character] = Field(
        description=(
            "既知の人物についてこのチャンクで新たに判明した情報。"
            "aliases/features/relationships/events には新規判明分のみを入れる"
        )
    )
    plot: list[str] = Field(
        description="あらすじ。既存と新規を統合し、物語の出来事を時系列順に並べる"
    )
    settings: Setting = Field(description="時代設定と場所。物語の舞台となる時代や地域")
    key_scenes: list[str] = Field(
        description="物語の転換点となる重要なシーン。クライマックスや印象的な場面"
    )
    symbols_motifs: list[str] = Field(
        description="繰り返し登場する象徴的な要素やモチーフ(小道具、色、言葉など)"
    )
    unresolved_mysteries: list[str] = Field(
        description="まだ明かされていない謎や伏線。読み進める中で解決されたら削除される"
    )


class NovelOverview(BaseModel):
    """作品全体の概要"""

    title: str = Field(description="作品のタイトル")
    genre: list[str] = Field(
        description="ジャンル(例: 純文学、恋愛小説、ミステリーなど)"
    )
    themes: list[str] = Field(
        description="作品の主要なテーマ(例: 孤独、友情、死生観など)"
    )
    summary: str = Field(description="作品全体の簡潔な要約 (200-300文字程度)")
    main_characters: list[str] = Field(description="主要登場人物の名前のリスト")
    atmosphere: str = Field(description="作品全体の雰囲気や文体の特徴")
