from app.citations import extract_citations, needs_warning_banner, BANNER


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
