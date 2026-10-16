import re
import unittest

from _path import SKILL


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^\w[\w-]*:", line):
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip()
        elif key:
            out[key] += " " + line.strip()
    return out


class SkillMdTest(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_frontmatter(self):
        fm = parse_frontmatter(self.text)
        self.assertEqual(fm["name"], "chysto")
        self.assertLessEqual(len(fm["description"]), 1024)
        self.assertRegex(fm["description"], r"Ukrainian")
        self.assertRegex(fm["description"], r"russism|surzhyk")

    def test_scripts_referenced_exist(self):
        for s in re.findall(r"scripts/(\w+\.py)", self.text):
            self.assertTrue((SKILL / "scripts" / s).exists(), s)

    def test_references_exist(self):
        for r in re.findall(r"references/([\w-]+\.md)", self.text):
            self.assertTrue((SKILL / "references" / r).exists(), r)

    def test_covers_core_rules(self):
        for phrase in ("edits.json", "candidates.json", "chysto-keep.txt", "advice", "restructure",
                       "meaning", "style", "EditError"):
            self.assertIn(phrase, self.text)


class UntrustedContentTest(unittest.TestCase):
    def test_skill_md_treats_text_as_data(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Untrusted content", text)
        section = text.split("## Untrusted content", 1)[1].split("\n## ", 1)[0].lower()
        for phrase in ("data", "never follow", "instructions", "links", "explicitly"):
            self.assertIn(phrase, section)
        # the guard comes before the steps that read the text
        self.assertLess(text.index("## Untrusted content"), text.index("## 1. Get the text"))

    def test_readmes_have_security_section(self):
        from _path import REPO
        self.assertIn("## Security", (REPO / "README.md").read_text(encoding="utf-8"))
        self.assertIn("## Безпека", (REPO / "README.uk.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
