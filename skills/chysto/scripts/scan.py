"""Scan a Ukrainian Markdown text for russisms, calques and Russian-slang jargon.

Writes candidates.json: every block of the document plus candidate spans with
suggestions. Wide on purpose; the agent decides which candidates become edits.

Usage: python3 scan.py INPUT.md [--keep chysto-keep.txt] [--data DIR] -o candidates.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

from lexicon import Lexicon, normalize, stems
from textmodel import is_protected, protected_spans, split_blocks

TOKEN_RX = re.compile(r"[^\W\d_](?:[\w'’ʼ́-]*\w)?", re.U)
SCANNED_KINDS = ("text", "heading")
MAX_SLOVNIK_ROWS = 3
MIN_TRANSLIT_LEN = 5


def tokenize(text: str) -> list:
    """(start, end, word) for each word in text."""
    return [(m.start(), m.end(), m.group()) for m in TOKEN_RX.finditer(text)]


def load_keep(path) -> set:
    if not path or not Path(path).exists():
        return set()
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return {ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")}


def _keep_index(keep: set):
    singles, phrases = set(), []
    for k in keep:
        toks = k.split()
        if len(toks) == 1:
            singles.update(stems(toks[0]))
        else:
            phrases.append(normalize(k))
    return singles, phrases


def _kept(match: str, toks: list, keep_singles: set, keep_phrases: list) -> bool:
    if any(set(stems(t)) & keep_singles for t in toks):
        return True
    m = normalize(match)
    return any(p in m or m in p for p in keep_phrases)


def _candidate(block_id, text, start, end, entry, lex):
    rows = []
    for s in entry.suggestions:
        for row in lex.slovnik_by_uk(s.split()[0]) if s.split() else []:
            if row not in rows:
                rows.append(row)
    return {
        "block": block_id, "start": start, "end": end, "match": text[start:end],
        "type": entry.type, "level": entry.level, "suggestions": entry.suggestions,
        "source": entry.source, "note": entry.note,
        "slovnik": [{"head_ru": r["head_ru"], "uk": r["uk"]} for r in rows[:MAX_SLOVNIK_ROWS]],
    }


def _phrase_hits(toks: list, lex) -> list:
    """(i, j, entry): tokens i..j-1 match a multi-word pattern stem by stem."""
    hits = []
    tok_stems = [set(stems(t[2])) for t in toks]
    for e in lex.phrases():
        pat = [set(stems(w)) for w in e.pattern.split()]
        n = len(pat)
        for i in range(len(toks) - n + 1):
            if all(tok_stems[i + k] & pat[k] for k in range(n)):
                hits.append((i, i + n, e))
    return hits


def _translit_hit(word: str, lex):
    """1918 row whose Russian headword, spelled in Ukrainian letters, equals this word."""
    if len(word) < MIN_TRANSLIT_LEN:
        return None
    index = lex.slovnik_translit_index()
    w = normalize(word)
    if lex.slovnik_by_uk(w):
        return None  # the word is itself a Ukrainian equivalent somewhere in the dictionary
    for row in index.get(w, []):
        if "low_conf" in row.get("flags", ""):
            continue
        uk_words = {normalize(t) for t in TOKEN_RX.findall(row["uk"])}
        if w not in uk_words:
            return row
    return None


def scan_block(block, lex, keep_singles, keep_phrases) -> list:
    text = block.text
    spans = protected_spans(text)
    toks = [t for t in tokenize(text) if not is_protected(spans, t[0], t[1])]
    found = []
    for i, j, e in _phrase_hits(toks, lex):
        found.append(_candidate(block.id, text, toks[i][0], toks[j - 1][1], e, lex))
    for start, end, word in toks:
        for e in lex.lookup_word(word):
            found.append(_candidate(block.id, text, start, end, e, lex))
        if not lex.lookup_word(word):
            row = _translit_hit(word, lex)
            if row:
                found.append({
                    "block": block.id, "start": start, "end": end, "match": word,
                    "type": "rusism", "level": "advice", "suggestions": [], "source": "slovnik1918",
                    "note": "написання збігається з російським словом у словнику 1918 р.; перевірити",
                    "slovnik": [{"head_ru": row["head_ru"], "uk": row["uk"]}],
                })
    found = [c for c in found
             if not _kept(c["match"], c["match"].split(), keep_singles, keep_phrases)]
    return _drop_overlaps(found)


def _drop_overlaps(found: list) -> list:
    """Keep the longest candidate among overlapping ones; one candidate per span."""
    kept = []
    for c in sorted(found, key=lambda c: (-(c["end"] - c["start"]), c["start"])):
        if all(c["end"] <= k["start"] or k["end"] <= c["start"] for k in kept):
            kept.append(c)
    return sorted(kept, key=lambda c: c["start"])


def scan_text(md: str, lex, keep: set, source: str = "") -> dict:
    blocks = split_blocks(md)
    keep_singles, keep_phrases = _keep_index(keep)
    candidates = []
    for b in blocks:
        if b.kind in SCANNED_KINDS:
            candidates.extend(scan_block(b, lex, keep_singles, keep_phrases))
    return {
        "source": source,
        "blocks": [{"id": b.id, "kind": b.kind, "text": b.text} for b in blocks],
        "candidates": candidates,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find russisms, calques and jargon in a Ukrainian text.")
    ap.add_argument("input")
    ap.add_argument("--keep", default="chysto-keep.txt", help="words/phrases never to flag")
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data"))
    ap.add_argument("-o", "--output", default="candidates.json")
    a = ap.parse_args(argv)
    md = Path(a.input).read_text(encoding="utf-8")
    result = scan_text(md, Lexicon.load(a.data), load_keep(a.keep), source=a.input)
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {}
    for c in result["candidates"]:
        counts[c["type"]] = counts.get(c["type"], 0) + 1
    print(f"{len(result['candidates'])} candidates {counts} -> {a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
