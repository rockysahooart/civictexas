"""Automated checks run on every generated summary before human review.

These checks catch mechanical problems: fabricated or misquoted citations,
describing a bill as law when it isn't, advocacy language and unlabeled
inferences. Passing them does NOT mean a summary is accurate. A person still
reviews every summary against the official text before it is published.
"""
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Tuple

from .schema import AffectedGroup, Citation, Statement, Summary
from .sections import canonical_section, normalize, split_sections, views

ENACTED_STATUSES = {"signed", "became_law_without_signature"}

# Phrases that present a measure as current law.
_ENACTED_LANGUAGE = re.compile(
    r"\b(is now (?:the )?law|became law|has become law|was signed into law|new law (?:requires|says)"
    r"|the law now|now requires|now prohibits|has been enacted|was enacted)\b", re.I)
# Advocacy, endorsements and motive attribution.
_ADVOCACY = re.compile(
    r"\b(you should|we (?:recommend|urge|support|oppose)|should (?:support|oppose|pass|reject)"
    r"|vote (?:for|against)|(?:a )?(?:good|bad|great|terrible|dangerous|common[- ]sense|radical|extreme) (?:bill|law|policy)"
    r"|in order to (?:punish|reward|help (?:their|his|her) )|politically motivated|the author wants to|aims to score)\b",
    re.I)
MAX_QUOTE_WORDS = 60


@dataclass
class Issue:
    code: str
    message: str
    where: str
    severity: str = "error"  # 'error' blocks publication; 'warning' needs reviewer attention


@dataclass
class ValidationResult:
    issues: List[Issue] = field(default_factory=list)
    citations_checked: int = 0

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def to_json(self) -> Dict:
        return {"passed": self.passed, "citations_checked": self.citations_checked,
                "issues": [asdict(i) for i in self.issues]}


def _all_statements(summary: Summary) -> Iterable[Tuple[str, Statement]]:
    yield "overview", summary.overview
    for name in ("key_provisions", "changes_to_existing_law", "effective_dates"):
        for i, s in enumerate(getattr(summary, name)):
            yield f"{name}[{i}]", s
    if summary.fiscal_information:
        yield "fiscal_information", summary.fiscal_information


def _check_citation(c: Citation, where: str, sections: Dict[str, str], full_text: str,
                    result: ValidationResult) -> None:
    result.citations_checked += 1
    key = canonical_section(c.section)
    if key not in sections:
        result.issues.append(Issue("unknown_section", f"cites {c.section!r}, which is not in this bill version", where))
        return
    if not c.quote:
        result.issues.append(Issue("empty_quote", f"citation to {key} has no supporting quote", where))
        return
    if len(c.quote.split()) > MAX_QUOTE_WORDS:
        result.issues.append(Issue("quote_too_long", f"quote from {key} exceeds {MAX_QUOTE_WORDS} words", where,
                                   "warning"))
    quote = normalize(c.quote)
    if not any(quote in view for view in views(sections[key])):
        if any(quote in view for view in views(full_text)):
            result.issues.append(Issue("quote_wrong_section", f"quote exists in the bill but not in {key}", where))
        else:
            result.issues.append(Issue("quote_not_found", f"quote not found in the official text: {c.quote[:80]!r}",
                                       where))


def validate_summary(summary: Summary, source_text: str, bill_status: str,
                     has_fiscal_note: bool = False) -> ValidationResult:
    result = ValidationResult()
    sections = split_sections(source_text)
    if not sections:
        result.issues.append(Issue("no_sections", "could not find any SECTION headings in the source text", "source"))

    for where, statement in _all_statements(summary):
        if not statement.citations:
            result.issues.append(Issue("missing_citation", "factual statement has no citation", where))
        for c in statement.citations:
            _check_citation(c, where, sections, source_text, result)

    for i, group in enumerate(summary.affected_groups):
        where = f"affected_groups[{i}]"
        if group.basis == "stated" and not group.citations:
            result.issues.append(Issue("missing_citation", "an effect described as stated in the bill needs a citation",
                                       where))
        for c in group.citations:
            _check_citation(c, where, sections, source_text, result)

    if summary.fiscal_information and not has_fiscal_note:
        result.issues.append(Issue("fiscal_without_source",
                                   "fiscal information given but no official fiscal note is available", "fiscal_information",
                                   "warning"))

    texts = [(w, s.text) for w, s in _all_statements(summary)]
    texts += [(f"affected_groups[{i}]", f"{g.group}: {g.effect}") for i, g in enumerate(summary.affected_groups)]
    texts += [(f"uncertainties[{i}]", u) for i, u in enumerate(summary.uncertainties)]
    for where, text in texts:
        if bill_status not in ENACTED_STATUSES and _ENACTED_LANGUAGE.search(text):
            result.issues.append(Issue("presented_as_law",
                                       f"describes the measure as law, but its status is {bill_status!r}", where))
        if _ADVOCACY.search(text):
            result.issues.append(Issue("not_neutral", f"advocacy or motive language: {_ADVOCACY.search(text).group(0)!r}",
                                       where))
    return result
