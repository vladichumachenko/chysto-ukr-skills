import unittest

from _path import REPO


class ReadmeTest(unittest.TestCase):
    def test_readmes_link_each_other_and_cover_sections(self):
        en = (REPO / "README.md").read_text(encoding="utf-8")
        uk = (REPO / "README.uk.md").read_text(encoding="utf-8")
        self.assertIn("README.uk.md", en.splitlines()[0])
        self.assertIn("README.md", uk.splitlines()[0])
        for s in ("npx skills add vladichumachenko/chysto-ukr-skills --skill chysto", "LanguageTool",
                  "1918", "MIT", "LGPL", "Vladyslav Chumachenko", "chysto-keep.txt"):
            self.assertIn(s, en)
            self.assertIn(s, uk)


if __name__ == "__main__":
    unittest.main()
