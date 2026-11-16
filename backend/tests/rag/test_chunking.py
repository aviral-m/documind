import pytest

from app.rag.chunking import chunk_pages


def sentences(count: int, prefix: str = "Sentence") -> str:
    return " ".join(f"{prefix} {number} is about topic." for number in range(1, count + 1))


def test_chunks_never_cross_a_page_boundary():
    chunks = chunk_pages(
        [(1, "alpha beta gamma"), (2, "delta epsilon zeta")], target_chars=1000, overlap_chars=150
    )

    assert [(chunk.page_number, chunk.text) for chunk in chunks] == [
        (1, "alpha beta gamma"),
        (2, "delta epsilon zeta"),
    ]


def test_empty_and_whitespace_pages_produce_no_chunks():
    chunks = chunk_pages(
        [(1, ""), (2, "   \n\n  "), (3, "real text"), (4, "\x0c")],
        target_chars=1000,
        overlap_chars=150,
    )

    assert [chunk.page_number for chunk in chunks] == [3]


def test_consecutive_chunks_on_a_page_overlap():
    chunks = chunk_pages([(1, sentences(12))], target_chars=100, overlap_chars=30)

    assert len(chunks) > 1
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous.text.split()[-1] in current.text.split()


def test_overlap_is_not_carried_across_pages():
    chunks = chunk_pages(
        [(1, sentences(12, "Alpha")), (2, sentences(12, "Beta"))],
        target_chars=100,
        overlap_chars=30,
    )

    page_two = [chunk for chunk in chunks if chunk.page_number == 2]
    assert page_two[0].text.startswith("Beta 1 is about topic.")
    assert all("Alpha" not in chunk.text for chunk in page_two)


def test_chunks_respect_the_target_size():
    chunks = chunk_pages([(1, sentences(60))], target_chars=120, overlap_chars=40)

    assert all(len(chunk.text) <= 120 for chunk in chunks)


def test_a_word_longer_than_the_target_is_hard_split():
    word = "x" * 250

    chunks = chunk_pages([(1, word)], target_chars=100, overlap_chars=10)

    assert all(len(chunk.text) <= 100 for chunk in chunks)
    assert "".join(chunk.text for chunk in chunks) == word


def test_chunk_index_is_continuous_across_pages():
    chunks = chunk_pages(
        [(1, sentences(10)), (2, sentences(10, "Other")), (3, "tail")],
        target_chars=100,
        overlap_chars=30,
    )

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_output_is_deterministic():
    pages = [(1, sentences(30)), (2, "First paragraph.\n\nSecond paragraph here.")]

    assert chunk_pages(pages, 100, 30) == chunk_pages(pages, 100, 30)


def test_paragraph_breaks_are_kept_between_paragraphs():
    text = "First paragraph ends here.\n\nSecond paragraph starts here."

    chunks = chunk_pages([(1, text)], target_chars=40, overlap_chars=0)

    assert [chunk.text for chunk in chunks] == [
        "First paragraph ends here.",
        "Second paragraph starts here.",
    ]


def test_wrapped_pdf_lines_are_joined_with_spaces():
    chunks = chunk_pages([(1, "The quick\nbrown fox\njumps.")], target_chars=1000, overlap_chars=0)

    assert chunks[0].text == "The quick brown fox jumps."


@pytest.mark.parametrize(("target", "overlap"), [(0, 0), (100, 100), (100, 150), (100, -1)])
def test_invalid_sizes_are_rejected(target, overlap):
    with pytest.raises(ValueError):
        chunk_pages([(1, "text")], target_chars=target, overlap_chars=overlap)
