import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _path
from lexhelper import make_lex
from scan import scan_text

LT = "задача\tзавдання\terror\t\n"
SOFT = "за замовчуванням\tтипово\tadvice\t\n"
CALQUES = "взяте зі стелі\tвисмоктане з пальця\tвзято с потолка\terror\t\n"
SLOVNIK = "задача\tзада́ча, завда́ння\t100\t\nследующий\tнасту́пний\t400\t\n"


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.lex = make_lex(lt=LT, soft=SOFT, calques=CALQUES, slovnik=SLOVNIK)

    def matches(self, md, keep=frozenset()):
        return [c["match"] for c in scan_text(md, self.lex, keep=set(keep))["candidates"]]

    def test_word_and_phrase_candidates(self):
        m = self.matches("Зараз задачі кладуться в чергу. Число не взяте зі стелі.\n")
        self.assertIn("задачі", m)
        self.assertIn("взяте зі стелі", m)

    def test_offsets_point_into_block_text(self):
        out = scan_text("Ці задачі.\n", self.lex, keep=set())
        x = out["candidates"][0]
        self.assertEqual(out["blocks"][x["block"]]["text"][x["start"]:x["end"]], x["match"])

    def test_protected_spans_and_code_blocks_ignored(self):
        md = "Текст `задача` і $задача$ https://x.ua/задача\n\n```\nзадача\n```\n"
        self.assertEqual(self.matches(md), [])

    def test_keep_list_suppresses(self):
        lex = make_lex(lt="лайнап\tчерга\terror\t\n")
        out = scan_text("Я сиджу в лайнапі.\n", lex, keep={"лайнап"})
        self.assertEqual(out["candidates"], [])

    def test_advice_level_preserved(self):
        c = scan_text("Типове значення за замовчуванням.\n", self.lex, keep=set())["candidates"]
        self.assertEqual({x["level"] for x in c if x["match"] == "за замовчуванням"}, {"advice"})

    def test_overlap_keeps_longest(self):
        lex = make_lex(calques="взяте зі стелі\tз пальця\t\terror\t\n", lt="стеля\tсуфіт\terror\t\n")
        c = scan_text("Не взяте зі стелі.\n", lex, keep=set())["candidates"]
        self.assertEqual([x["match"] for x in c], ["взяте зі стелі"])

    def test_capitalised_match_keeps_original_text(self):
        self.assertEqual(self.matches("Задачі тут.\n"), ["Задачі"])

    def test_slovnik_rows_attached_via_suggestion(self):
        c = scan_text("Ці задачі.\n", self.lex, keep=set())["candidates"][0]
        self.assertEqual(c["slovnik"][0]["head_ru"], "задача")

    def test_translit_hit_flags_surzhyk_spelling(self):
        lex = make_lex(slovnik="следующій\tнасту\u0301пний\t400\t\n")
        c = scan_text("Ось следующій крок.\n", lex, keep=set())["candidates"]
        self.assertEqual([(x["match"], x["source"], x["level"]) for x in c],
                         [("следующій", "slovnik1918", "advice")])

    def test_translit_skips_words_known_as_ukrainian(self):
        lex = make_lex(slovnik="безпека\tнедба\u0301лиця\t21\t\nбезопасность\tбезпе\u0301ка\t21\t\n")
        self.assertEqual(scan_text("Безпека продакшену.\n", lex, keep=set())["candidates"], [])

    def test_candidate_fields(self):
        c = scan_text("Ці задачі.\n", self.lex, keep=set())["candidates"][0]
        self.assertEqual(set(c), {"block", "start", "end", "match", "type", "level", "suggestions",
                                  "source", "note", "slovnik"})


class ScanCliTest(unittest.TestCase):
    def test_cli_writes_json(self):
        d = Path(tempfile.mkdtemp())
        (d / "a.md").write_text("Ці задачі.\n", encoding="utf-8")
        rc = subprocess.run([sys.executable, str(_path.SCRIPTS / "scan.py"), str(d / "a.md"),
                             "-o", str(d / "c.json")], capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, rc.stderr)
        out = json.loads((d / "c.json").read_text(encoding="utf-8"))
        self.assertEqual(out["source"], str(d / "a.md"))
        self.assertIn("blocks", out)


if __name__ == "__main__":
    unittest.main()
