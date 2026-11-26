"""Split official bill text into citable sections.

Texas bills are organized into numbered SECTIONs ("SECTION 1.", "SECTION 2.").
Inside a SECTION, sections of a code being added or amended appear as
"Sec. 32.351." Both levels are citable.
"""
import re
from typing import Dict, List

_SECTION = re.compile(r"^\s*SECTION\s+(\d+[A-Z]?)\.", re.M)
_CODE_SEC = re.compile(r"(?:^|\{\+|\[-|\s)Sec\.\s+(\d+[A-Z]?\.\d+[A-Za-z0-9]*)\.", re.M)
_MARKERS = re.compile(r"\{\+|\+\}|\[-|-\]")


_ADDED = re.compile(r"\{\+(.*?)\+\}", re.S)
_REMOVED = re.compile(r"\[-(.*?)-\]", re.S)


def views(text: str) -> List[str]:
    """Normalized readings of a passage, for quote matching:
    as amended (added text kept, removed text dropped), current law (the
    reverse), and the raw text with both."""
    amended = _REMOVED.sub("", _ADDED.sub(r"\1", text))
    current = _ADDED.sub("", _REMOVED.sub(r"\1", text))
    return [normalize(amended), normalize(current), normalize(text)]


def normalize(text: str) -> str:
    """Strip amendment markers, unify quotes and collapse whitespace for matching."""
    text = _MARKERS.sub("", text)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def split_sections(text: str) -> Dict[str, str]:
    """Return {'SECTION 1': text, 'Sec. 32.351': text, ...}.

    'Sec.' entries run from their heading to the next 'Sec.' or SECTION.
    """
    sections: Dict[str, str] = {}
    starts = [(m.start(), f"SECTION {m.group(1)}") for m in _SECTION.finditer(text)]
    for i, (start, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        sections[name] = text[start:end]
    code_starts = sorted([(m.start(), f"Sec. {m.group(1)}") for m in _CODE_SEC.finditer(text)] + starts)
    for i, (start, name) in enumerate(code_starts):
        if not name.startswith("Sec."):
            continue
        end = code_starts[i + 1][0] if i + 1 < len(code_starts) else len(text)
        sections.setdefault(name, text[start:end])
    return sections


def canonical_section(name: str) -> str:
    """'section 1' / 'SECTION 1.' / 'Sec 32.351' -> canonical key."""
    name = name.strip().rstrip(".")
    m = re.match(r"^section\s+(\d+[a-z]?)$", name, re.I)
    if m:
        return f"SECTION {m.group(1).upper()}"
    m = re.match(r"^(?:sec\.?|§)\s*(\d+[a-z]?\.\d+[a-z0-9]*)$", name, re.I)
    if m:
        return f"Sec. {m.group(1)}"
    return name
