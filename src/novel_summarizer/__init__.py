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
def command_summarize(source_text: Path, page_header: str, dest: Path | None) -> None:
    from novel_summarizer.chunker import chunked
    from novel_summarizer.pager import pagenize

    text = source_text.read_text(encoding="utf-8")
    pages = pagenize(text, re.compile(page_header))
    page_chunks = chunked(pages, chunk_size=10, overlap=2)

    # for n, page in enumerate(pages[0:5]):
    #     print(f"# {n} ############################################")
    #     print(page)
    print(len(pages))

    for chunk in [*page_chunks[0:2], *page_chunks[-2:]]:
        print(f"# Pages {chunk.start_page} to {chunk.end_page} ####################")
        print(chunk.text[0:100])
        print("...")
        print(chunk.text[-100:])


if __name__ == "__main__":
    main()
