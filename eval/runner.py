from dataclasses import dataclass, field
from pathlib import Path
import yaml
from app.citations import extract_citations


@dataclass
class GoldenCase:
    id: str
    question: str
    must_have_citations: bool = False
    must_not_call_tools: bool = False
    must_mention_any: list[str] = field(default_factory=list)
    must_not_mention: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    failures: list[str]


def load_cases(path: Path) -> list[GoldenCase]:
    data = yaml.safe_load(Path(path).read_text())
    return [GoldenCase(**d) for d in data]


def evaluate_response(case: GoldenCase, response_text: str, *, tool_calls: list[str] | None = None) -> EvalResult:
    fails: list[str] = []
    if case.must_have_citations and not extract_citations(response_text):
        fails.append("missing citations")
    if case.must_not_call_tools and tool_calls:
        fails.append(f"unexpected tool calls: {tool_calls}")
    if case.must_mention_any:
        if not any(s.lower() in response_text.lower() for s in case.must_mention_any):
            fails.append(f"none of {case.must_mention_any} mentioned")
    for s in case.must_not_mention:
        if s.lower() in response_text.lower():
            fails.append(f"forbidden mention of '{s}'")
    return EvalResult(case_id=case.id, passed=not fails, failures=fails)
