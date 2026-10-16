"""Build a small Lexicon from TSV strings for tests."""
import tempfile
from pathlib import Path

import _path  # noqa: F401
from lexicon import Lexicon

HEADERS = {
    "lt-replace.tsv": "pattern\tsuggestions\tlevel\tnote\n",
    "slovnik1918.tsv": "head_ru\tuk\tpage\tflags\n",
    "chysto-calques.tsv": "pattern\tsuggestions\tru_source\tlevel\tnote\n",
    "chysto-jargon.tsv": "pattern\tsuggestions\tnote\n",
}


def make_lex(lt="", soft="", calques="", jargon="", slovnik=""):
    """Each argument is TSV body rows (no header); soft rows are appended to lt with level=advice."""
    d = Path(tempfile.mkdtemp())
    bodies = {
        "lt-replace.tsv": lt + soft,
        "slovnik1918.tsv": slovnik,
        "chysto-calques.tsv": calques,
        "chysto-jargon.tsv": jargon,
    }
    for name, body in bodies.items():
        (d / name).write_text(HEADERS[name] + body, encoding="utf-8")
    return Lexicon.load(d)
