import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from lexhelper import make_lex
from lexicon import Lexicon, normalize, ru_to_uk_translit, stems


class NormalizeTest(unittest.TestCase):
    def test_case_and_combining_stress(self):
        self.assertEqual(normalize("Зада́чі"), "задачі")

    def test_latin_lookalike_stress(self):
        self.assertEqual(normalize("задáчі"), "задачі")

    def test_apostrophes_unified(self):
        self.assertEqual(normalize("п’ять"), normalize("пʼять"))
        self.assertEqual(normalize("п'ять"), normalize("пʼять"))


class StemsTest(unittest.TestCase):
    def test_includes_word_itself(self):
        self.assertIn("задачі", stems("задачі"))

    def test_strips_ending(self):
        self.assertIn("задач", stems("задачі"))

    def test_never_shorter_than_three(self):
        self.assertTrue(all(len(s) >= 3 for s in stems("ями") if s != "ями"))
        self.assertEqual(stems("по"), ["по"])

    def test_reflexive(self):
        self.assertIn("клад", stems("кладуться"))


class TranslitTest(unittest.TestCase):
    def test_translit(self):
        # mapping: и→і, ы→и, э→е, ъ→', ё→ьо, е kept; used only for low-confidence hints
        self.assertEqual(ru_to_uk_translit("быстрый"), "бистрий")
        self.assertEqual(ru_to_uk_translit("лист"), "ліст")


class LookupTest(unittest.TestCase):
    def test_inflected_form_finds_lemma_entry(self):
        lex = make_lex(lt="задача\tзавдання\terror\t\n")
        hits = lex.lookup_word("Задачі")
        self.assertEqual([h.suggestions for h in hits], [["завдання"]])
        self.assertEqual((hits[0].type, hits[0].level, hits[0].source), ("rusism", "error", "lt"))

    def test_short_words_do_not_overmatch(self):
        lex = make_lex(lt="поза\tза\terror\t\n")
        self.assertEqual(lex.lookup_word("потік"), [])

    def test_short_stem_does_not_collide(self):
        lex = make_lex(lt="вон\tгеть\terror\t\nкажись\tначе\terror\t\n")
        self.assertEqual(lex.lookup_word("вона"), [])
        self.assertEqual(lex.lookup_word("кажу"), [])

    def test_oblique_form_pattern_matches_exactly_only(self):
        lex = make_lex(lt="моделів\tмоделей\terror\t\n")
        self.assertEqual(lex.lookup_word("моделі"), [])
        self.assertEqual(len(lex.lookup_word("моделів")), 1)

    def test_one_and_two_letter_patterns_ignored(self):
        lex = make_lex(lt="в\tна\terror\t\nпо\tз\terror\t\n")
        self.assertEqual(lex.lookup_word("в"), [])
        self.assertEqual(lex.lookup_word("по"), [])

    def test_identity_suggestion_dropped(self):
        lex = make_lex(lt="туда\tтуди\terror\t\n")
        self.assertEqual(lex.lookup_word("туди"), [])

    def test_verb_forms_match_infinitive(self):
        lex = make_lex(calques="являтися\tбути\tявляться\terror\t\n", jargon="вливати\tmerge\t\n")
        for form in ("являється", "являються", "являвся"):
            self.assertEqual(len(lex.lookup_word(form)), 1, form)
        for form in ("вливаю", "вливає", "вливав", "вливаємо", "вливають"):
            self.assertEqual(len(lex.lookup_word(form)), 1, form)

    def test_advice_source(self):
        lex = make_lex(soft="айтішник\tайтівець\tadvice\t\n")
        self.assertEqual(lex.lookup_word("айтішник")[0].source, "lt-soft")

    def test_phrases(self):
        lex = make_lex(lt="в силу обставин\tчерез обставини\terror\tВ силу цього\n",
                       calques="так от\tотож\tтак вот\terror\t\n",
                       jargon="покласти прод\tзламати production\t\n")
        by_pattern = {e.pattern: e for e in lex.phrases()}
        self.assertEqual(by_pattern["в силу обставин"].type, "calque")
        self.assertEqual((by_pattern["так от"].type, by_pattern["так от"].source), ("calque", "chysto"))
        self.assertEqual((by_pattern["покласти прод"].type, by_pattern["покласти прод"].level), ("jargon", "error"))
        self.assertEqual(lex.lookup_word("в"), [])

    def test_single_word_jargon(self):
        lex = make_lex(jargon="прод\tproduction|prod\t\n")
        self.assertEqual(lex.lookup_word("проду")[0].type, "jargon")

    def test_slovnik_for_combined_heads(self):
        lex = make_lex(slovnik="безмолвный, но\tбезмо́вний, мовчазний\t20\t\n")
        self.assertEqual(lex.slovnik_for("Безмолвный")[0]["uk"], "безмо́вний, мовчазний")

    def test_translit_index(self):
        lex = make_lex(slovnik="следующий\tнаступний\t400\t\n")
        self.assertIn("следующій", lex.slovnik_translit_index())

    def test_missing_optional_files(self):
        d = Path(tempfile.mkdtemp())
        (d / "lt-replace.tsv").write_text("pattern\tsuggestions\tlevel\tnote\nзадача\tзавдання\terror\t\n")
        self.assertEqual(len(Lexicon.load(d).lookup_word("задача")), 1)


if __name__ == "__main__":
    unittest.main()
