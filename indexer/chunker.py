from dataclasses import dataclass
from markdown_it import MarkdownIt


@dataclass(frozen=True)
class Chunk:
    text: str
    title_path: str
    source_path: str
    char_start: int


_md = MarkdownIt()


def _split_long(text: str, max_chars: int, overlap: int) -> list[tuple[int, str]]:
    if len(text) <= max_chars:
        return [(0, text)]
    pieces = []
    start = 0
    step = max(1, max_chars - overlap)
    while start < len(text):
        end = min(len(text), start + max_chars)
        pieces.append((start, text[start:end]))
        if end == len(text):
            break
        start += step
    return pieces


def _line_start_offsets(content: str) -> list[int]:
    """Return a list mapping line index -> character offset where that line starts."""
    offsets = [0]
    for i, ch in enumerate(content):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def chunk_markdown(
    content: str,
    *,
    source_path: str,
    max_chars: int = 2000,
    overlap_chars: int = 200,
) -> list[Chunk]:
    if not content.strip():
        return []
    tokens = _md.parse(content)
    line_starts = _line_start_offsets(content)

    def line_to_offset(line_no: int) -> int:
        if line_no < 0:
            return 0
        if line_no >= len(line_starts):
            return len(content)
        return line_starts[line_no]

    sections: list[tuple[list[str], int, int]] = []
    title_stack: list[str] = []
    current_start = 0

    def flush_until(idx: int) -> None:
        if idx > current_start:
            sections.append((list(title_stack), current_start, idx))

    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            level = int(tok.tag[1])
            line_no = tok.map[0] if tok.map else 0
            byte_pos = line_to_offset(line_no)
            flush_until(byte_pos)
            inline = tokens[i + 1] if i + 1 < len(tokens) else None
            text = inline.content.strip() if inline is not None and inline.type == "inline" else ""
            # Trim stack to parent depth, then push this header.
            title_stack[:] = title_stack[: max(0, level - 1)]
            title_stack.append(text)
            current_start = byte_pos
    flush_until(len(content))

    chunks: list[Chunk] = []
    for stack, s, e in sections:
        body = content[s:e]
        if not body.strip():
            continue
        title_path = " > ".join(stack) if stack else source_path
        for off, piece in _split_long(body, max_chars, overlap_chars):
            chunks.append(
                Chunk(
                    text=piece,
                    title_path=title_path,
                    source_path=source_path,
                    char_start=s + off,
                )
            )
    return chunks
