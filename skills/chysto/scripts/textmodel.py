"""Markdown text model: split a document into blocks and find spans that must never be edited.

A block keeps its source text verbatim (including newlines), so joining the blocks
reproduces the document byte for byte. Edits address a block by its id.
"""
import re
from dataclasses import dataclass

# Fences may be longer than three characters, indented, or inside quotes and list items.
QUOTE_PREFIX = re.compile(r"^(?:[ \t]*>)*[ \t]*")
FENCE_OPEN = re.compile(r"(`{3,}|~{3,})")
HEADING = re.compile(r"^#{1,6}\s")
INDENTED = re.compile(r"^( {4}|\t)")

# Spans inside a text block that are code, math, or addresses rather than prose.
PROTECTED = [
    re.compile(r"(`+)[^`]*?\1"),                       # inline code, any number of backticks
    re.compile(r"\$\$.+?\$\$", re.S),                  # display math
    re.compile(r"(?<![\\\w])\$[^$\n]+?\$(?!\w)"),      # inline math
    re.compile(r"https?://[^\s<>()\]]+[^\s<>()\].,;:!?»\"']"),  # bare URLs
    re.compile(r"\]\([^)\s]+(?:\s+\"[^\"]*\")?\)"),    # Markdown link targets
    re.compile(r"<[^>\n]+>"),                          # inline HTML tags
]


@dataclass
class Block:
    id: int
    kind: str  # "text" | "heading" | "code" | "blank"
    text: str


def _strip_prefix(line: str) -> str:
    return line[QUOTE_PREFIX.match(line).end():]


def fence_open(line: str):
    """(char, length) if line opens a fenced code block, else None."""
    m = FENCE_OPEN.match(_strip_prefix(line))
    return (m.group(1)[0], len(m.group(1))) if m else None


def fence_closes(line: str, fence) -> bool:
    rest = _strip_prefix(line).rstrip()
    char, n = fence
    return len(rest) >= n and set(rest) == {char}


def split_blocks(md: str) -> list:
    """Split Markdown into blocks; join_blocks(split_blocks(md)) == md."""
    lines = md.splitlines(keepends=True)
    raw = []  # (kind, text)
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            raw.append(("blank", "".join(lines[i:j])))
            i = j
        elif fence_open(line):
            fence = fence_open(line)
            j = i + 1
            while j < len(lines) and not fence_closes(lines[j], fence):
                j += 1
            j = min(j + 1, len(lines))  # include the closing fence when present
            raw.append(("code", "".join(lines[i:j])))
            i = j
        elif HEADING.match(line):
            raw.append(("heading", line))
            i += 1
        else:
            j = i
            while (j < len(lines) and lines[j].strip()
                   and not fence_open(lines[j]) and not HEADING.match(lines[j])):
                j += 1
            chunk = lines[i:j]
            # A paragraph whose every line is indented by 4+ spaces is an indented code block.
            kind = "code" if all(INDENTED.match(ln) for ln in chunk) else "text"
            raw.append((kind, "".join(chunk)))
            i = j
    return [Block(n, kind, text) for n, (kind, text) in enumerate(raw)]


def join_blocks(blocks: list) -> str:
    return "".join(b.text for b in blocks)


def protected_spans(text: str) -> list:
    """Sorted, merged (start, end) spans of code, math, URLs and link targets in text."""
    spans = sorted((m.start(), m.end()) for rx in PROTECTED for m in rx.finditer(text))
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def is_protected(spans: list, start: int, end: int) -> bool:
    """True if [start, end) overlaps any protected span."""
    return any(s < end and start < e for s, e in spans)
