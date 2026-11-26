"""Convert official bill HTML into plain text while keeping amendment markup.

In Texas bill text, underlined text is language being added to existing law
and struck-through text is language being removed. That distinction matters,
so it is preserved with markers:

    {+added text+}    [-removed text-]
"""
import hashlib
import re
from html.parser import HTMLParser
from typing import List

ADD_OPEN, ADD_CLOSE = "{+", "+}"
DEL_OPEN, DEL_CLOSE = "[-", "-]"

_BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "table", "pre"}
_SKIP_TAGS = {"script", "style", "head", "title"}


class _BillTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "u":
            self.parts.append(ADD_OPEN)
        elif tag in ("s", "strike", "del"):
            self.parts.append(DEL_OPEN)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")
        elif tag == "td":
            self.parts.append(" ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "u":
            self.parts.append(ADD_CLOSE)
        elif tag in ("s", "strike", "del"):
            self.parts.append(DEL_CLOSE)
        elif tag in _BLOCK_TAGS or tag == "tr":
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)


def decode_html(raw: bytes) -> str:
    """Decode TLC HTML. Files are usually UTF-8 but older ones are Windows-1252."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def html_to_text(html: str) -> str:
    parser = _BillTextParser()
    parser.feed(html)
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    # Merge adjacent markers ("{+Sec.+}{+ +}{+1.+}" -> "{+Sec. 1.+}") and drop empty ones.
    text = text.replace(ADD_CLOSE + ADD_OPEN, "").replace(DEL_CLOSE + DEL_OPEN, "")
    text = text.replace(ADD_OPEN + ADD_CLOSE, "").replace(DEL_OPEN + DEL_CLOSE, "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
