import re
from collections.abc import Iterable

from app.rag.types import Chunk

PARAGRAPH_BREAK = "\n\n"
PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

Unit = tuple[str, str]  # (joiner placed before this unit, text)


def chunk_pages(
    pages: Iterable[tuple[int, str]], target_chars: int, overlap_chars: int
) -> list[Chunk]:
    """Splits each page into chunks. A chunk never spans two pages."""
    if target_chars < 1 or not 0 <= overlap_chars < target_chars:
        raise ValueError("Need target_chars >= 1 and 0 <= overlap_chars < target_chars")

    chunks: list[Chunk] = []
    for page_number, text in pages:
        for piece in _chunk_page(text, target_chars, overlap_chars):
            chunks.append(Chunk(chunk_index=len(chunks), page_number=page_number, text=piece))
    return chunks


def _chunk_page(text: str, target: int, overlap: int) -> list[str]:
    paragraphs = _normalize_paragraphs(text)
    units = _units(paragraphs, target)
    return _pack(units, target, overlap)


def _normalize_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = PARAGRAPH_SPLIT.split(normalized)
    # PDF lines are wrapped mid-sentence, so single line breaks become spaces.
    return [" ".join(paragraph.split()) for paragraph in paragraphs if paragraph.strip()]


def _units(paragraphs: list[str], target: int) -> list[Unit]:
    units: list[Unit] = []
    for p_index, paragraph in enumerate(paragraphs):
        for s_index, piece in enumerate(_pieces(paragraph, target)):
            if s_index == 0:
                joiner = PARAGRAPH_BREAK if p_index else ""
            else:
                joiner = " "
            units.append((joiner, piece))
    return units


def _pieces(paragraph: str, target: int) -> list[str]:
    """Splits a paragraph into pieces no longer than target: sentences first, then words."""
    if len(paragraph) <= target:
        return [paragraph]
    pieces: list[str] = []
    for sentence in SENTENCE_SPLIT.split(paragraph):
        if len(sentence) <= target:
            pieces.append(sentence)
        else:
            pieces.extend(_split_words(sentence, target))
    return pieces


def _split_words(text: str, target: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for word in text.split(" "):
        # A single word longer than the target is hard-split.
        while len(word) > target:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:target])
            word = word[target:]
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= target:
            current = f"{current} {word}"
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def _join(units: list[Unit]) -> str:
    return "".join((joiner if index else "") + text for index, (joiner, text) in enumerate(units))


def _overlap_tail(units: list[Unit], overlap: int) -> list[Unit]:
    tail: list[Unit] = []
    for unit in reversed(units):
        if len(_join([unit, *tail])) > overlap:
            break
        tail.insert(0, unit)
    return tail


def _pack(units: list[Unit], target: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current: list[Unit] = []
    for unit in units:
        if current and len(_join([*current, unit])) > target:
            chunks.append(_join(current))
            current = _overlap_tail(current, overlap)
            # Drop overlap from the front until the new unit fits.
            while current and len(_join([*current, unit])) > target:
                current = current[1:]
        current = [*current, unit]
    if current:
        chunks.append(_join(current))
    return chunks
