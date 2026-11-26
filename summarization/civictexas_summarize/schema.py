"""Structured summary format.

Every factual statement carries citations to bill sections, and each citation
includes a short verbatim quote so it can be checked against the official text.
Stored as JSON in public.ai_summaries.content and rendered by
web/src/components/summary-view.tsx.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "2026-11-26"


class SchemaError(ValueError):
    """The model output does not match the required structure."""


@dataclass
class Citation:
    section: str  # e.g. 'SECTION 1' or 'Sec. 32.351'
    quote: str  # short verbatim excerpt from that section


@dataclass
class Statement:
    text: str
    citations: List[Citation] = field(default_factory=list)


@dataclass
class AffectedGroup:
    group: str
    effect: str
    basis: str  # 'stated' (the bill says so) or 'inferred' (a reasonable reading)
    citations: List[Citation] = field(default_factory=list)


@dataclass
class Summary:
    overview: Statement
    key_provisions: List[Statement]
    changes_to_existing_law: List[Statement]
    affected_groups: List[AffectedGroup]
    effective_dates: List[Statement]
    fiscal_information: Optional[Statement]
    uncertainties: List[str]

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


# JSON Schema handed to providers that support structured output.
_CITATIONS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"section": {"type": "string"}, "quote": {"type": "string"}},
        "required": ["section", "quote"],
        "additionalProperties": False,
    },
}
_STATEMENT = {
    "type": "object",
    "properties": {"text": {"type": "string"}, "citations": _CITATIONS},
    "required": ["text", "citations"],
    "additionalProperties": False,
}
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": _STATEMENT,
        "key_provisions": {"type": "array", "items": _STATEMENT},
        "changes_to_existing_law": {"type": "array", "items": _STATEMENT},
        "affected_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "group": {"type": "string"},
                    "effect": {"type": "string"},
                    "basis": {"type": "string", "enum": ["stated", "inferred"]},
                    "citations": _CITATIONS,
                },
                "required": ["group", "effect", "basis", "citations"],
                "additionalProperties": False,
            },
        },
        "effective_dates": {"type": "array", "items": _STATEMENT},
        "fiscal_information": {"anyOf": [_STATEMENT, {"type": "null"}]},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["overview", "key_provisions", "changes_to_existing_law", "affected_groups",
                 "effective_dates", "fiscal_information", "uncertainties"],
    "additionalProperties": False,
}


def _citations(raw: Any, where: str) -> List[Citation]:
    if not isinstance(raw, list):
        raise SchemaError(f"{where}.citations must be a list")
    out = []
    for i, c in enumerate(raw):
        if not isinstance(c, dict) or not isinstance(c.get("section"), str) or not isinstance(c.get("quote"), str):
            raise SchemaError(f"{where}.citations[{i}] needs string 'section' and 'quote'")
        out.append(Citation(section=c["section"].strip(), quote=c["quote"].strip()))
    return out


def _statement(raw: Any, where: str) -> Statement:
    if not isinstance(raw, dict) or not isinstance(raw.get("text"), str) or not raw["text"].strip():
        raise SchemaError(f"{where} needs non-empty 'text'")
    return Statement(text=raw["text"].strip(), citations=_citations(raw.get("citations", []), where))


def _statements(raw: Any, where: str) -> List[Statement]:
    if not isinstance(raw, list):
        raise SchemaError(f"{where} must be a list")
    return [_statement(item, f"{where}[{i}]") for i, item in enumerate(raw)]


def parse_summary(data: Any) -> Summary:
    """Validate the structure of model output. Raises SchemaError."""
    if not isinstance(data, dict):
        raise SchemaError("summary must be a JSON object")
    missing = [k for k in JSON_SCHEMA["required"] if k not in data]
    if missing:
        raise SchemaError(f"missing fields: {', '.join(missing)}")
    groups = []
    for i, g in enumerate(data["affected_groups"] if isinstance(data["affected_groups"], list) else []):
        where = f"affected_groups[{i}]"
        if not isinstance(g, dict) or g.get("basis") not in ("stated", "inferred"):
            raise SchemaError(f"{where}.basis must be 'stated' or 'inferred'")
        if not str(g.get("group", "")).strip() or not str(g.get("effect", "")).strip():
            raise SchemaError(f"{where} needs 'group' and 'effect'")
        groups.append(AffectedGroup(group=g["group"].strip(), effect=g["effect"].strip(), basis=g["basis"],
                                    citations=_citations(g.get("citations", []), where)))
    if not isinstance(data["uncertainties"], list) or not all(isinstance(u, str) for u in data["uncertainties"]):
        raise SchemaError("uncertainties must be a list of strings")
    fiscal = data["fiscal_information"]
    return Summary(
        overview=_statement(data["overview"], "overview"),
        key_provisions=_statements(data["key_provisions"], "key_provisions"),
        changes_to_existing_law=_statements(data["changes_to_existing_law"], "changes_to_existing_law"),
        affected_groups=groups,
        effective_dates=_statements(data["effective_dates"], "effective_dates"),
        fiscal_information=_statement(fiscal, "fiscal_information") if fiscal is not None else None,
        uncertainties=[u.strip() for u in data["uncertainties"] if u.strip()],
    )
