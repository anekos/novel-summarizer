from click.testing import CliRunner

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
    assert "Input tokens: 1000" in result.output
    assert "Output tokens: 1000" in result.output
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
