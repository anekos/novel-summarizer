from novel_summarizer.types import Page, PageChunk


def chunked(pages: list[Page], chunk_size: int, overlap: int) -> list[PageChunk]:
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
        )
    if overlap < 0:
        raise ValueError(f"overlap ({overlap}) must be non-negative")
    if chunk_size <= 0:
        raise ValueError(f"chunk_size ({chunk_size}) must be positive")

    page_chunks = []
    step = chunk_size - overlap

    for i in range(0, len(pages), step):
        _pages = pages[i : i + chunk_size]

        text = "\n".join(p.text for p in _pages)

        chunk = PageChunk(
            text=text,
            start_page=_pages[0].number,
            end_page=_pages[-1].number,
        )

        page_chunks.append(chunk)

    return page_chunks
