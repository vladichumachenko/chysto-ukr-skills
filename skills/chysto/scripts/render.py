"""Apply agent edits to a Markdown text and render the review page.

Every edit names a block and an exact `before` substring that must occur once in that
block, outside code, math and URLs. Edits are validated first; nothing is changed if any
edit is invalid. Only `level == "error"` edits reach the fixed text; advice is shown only.

Usage: python3 render.py INPUT.md EDITS.json [-o OUTDIR]
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

from textmodel import is_protected, join_blocks, protected_spans, split_blocks

TYPES = ("rusism", "calque", "jargon", "restructure")
LEVELS = ("error", "advice")
EDITABLE_KINDS = ("text", "heading")
# Markdown markup at the start of a line that an edit must not swallow.
LINE_MARKUP = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+|[-*+][ \t]+|\d+[.)][ \t]+|>[ \t]?|\|[ \t]*)*")


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
    after = e.get("after")
    if not isinstance(after, str):
        raise EditError(f"edit {eid}: `after` must be a string")
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
    line_start = block.text.rfind("\n", 0, start) + 1
    markup_end = line_start + LINE_MARKUP.match(block.text[line_start:]).end()
    if start < markup_end:
        raise EditError(f"edit {eid}: `before` includes Markdown markup (#, -, >, |) at the start "
                        f"of a line in block {bid}; start `before` after the markup")
    return block, start, end


def validate_edits(blocks: list, edits: list) -> None:
    if not isinstance(edits, list) or not all(isinstance(e, dict) for e in edits):
        raise EditError("edits.json must be a JSON list of edit objects")
    spans, seen = {}, set()
    for e in edits:
        if e.get("id") in seen:
            raise EditError(f"edit {e.get('id')}: duplicate id")
        seen.add(e.get("id"))
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


# ---------------------------------------------------------------- review page
# Footnotes speak to the author of the Ukrainian text, so labels are Ukrainian.
TYPE_LABELS = {"rusism": "русизм", "calque": "калька", "jargon": "жаргон", "restructure": "перебудова"}
LEVEL_LABELS = {"error": "помилка", "advice": "порада"}
SOURCE_LABELS = {"lt": "LanguageTool", "lt-soft": "LanguageTool (м'яка порада)", "chysto": "список chysto",
                 "slovnik1918": "словник Іваницького–Шумлянського (1918)", "model": "оцінка редактора"}

CSS = """
:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#6b6f76;--del-bg:#fde2e2;--del-fg:#9b1c1c;--ins-bg:#dcfce7;
--ins-fg:#14532d;--adv:#b7791f;--adv-bg:#fef6e0;--rule:#e5e3dc;--code:#f2f0ea}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e6e6e6;--muted:#9aa0a6;--del-bg:#4a1d1d;
--del-fg:#ffb4b4;--ins-bg:#173a24;--ins-fg:#b6f2c8;--adv:#f0b545;--adv-bg:#3a2f12;--rule:#2c2f36;--code:#22252b}}
body{background:var(--bg);color:var(--fg);font:17px/1.65 Georgia,"Times New Roman",serif;margin:0}
main{max-width:46rem;margin:0 auto;padding:2rem 1rem 4rem}
h1,h2,h3,h4,h5,h6{font-family:-apple-system,"Segoe UI",sans-serif;line-height:1.25}
.ch-summary{font:14px/1.5 -apple-system,"Segoe UI",sans-serif;border:1px solid var(--rule);border-radius:8px;
padding:.75rem 1rem;margin-bottom:2rem}
.ch-summary ul{margin:.25rem 0 0;padding-left:1.2rem}
del.ch-del{background:var(--del-bg);color:var(--del-fg);text-decoration:line-through;border-radius:3px;padding:0 2px}
ins.ch-ins{background:var(--ins-bg);color:var(--ins-fg);text-decoration:none;border-radius:3px;padding:0 2px}
.ch-advice{text-decoration:underline wavy var(--adv);text-underline-offset:3px;background:var(--adv-bg)}
sup{font:700 11px -apple-system,sans-serif;color:var(--muted)}
ol.ch-notes{font:14px/1.5 -apple-system,"Segoe UI",sans-serif;color:var(--muted);border-left:3px solid var(--rule);
margin:.25rem 0 1.5rem;padding-left:2rem}
.ch-tag{display:inline-block;font-weight:600;font-size:12px;border-radius:9px;padding:0 7px;margin-right:4px;
background:var(--code);color:var(--fg)}
.ch-tag.advice{background:var(--adv-bg);color:var(--adv)}
code,pre{font-family:ui-monospace,Menlo,monospace;font-size:14px;background:var(--code);border-radius:4px}
code{padding:0 3px}pre{padding:.75rem;overflow-x:auto;white-space:pre-wrap}
"""


def _inline(text: str) -> str:
    """Escape text and render inline code and bold; line breaks are kept."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", out)
    return out.replace("\n", "<br>\n")


def _block_html(block, marks: list) -> tuple:
    """Render one block; marks are (start, end, edit, number). Returns (html, footnotes)."""
    if block.kind == "blank":
        return "", []
    if block.kind == "code":
        return f"<pre>{html.escape(block.text.rstrip(chr(10)), quote=False)}</pre>\n", []
    text = block.text.rstrip("\n")
    parts, notes, pos = [], [], 0
    for start, end, e, n in sorted(marks, key=lambda m: m[0]):
        parts.append(_inline(text[pos:start]))
        before, after = _inline(text[start:end]), _inline(e.get("after", ""))
        if e["level"] == "error":
            parts.append(f'<del class="ch-del">{before}</del><ins class="ch-ins">{after}</ins><sup>{n}</sup>')
        else:
            parts.append(f'<span class="ch-advice" title="{html.escape(e.get("after", ""))}">{before}</span>'
                         f'<sup>{n}</sup>')
        notes.append((n, e))
        pos = end
    parts.append(_inline(text[pos:]))
    body = "".join(parts)
    if block.kind == "heading":
        level = len(text) - len(text.lstrip("#"))
        body = re.sub(r"^#{1,6}\s*", "", body)
        return f"<h{level}>{body}</h{level}>\n", notes
    return f"<p>{body}</p>\n", notes


def _note_html(n: int, e: dict) -> str:
    level = e["level"]
    tags = (f'<span class="ch-tag">{TYPE_LABELS[e["type"]]}</span>'
            f'<span class="ch-tag {level}">{LEVEL_LABELS[level]}</span>')
    proposal = ""
    if level == "advice":
        proposal = f'можна: «{html.escape(e.get("before", ""))}» → «{html.escape(e.get("after", ""))}». '
    source = SOURCE_LABELS.get(e.get("source", ""), e.get("source", ""))
    src = f' <em>Джерело: {html.escape(source)}.</em>' if source else ""
    return f'<li value="{n}">{tags}{proposal}{html.escape(e.get("reason", ""))}{src}</li>'


def render_html(md: str, edits: list, title: str) -> str:
    blocks = split_blocks(md)
    validate_edits(blocks, edits)
    located = sorted(((locate(blocks, e), e) for e in edits), key=lambda x: (x[0][0].id, x[0][1]))
    marks = {}
    for n, ((block, start, end), e) in enumerate(located, 1):
        marks.setdefault(block.id, []).append((start, end, e, n))

    counts_type, counts_level = {}, {}
    for e in edits:
        counts_type[e["type"]] = counts_type.get(e["type"], 0) + 1
        counts_level[e["level"]] = counts_level.get(e["level"], 0) + 1
    summary_items = "".join(f"<li>{TYPE_LABELS[t]}: {c}</li>" for t, c in counts_type.items())
    levels = ", ".join(f"{LEVEL_LABELS[lv]}: {c}" for lv, c in counts_level.items()) or "правок немає"

    body = []
    for b in blocks:
        chunk, notes = _block_html(b, marks.get(b.id, []))
        body.append(chunk)
        if notes:
            body.append('<ol class="ch-notes">' + "".join(_note_html(n, e) for n, e in notes) + "</ol>\n")

    return ("<!doctype html>\n<html lang=\"uk\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)} — chysto</title><style>{CSS}</style></head><body><main>\n"
            f'<section class="ch-summary"><strong>Правок: {len(edits)}</strong> ({levels})'
            f"<ul>{summary_items}</ul></section>\n" + "".join(body) + "</main></body></html>\n")


def _title(md: str, fallback: str) -> str:
    for b in split_blocks(md):
        if b.kind == "heading":
            return re.sub(r"^#{1,6}\s*", "", b.text).strip()
    return fallback


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Apply edits.json and write <name>.fixed.md + <name>.review.html")
    ap.add_argument("input")
    ap.add_argument("edits")
    ap.add_argument("-o", "--outdir", default=None, help="output directory (default: next to INPUT)")
    a = ap.parse_args(argv)
    src = Path(a.input)
    try:
        with open(src, encoding="utf-8", newline="") as f:  # keep CRLF byte for byte
            md = f.read()
        with open(a.edits, encoding="utf-8") as f:
            edits = json.load(f)
        fixed = apply_edits(md, edits)
        page = render_html(md, edits, _title(md, src.stem))
    except json.JSONDecodeError as err:
        print(f"error: {a.edits} is not valid JSON: {err}", file=sys.stderr)
        return 1
    except (EditError, OSError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    out = Path(a.outdir) if a.outdir else src.parent
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"{src.stem}.fixed.md", "w", encoding="utf-8", newline="") as f:
        f.write(fixed)
    (out / f"{src.stem}.review.html").write_text(page, encoding="utf-8")
    print(f"{len(edits)} edits -> {out / (src.stem + '.fixed.md')}, {out / (src.stem + '.review.html')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
