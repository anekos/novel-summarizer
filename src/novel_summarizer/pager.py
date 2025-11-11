import re

from novel_summarizer.types import Page


def pagenize(text: str, page_header: re.Pattern) -> list[Page]:
    lines = text.splitlines()

    result: list[Page] = []
    buffer: list[str] = []
    last_page_number: int | None = None

    for line in lines:
        if m := page_header.match(line):
            page_number = int(m.group(1))
            if last_page_number is not None:
                result.append(
                    Page(
                        text="\n".join(buffer).strip(),
                        number=last_page_number,
                    )
                )
                buffer.clear()
            last_page_number = page_number
            continue

        buffer.append(line)

    assert last_page_number is not None
    result.append(
        Page(
            text="\n".join(buffer).strip(),
            number=last_page_number,
        )
    )

    return result
