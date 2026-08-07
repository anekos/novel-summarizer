import re
import time
from pathlib import Path

import click

from novel_summarizer.logger import WithFileLogger
from novel_summarizer.summarizer import (
    EXTRACT_MODEL,
    OVERVIEW_MODEL,
    SUMMARY_MODEL,
    create_overview,
    summarize,
)
from novel_summarizer.summarizer.cost import Cost

TypePath = click.types.Path(path_type=Path)


@click.group(context_settings={"show_default": True})
@click.pass_context
def main(ctx: click.Context) -> None:
    # ctx.obj = App()
    pass


@main.command(name="cost")
@click.option(
    "--model",
    type=str,
    required=True,
    help="OpenAI model ID to price against.",
)
@click.option(
    "--input-tokens",
    type=int,
    required=False,
    default=0,
    show_default=True,
    help="Number of prompt/input tokens.",
)
@click.option(
    "--output-tokens",
    type=int,
    required=False,
    default=0,
    show_default=True,
    help="Number of completion/output tokens.",
)
def command_cost(model: str, input_tokens: int, output_tokens: int) -> None:
    """Calculate cost for a single API call."""
    if input_tokens < 0 or output_tokens < 0:
        raise click.ClickException("Token counts must be non-negative integers.")

    usage = Cost(input_tokens=input_tokens, output_tokens=output_tokens)

    try:
        price = usage.price(model)
    except KeyError as exc:
        raise click.ClickException(f"Unknown model '{model}'.") from exc

    click.echo(f"Model: {model}")
    click.echo(f"Input tokens: {input_tokens:,}")
    click.echo(f"Output tokens: {output_tokens:,}")
    click.echo(f"Total price: ${price:.4f}")


@main.command(name="summarize")
@click.argument("source-text", type=TypePath, required=True)
@click.argument("page-header", type=str, required=True)
@click.option("--dest", type=TypePath, required=False, help="The person to greet.")
@click.option(
    "--chunk-size", type=int, required=False, help="Page chunks size", default=50
)
@click.option("--overlap", type=int, required=False, help="Overlap pages", default=5)
@click.option(
    "--summary-model",
    type=str,
    required=False,
    default=SUMMARY_MODEL,
    show_default=True,
    help="OpenAI model ID used for individual chunk summaries.",
)
@click.option(
    "--overview-model",
    type=str,
    required=False,
    default=OVERVIEW_MODEL,
    show_default=True,
    help="OpenAI model ID used for the final overview.",
)
@click.option(
    "--extract-model",
    type=str,
    required=False,
    default=EXTRACT_MODEL,
    show_default=True,
    help="OpenAI model ID used for character name extraction.",
)
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
    from novel_summarizer.chunker import chunked
    from novel_summarizer.markdown_writer import (
        overview_to_markdown,
        summary_to_markdown,
    )
    from novel_summarizer.pager import pagenize
    from novel_summarizer.types import NovelSummary

    start_time = time.perf_counter()

    text = source_text.read_text(encoding="utf-8")
    title = source_text.stem
    pages = pagenize(text, re.compile(page_header))
    page_chunks = chunked(pages, chunk_size=chunk_size, overlap=overlap)

    if dest is not None:
        dest.mkdir(parents=True, exist_ok=True)
    log_path = dest / "log.txt" if dest is not None else None

    summary_usage = Cost()
    overview_usage = Cost()
    extract_usage = Cost()

    with WithFileLogger(log_path) as logger:
        logger.log(f"=== Summarization for {title} ===")

        for chunk in [*page_chunks[0:2], *page_chunks[-2:]]:
            logger.log(
                f"# Pages {chunk.start_page} to {chunk.end_page} ####################"
            )
            logger.log(chunk.text[0:100])
            logger.log("...")
            logger.log(chunk.text[-100:])

        logger.log("\n\n=== Summary ===\n")

        final_summary: None | NovelSummary = None

        for chunk, summary, cost, extract_cost, extracted_names in summarize(
            page_chunks, model=summary_model, extract_model=extract_model
        ):
            md = summary_to_markdown(summary)
            final_summary = summary
            summary_usage = summary_usage + cost
            extract_usage = extract_usage + extract_cost
            logger.log(
                f"# Pages {chunk.start_page} to {chunk.end_page} Summary ####################"
            )
            logger.log(
                f"Extracted characters ({len(extracted_names)}): "
                + ", ".join(extracted_names)
            )
            logger.log(md)
            if dest is not None:
                filename = f"{chunk.start_page:04d}-{chunk.end_page:04d}.md"
                md = summary_to_markdown(summary)
                (dest / filename).write_text(md, encoding="utf-8")

                json_filename = f"{chunk.start_page:04d}-{chunk.end_page:04d}.json"
                json_payload = summary.model_dump_json(indent=2, ensure_ascii=False)
                (dest / json_filename).write_text(json_payload, encoding="utf-8")

        if final_summary is None:
            _log_total_time(logger, start_time)
            _log_api_costs(
                logger,
                summary_usage,
                overview_usage,
                extract_usage,
                summary_model=summary_model,
                overview_model=overview_model,
                extract_model=extract_model,
            )
            return

        overview, overview_cost = create_overview(
            final_summary, title=title, model=overview_model
        )
        md = overview_to_markdown(overview)
        overview_usage = overview_usage + overview_cost
        logger.log("# Overview ####################")
        logger.log(md)
        if dest is not None:
            (dest / "overview.md").write_text(md, encoding="utf-8")
            overview_json = overview.model_dump_json(indent=2, ensure_ascii=False)
            (dest / "overview.json").write_text(overview_json, encoding="utf-8")

        _log_total_time(logger, start_time)
        _log_api_costs(
            logger,
            summary_usage,
            overview_usage,
            extract_usage,
            summary_model=summary_model,
            overview_model=overview_model,
            extract_model=extract_model,
        )


if __name__ == "__main__":
    main()


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

    _log_usage_detail(logger, "Extraction", extract_model, extract_price, extract_cost)
    _log_usage_detail(logger, "Summaries", summary_model, summary_price, summary_cost)
    _log_usage_detail(logger, "Overview", overview_model, overview_price, overview_cost)
    _log_usage_detail(
        logger,
        "Combined",
        "aggregate",
        total_price if not missing_models else None,
        total_usage,
    )


def _log_usage_detail(
    logger: WithFileLogger,
    label: str,
    model: str,
    price: float | None,
    cost: Cost,
) -> None:
    if price is None:
        logger.log(f"{label}: price unknown (model {model})")
    else:
        logger.log(f"{label}: ${price:.4f} (model {model})")
    logger.log(
        f"    tokens total {cost.total_tokens:,} "
        f"(input {cost.input_tokens:,}, output {cost.output_tokens:,})"
    )


def _price_for_model(cost: Cost, model: str) -> float | None:
    try:
        return cost.price(model)
    except KeyError:
        return None


def _known_total(prices: list[float | None]) -> float:
    return sum(price for price in prices if price is not None)


def _log_total_time(logger: WithFileLogger, start_time: float) -> None:
    elapsed_minutes = (time.perf_counter() - start_time) / 60
    logger.log(f"=== Total Time === {elapsed_minutes:.2f}分")
