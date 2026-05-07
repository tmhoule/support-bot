from eval.runner import evaluate_response, GoldenCase


def test_must_have_citations_pass():
    case = GoldenCase(id="x", question="q", must_have_citations=True)
    res = evaluate_response(case, "see [github:a.md] for details")
    assert res.passed


def test_must_have_citations_fail():
    case = GoldenCase(id="x", question="q", must_have_citations=True)
    res = evaluate_response(case, "no citation here")
    assert not res.passed


def test_must_mention_any():
    case = GoldenCase(id="x", question="q", must_mention_any=["weekly"])
    assert evaluate_response(case, "patch weekly").passed
    assert not evaluate_response(case, "patch monthly").passed


def test_must_not_mention():
    case = GoldenCase(id="x", question="q", must_not_mention=["joke"])
    assert evaluate_response(case, "I cannot do that.").passed
    assert not evaluate_response(case, "Here's a joke").passed
