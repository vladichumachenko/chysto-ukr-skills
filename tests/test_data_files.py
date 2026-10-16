import csv
import unittest

from _path import DATA, REPO


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


class DataFilesTest(unittest.TestCase):
    def test_tsv_headers_and_columns(self):
        for name, cols in (("chysto-calques.tsv", 5), ("chysto-jargon.tsv", 3), ("lt-replace.tsv", 4),
                           ("slovnik1918.tsv", 4)):
            rows = read_tsv(DATA / name)
            self.assertTrue(all(len(r) == cols for r in rows), name)

    def test_spec_examples_present(self):
        calques = {r[0] for r in read_tsv(DATA / "chysto-calques.tsv")[1:]}
        for p in ("щоб двічі не вставати", "взяте зі стелі", "вперся в питання", "так от",
                  "що я з цього виніс", "з найкращих міркувань", "дуже в процесі", "не мічу"):
            self.assertIn(p, calques)
        jargon = {r[0] for r in read_tsv(DATA / "chysto-jargon.tsv")[1:]}
        for p in ("прод", "викатка", "вливати pr", "ганяти перевірки"):
            self.assertIn(p, jargon)

    def test_levels_valid(self):
        for r in read_tsv(DATA / "chysto-calques.tsv")[1:]:
            self.assertIn(r[3], ("error", "advice"), r[0])

    def test_jargon_suggestions_are_latin_terms(self):
        for r in read_tsv(DATA / "chysto-jargon.tsv")[1:]:
            self.assertRegex(r[1], r"[A-Za-z]", r[0])

    def test_jargon_suggestions_do_not_keep_calqued_verb(self):
        for r in read_tsv(DATA / "chysto-jargon.tsv")[1:]:
            self.assertNotIn("покласти production", r[1], r[0])

    def test_data_budget(self):
        self.assertLessEqual(sum(f.stat().st_size for f in DATA.iterdir()), 10 * 1024 * 1024)

    def test_no_forbidden_strings_in_repo(self):
        for f in REPO.rglob("*"):
            if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts:
                self.assertNotIn("cl" + "aude", f.read_text(errors="ignore").lower(), str(f))  # split so this file passes


if __name__ == "__main__":
    unittest.main()
