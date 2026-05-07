from app.citations import (
    extract_citations,
    needs_warning_banner,
    BANNER,
    render_inline_citations_html,
    CitationStreamRewriter,
)


def test_extract_github_citations():
    text = "See [github:security/patching.md] and [github:README.md]."
    cites = extract_citations(text)
    assert {c.kind for c in cites} == {"github"}
    assert sorted(c.ref for c in cites) == ["README.md", "security/patching.md"]


def test_extract_url_citations():
    text = "Per [https://learn.microsoft.com/en-us/x] this works."
    cites = extract_citations(text)
    assert any(c.kind == "url" and "learn.microsoft.com" in c.ref for c in cites)


def test_no_warning_for_greeting():
    assert not needs_warning_banner("Hi! How can I help?")
    assert not needs_warning_banner("Could you tell me the hostname?")


def test_warning_when_factual_claim_no_citation():
    text = "RDP requires firewall port 3389 to be open."
    assert needs_warning_banner(text)


def test_no_warning_when_factual_claim_with_citation():
    text = "RDP requires port 3389 [github:security/rdp.md]."
    assert not needs_warning_banner(text)


def test_banner_string():
    assert "documentation" in BANNER.lower() or "verify" in BANNER.lower()


def test_render_github_citation_to_anchor():
    out = render_inline_citations_html(
        "see [github:architecture/firewall.md] for details",
        github_repo_url="https://github.com/owner/repo",
    )
    assert '<a href="https://github.com/owner/repo/blob/main/architecture/firewall.md"' in out
    assert ">github:architecture/firewall.md</a>" in out
    assert 'target="_blank"' in out


def test_render_strips_dot_git_suffix():
    out = render_inline_citations_html(
        "[github:x.md]",
        github_repo_url="https://github.com/owner/repo.git",
    )
    assert "https://github.com/owner/repo/blob/main/x.md" in out
    assert ".git/blob" not in out


def test_render_url_citation_to_anchor():
    out = render_inline_citations_html(
        "[https://learn.microsoft.com/en-us/x] is the source",
        github_repo_url="https://github.com/x/y",
    )
    assert '<a href="https://learn.microsoft.com/en-us/x"' in out


def test_stream_rewriter_holds_unclosed_bracket():
    rw = CitationStreamRewriter(github_repo_url="https://github.com/x/y")
    a = rw.feed("see [github:")
    assert a == "see "
    b = rw.feed("a.md] more")
    assert "github:a.md</a>" in b
    assert " more" in b


def test_stream_rewriter_flush_emits_unclosed_as_plain():
    rw = CitationStreamRewriter(github_repo_url="https://github.com/x/y")
    rw.feed("hello [github:")
    tail = rw.flush()
    assert "[github:" in tail
    assert "<a" not in tail


def test_stream_rewriter_handles_complete_citation_in_one_token():
    rw = CitationStreamRewriter(github_repo_url="https://github.com/x/y")
    out = rw.feed("answer [github:a.md].")
    assert "github:a.md</a>" in out


def test_stream_rewriter_escapes_html_in_text():
    rw = CitationStreamRewriter(github_repo_url="https://github.com/x/y")
    out = rw.feed("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
