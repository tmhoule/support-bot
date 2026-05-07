from indexer.chunker import chunk_markdown, Chunk


def test_chunks_split_on_h2():
    md = "# Top\nintro\n## Sec A\nbody A\n## Sec B\nbody B\n"
    chunks = chunk_markdown(md, source_path="docs/a.md")
    titles = [c.title_path for c in chunks]
    assert "Top > Sec A" in titles
    assert "Top > Sec B" in titles


def test_chunk_carries_source_path():
    md = "# T\nhello\n"
    chunks = chunk_markdown(md, source_path="x/y.md")
    assert all(c.source_path == "x/y.md" for c in chunks)


def test_long_section_splits_into_overlapping_pieces():
    body = ("paragraph. " * 200)
    md = f"# T\n## Long\n{body}"
    chunks = chunk_markdown(md, source_path="z.md", max_chars=800, overlap_chars=100)
    long_chunks = [c for c in chunks if c.title_path.endswith("Long")]
    assert len(long_chunks) >= 2
    assert all(len(c.text) <= 900 for c in long_chunks)


def test_empty_input_returns_no_chunks():
    assert chunk_markdown("", source_path="empty.md") == []
