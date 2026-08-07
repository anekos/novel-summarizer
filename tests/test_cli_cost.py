from click.testing import CliRunner
from pytest import CaptureFixture

from novel_summarizer import main
from novel_summarizer.summarizer.cost import Cost


def test_cost_command_calculates_total_price() -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "cost",
            "--model",
            "gpt-4o-mini",
            "--input-tokens",
            "1000",
            "--output-tokens",
            "1000",
        ],
    )

    assert result.exit_code == 0
    assert "Model: gpt-4o-mini" in result.output
    assert "Input tokens: 1,000" in result.output
    assert "Output tokens: 1,000" in result.output
    expected = Cost(input_tokens=1000, output_tokens=1000).price("gpt-4o-mini")
    assert f"Total price: ${expected:.4f}" in result.output


def test_cost_command_handles_unknown_model() -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "cost",
            "--model",
            "does-not-exist",
            "--input-tokens",
            "1",
            "--output-tokens",
            "1",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown model" in result.output


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
