from pathlib import Path

import pymupdf

UNREADABLE_MESSAGE = "This file couldn't be read. It may be damaged."
TOO_MANY_PAGES_MESSAGE = "This PDF has more than {max_pages} pages."
NO_TEXT_MESSAGE = "No extractable text. OCR isn't supported yet."


class ExtractionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def extract_pages(path: Path, max_pages: int) -> list[str]:
    """Returns each page's text in order. Raises ExtractionError with a user-facing message."""
    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise ExtractionError(UNREADABLE_MESSAGE) from exc

    with document:
        if document.page_count > max_pages:
            raise ExtractionError(TOO_MANY_PAGES_MESSAGE.format(max_pages=max_pages))
        try:
            pages = [page.get_text() for page in document]
        except Exception as exc:
            raise ExtractionError(UNREADABLE_MESSAGE) from exc

    if not any(text.strip() for text in pages):
        raise ExtractionError(NO_TEXT_MESSAGE)
    return pages
