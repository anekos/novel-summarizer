from types import SimpleNamespace

from novel_summarizer.summarizer.cost import Cost, cost_from_usage


def test_cost_from_usage_handles_object_payload() -> None:
    usage = SimpleNamespace(
        input_tokens=1_000,
        output_tokens=500,
        input_characters=2_000,
        output_characters=1_000,
    )

    cost = cost_from_usage(usage)

    assert cost.input_tokens == 1_000
    assert cost.output_tokens == 500
    # ensure price computation works without raising and uses million-token units
    assert cost.price("gpt-4o-mini") > 0


def test_cost_from_usage_fallbacks_to_prompt_completion_keys() -> None:
    usage = {"prompt_tokens": 2_000, "completion_tokens": 1_000}

    cost = cost_from_usage(usage)

    assert cost.input_tokens == 2_000
    assert cost.output_tokens == 1_000


def test_cost_addition_sums_fields() -> None:
    total = Cost(input_tokens=10, output_tokens=5) + Cost(
        input_tokens=2, output_tokens=3
    )

    assert total.input_tokens == 12
    assert total.output_tokens == 8
    assert total.total_tokens == 20


def test_tokens_per_character_handles_zero_division() -> None:
    empty_cost = Cost()
    assert empty_cost.tokens_per_character() is None

    cost = Cost(
        input_tokens=100,
        output_tokens=50,
        input_characters=75,
        output_characters=25,
    )
    assert cost.tokens_per_character() == 150 / 100
