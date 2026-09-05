from novel_summarizer.types import NovelOverview, NovelSummary


def summary_to_markdown(summary: NovelSummary) -> str:
    """
    NovelSummary を Markdown 形式に変換する

    Args:
        summary: 小説要約オブジェクト

    Returns:
        Markdown 形式の文字列
    """
    lines = []

    lines.append("# 登場人物")
    for char in summary.characters:
        lines.append(f"- {char.name}")

        if char.aliases:
            lines.append("    - 愛称・別名")
            for alias in char.aliases:
                lines.append(f"        - {alias}")

        if char.features:
            lines.append("    - 特徴")
            for feature in char.features:
                lines.append(f"        - {feature}")

        if char.relationships:
            lines.append("    - 関係")
            for rel in char.relationships:
                lines.append(f"        - {rel}")

        if char.events:
            lines.append("    - 出来事")
            for event in char.events:
                lines.append(f"        - {event}")

    lines.append("\n# あらすじ")
    for event in summary.plot:
        lines.append(f"- {event}")

    return "\n".join(lines)


def overview_to_markdown(overview: NovelOverview) -> str:
    """
    NovelOverview を Markdown 形式に変換する

    Args:
        overview: 作品概要オブジェクト

    Returns:
        Markdown 形式の文字列
    """
    lines = []

    lines.append(f"# {overview.title}")
    lines.append("")

    lines.append("## ジャンル")
    for genre in overview.genre:
        lines.append(f"- {genre}")
    lines.append("")

    lines.append("## 主要テーマ")
    for theme in overview.themes:
        lines.append(f"- {theme}")
    lines.append("")

    lines.append("## 作品概要")
    lines.append(overview.summary)
    lines.append("")

    lines.append("## 主要登場人物")
    for char in overview.main_characters:
        lines.append(f"- {char}")
    lines.append("")

    lines.append("## 雰囲気・特徴")
    lines.append(overview.atmosphere)

    return "\n".join(lines)
