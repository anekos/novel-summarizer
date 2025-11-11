import re
from pathlib import Path

import click

TypePath = click.types.Path(path_type=Path)


@click.group(context_settings={"show_default": True})
@click.pass_context
def main(ctx: click.Context) -> None:
    # ctx.obj = App()
    pass


@main.command(name="summarize")
@click.argument("source-text", type=TypePath, required=True)
@click.argument("page-header", type=str, required=True)
@click.option("--dest", type=TypePath, required=False, help="The person to greet.")
@click.option(
    "--chunk-size", type=int, required=False, help="Page chunks size", default=50
)
@click.option("--overlap", type=int, required=False, help="Overlap pages", default=5)
def command_summarize(
    source_text: Path,
    page_header: str,
    chunk_size: int,
    overlap: int,
    dest: Path | None,
) -> None:
    from novel_summarizer.chunker import chunked
    from novel_summarizer.markdown_writer import (
        overview_to_markdown,
        summary_to_markdown,
    )
    from novel_summarizer.pager import pagenize
    from novel_summarizer.summarizer import create_overview, summarize
    from novel_summarizer.types import NovelSummary

    text = source_text.read_text(encoding="utf-8")
    title = source_text.stem
    pages = pagenize(text, re.compile(page_header))
    page_chunks = chunked(pages, chunk_size=chunk_size, overlap=overlap)

    print(f"=== Summarization for {title} ===")

    for chunk in [*page_chunks[0:2], *page_chunks[-2:]]:
        print(f"# Pages {chunk.start_page} to {chunk.end_page} ####################")
        print(chunk.text[0:100])
        print("...")
        print(chunk.text[-100:])

    print("\n\n=== Summary ===\n")

    if dest is not None:
        dest.mkdir(parents=True, exist_ok=True)

    final_summary: None | NovelSummary = None

    for chunk, summary in summarize(page_chunks):
        md = summary_to_markdown(summary)
        final_summary = summary
        print(
            f"# Pages {chunk.start_page} to {chunk.end_page} Summary ####################"
        )
        print(md)
        if dest is not None:
            filename = f"{chunk.start_page:04d}-{chunk.end_page:04d}.md"
            md = summary_to_markdown(summary)
            (dest / filename).write_text(md, encoding="utf-8")

    if final_summary is None:
        return

    overview = create_overview(final_summary, title=title)
    md = overview_to_markdown(overview)
    print("# Overview ####################")
    print(md)
    if dest is not None:
        (dest / "overview.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
