"""Bundled lexicon: LanguageTool replacements, chysto lists and the 1918 dictionary.

Matching is deliberately crude (normalisation + one stripped ending): the scanner aims
for recall, and the agent decides which candidates are real problems.
"""
import csv
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ACUTE = "́"
LATIN_STRESSED = {"á": "а", "ó": "о", "é": "е", "ý": "у", "í": "і",
                  "Á": "А", "Ó": "О", "É": "Е", "Ý": "У", "Í": "І"}
APOSTROPHES = {"’": "'", "ʼ": "'", "`": "'", "‘": "'"}

# Common Ukrainian inflectional endings (nominal and verbal). Every matching ending yields
# one candidate stem, so «школа»/«школи» share «школ» and «вливати»/«вливаю» share «влива».
ENDINGS = sorted("ами ями ові еві ого ому ими іми ій ої ою ею ів їв ах ях ам ям ом ем им ім ий "
                 "ти ють ять уть ать ємо имо емо єте ете ите ає ла ло ли "
                 "а я у ю і ї е є о и в".split(), key=len, reverse=True)
REFLEXIVE = ("ться", "ся", "сь")
MIN_STEM = 3
MIN_MATCH_STEM = 4      # shorter shared stems collide (вона/вон, кажу/кажись)
MIN_PATTERN_LEN = 3     # one- and two-letter LT patterns are context rules, unusable here
# A pattern may match other forms only if it looks like a dictionary form; patterns in
# oblique cases (моделів, статтів) are form-specific errors and match exactly.
OBLIQUE_ENDINGS = ("ів", "їв", "ами", "ями", "ах", "ях", "ові", "еві", "ого", "ому", "ими", "іми",
                   "ою", "ею", "ам", "ям", "ом", "ем", "им", "ім", "ої")

TRANSLIT = {"и": "і", "ы": "и", "э": "е", "ъ": "'", "ё": "ьо"}
WORD_RX = re.compile(r"[\w'’ʼ́-]+", re.U)


def normalize(s: str) -> str:
    """Lower-case, drop stress marks (combining or Latin look-alikes), unify apostrophes."""
    s = "".join(LATIN_STRESSED.get(c, c) for c in s)
    s = unicodedata.normalize("NFD", s).replace(ACUTE, "")
    s = unicodedata.normalize("NFC", s).lower()
    return "".join(APOSTROPHES.get(c, c) for c in s)


def stems(word: str) -> list:
    """The normalized word plus its forms with a reflexive suffix and/or one ending removed.

    Every ending that fits produces a stem (not only the longest), never shorter than MIN_STEM.
    """
    w = normalize(word)
    out = [w]
    bases = [w]
    for r in REFLEXIVE:
        if w.endswith(r) and len(w) - len(r) >= MIN_STEM:
            bases.append(w[: -len(r)])
            break
    for b in bases:
        if b not in out:
            out.append(b)
        for e in ENDINGS:
            if b.endswith(e) and len(b) - len(e) >= MIN_STEM:
                out.append(b[: -len(e)])
    return list(dict.fromkeys(out))


def ru_to_uk_translit(word: str) -> str:
    """Spell a Russian word with Ukrainian letters, the way surzhyk usually does."""
    return "".join(TRANSLIT.get(c, c) for c in normalize(word))


def words(text: str) -> list:
    return WORD_RX.findall(text)


@dataclass
class Entry:
    pattern: str
    suggestions: list
    type: str     # rusism | calque | jargon
    level: str    # error | advice
    source: str   # lt | lt-soft | chysto | slovnik1918
    note: str = ""
    ru_source: str = ""


@dataclass
class Lexicon:
    singles: dict = field(default_factory=dict)   # stem -> [Entry] (lemma-like patterns only)
    exact: dict = field(default_factory=dict)     # normalized pattern -> [Entry]
    multi: list = field(default_factory=list)     # [Entry] with multi-word patterns
    slovnik: dict = field(default_factory=dict)   # normalized ru head -> [row dict]
    _translit: dict = None
    _by_uk: dict = None

    @classmethod
    def load(cls, data_dir) -> "Lexicon":
        d = Path(data_dir)
        lex = cls()
        for row in _read(d / "lt-replace.tsv"):
            single = len(row["pattern"].split()) == 1
            lex._add(Entry(row["pattern"], _alts(row["suggestions"]), "rusism" if single else "calque",
                           row["level"], "lt" if row["level"] == "error" else "lt-soft", row.get("note", "")))
        for row in _read(d / "chysto-calques.tsv"):
            lex._add(Entry(row["pattern"], _alts(row["suggestions"]), "calque", row.get("level") or "error",
                           "chysto", row.get("note", ""), row.get("ru_source", "")))
        for row in _read(d / "chysto-jargon.tsv"):
            lex._add(Entry(row["pattern"], _alts(row["suggestions"]), "jargon", "error", "chysto",
                           row.get("note", "")))
        for row in _read(d / "slovnik1918.tsv"):
            for head in _heads(row["head_ru"]):
                lex.slovnik.setdefault(head, []).append(row)
        return lex

    def _add(self, e: Entry) -> None:
        toks = words(e.pattern)
        if len(toks) > 1:
            self.multi.append(e)
        elif toks:
            w = normalize(toks[0])
            if len(w) < MIN_PATTERN_LEN:
                return
            self.exact.setdefault(w, []).append(e)
            if not w.endswith(OBLIQUE_ENDINGS):
                for s in stems(w):
                    if len(s) >= MIN_MATCH_STEM:
                        self.singles.setdefault(s, []).append(e)

    def lookup_word(self, word: str) -> list:
        """Single-word entries matching word exactly or by a shared stem of >= 4 letters.

        Entries whose only suggestion is the word itself (e.g. «туда» -> «туди» found on «туди»)
        are dropped.
        """
        w = normalize(word)
        seen, out = set(), []
        pools = [self.exact.get(w, [])] + [self.singles.get(s, []) for s in stems(w)
                                           if len(s) >= MIN_MATCH_STEM]
        for pool in pools:
            for e in pool:
                if id(e) in seen:
                    continue
                seen.add(id(e))
                if all(normalize(s) == w for s in e.suggestions):
                    continue
                out.append(e)
        return out

    def phrases(self) -> list:
        return list(self.multi)

    def slovnik_for(self, ru_head: str) -> list:
        return list(self.slovnik.get(normalize(ru_head), []))

    def slovnik_translit_index(self) -> dict:
        """Ukrainian-letter spelling of each 1918 headword -> its rows (built once)."""
        if self._translit is None:
            self._translit = {}
            for head, rows in self.slovnik.items():
                self._translit.setdefault(ru_to_uk_translit(head), []).extend(rows)
        return self._translit


    def slovnik_by_uk(self, word: str) -> list:
        """1918 rows whose Ukrainian side contains word (normalized, exact token match)."""
        if self._by_uk is None:
            self._by_uk = {}
            for rows in self.slovnik.values():
                for row in rows:
                    for w in set(normalize(t) for t in words(row["uk"])):
                        bucket = self._by_uk.setdefault(w, [])
                        if not bucket or bucket[-1] is not row:
                            bucket.append(row)
        return list(self._by_uk.get(normalize(word), []))


def _read(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE) if r.get("pattern", r.get("head_ru"))]


def _alts(cell: str) -> list:
    return [a.strip() for a in (cell or "").split("|") if a.strip()]


def _heads(cell: str) -> list:
    """'безмолвный, но' -> ['безмолвный']; drops grammatical tails like 'но', 'ся', 'ца'."""
    parts = [normalize(p.strip()) for p in cell.split(",")]
    return [p for p in parts if len(p) >= MIN_STEM and " " not in p]
