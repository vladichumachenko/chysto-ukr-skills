"""Apply agent edits to a Markdown text and render the review page.

Every edit names a block and an exact `before` substring that must occur once in that
block, outside code, math and URLs. Edits are validated first; nothing is changed if any
edit is invalid. Only `level == "error"` edits reach the fixed text; advice is shown only.
"""
from textmodel import is_protected, join_blocks, protected_spans, split_blocks

TYPES = ("rusism", "calque", "jargon", "restructure")
LEVELS = ("error", "advice")
EDITABLE_KINDS = ("text", "heading")


class EditError(Exception):
    pass


def _occurrences(text: str, needle: str) -> list:
    out, i = [], text.find(needle)
    while needle and i != -1:
        out.append(i)
        i = text.find(needle, i + len(needle))
    return out


def locate(blocks: list, e: dict) -> tuple:
    """(block, start, end) of the edit's `before`; raises EditError naming the edit."""
    eid = e.get("id")
    if e.get("type") not in TYPES:
        raise EditError(f"edit {eid}: unknown type {e.get('type')!r}; expected one of {TYPES}")
    if e.get("level") not in LEVELS:
        raise EditError(f"edit {eid}: unknown level {e.get('level')!r}; expected one of {LEVELS}")
    bid = e.get("block")
    if not isinstance(bid, int) or not 0 <= bid < len(blocks):
        raise EditError(f"edit {eid}: block {bid!r} does not exist")
    block = blocks[bid]
    if block.kind not in EDITABLE_KINDS:
        raise EditError(f"edit {eid}: block {bid} is {block.kind}, not editable prose")
    before = e.get("before") or ""
    hits = _occurrences(block.text, before)
    if not hits:
        raise EditError(f"edit {eid}: `before` not found in block {bid}: {before!r}")
    if len(hits) > 1:
        raise EditError(f"edit {eid}: `before` occurs {len(hits)} times in block {bid}; "
                        f"extend it with surrounding words to make it unique: {before!r}")
    start, end = hits[0], hits[0] + len(before)
    if is_protected(protected_spans(block.text), start, end):
        raise EditError(f"edit {eid}: `before` touches code, math or a URL in block {bid}")
    return block, start, end


def validate_edits(blocks: list, edits: list) -> None:
    spans = {}
    for e in edits:
        block, start, end = locate(blocks, e)
        for other_id, s, t in spans.get(block.id, []):
            if start < t and s < end:
                raise EditError(f"edit {e.get('id')}: overlaps edit {other_id} in block {block.id}")
        spans.setdefault(block.id, []).append((e.get("id"), start, end))


def apply_edits(md: str, edits: list) -> str:
    blocks = split_blocks(md)
    validate_edits(blocks, edits)
    by_block = {}
    for e in edits:
        if e["level"] == "error":
            _, start, end = locate(blocks, e)
            by_block.setdefault(e["block"], []).append((start, end, e["after"]))
    for bid, changes in by_block.items():
        text = blocks[bid].text
        for start, end, after in sorted(changes, reverse=True):  # right to left keeps offsets valid
            text = text[:start] + after + text[end:]
        blocks[bid].text = text
    return join_blocks(blocks)
