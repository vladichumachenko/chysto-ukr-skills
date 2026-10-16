import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _path
from render import render_html

EDIT_ERROR = dict(id=1, block=0, before="задачі", after="завдання", type="rusism",
                  level="error", reason="task = «завдання»", source="lt")
EDIT_ERROR_ZADACHI = EDIT_ERROR
EDIT_ADVICE = dict(id=1, block=0, before="за замовчуванням", after="типово", type="rusism",
                   level="advice", reason="пуристська заміна", source="lt-soft")


class RenderHtmlTest(unittest.TestCase):
    def test_inline_diff_and_footnote(self):
        h = render_html("Зараз задачі тут.\n", [EDIT_ERROR], "t")
        self.assertIn('<del class="ch-del">задачі</del>', h)
        self.assertIn('<ins class="ch-ins">завдання</ins><sup>1</sup>', h)
        self.assertIn("русизм", h)        # Ukrainian label of type
        self.assertIn("помилка", h)       # Ukrainian label of level
        self.assertIn("task = «завдання»", h)

    def test_advice_shown_but_not_struck(self):
        h = render_html("Ось за замовчуванням.\n", [EDIT_ADVICE], "t")
        self.assertIn('class="ch-advice"', h)
        self.assertNotIn("<del", h)
        self.assertIn("порада", h)
        self.assertIn("типово", h)

    def test_escaping(self):
        h = render_html("a < b & c задачі\n", [EDIT_ERROR_ZADACHI], "t")
        self.assertIn("a &lt; b &amp; c", h)

    def test_self_contained(self):
        h = render_html("x\n", [], "t")
        for bad in ("<script src", "<link ", "http://", "https://"):
            self.assertNotIn(bad, h)

    def test_summary_counts(self):
        h = render_html("Зараз задачі тут.\n", [EDIT_ERROR], "t")
        self.assertRegex(h, r"русизм[^<]*1")

    def test_headings_and_code_blocks(self):
        h = render_html("## Де я\n\n```go\nx := <1>\n```\n", [], "t")
        self.assertIn("<h2>Де я</h2>", h)
        self.assertIn("<pre>", h)
        self.assertIn("x := &lt;1&gt;", h)

    def test_footnotes_numbered_in_document_order(self):
        md = "Перший кладуться.\n\nДругий задачі.\n"
        edits = [dict(EDIT_ERROR, id=9, block=2),
                 dict(EDIT_ERROR, id=4, block=0, before="кладуться", after="потрапляють")]
        h = render_html(md, edits, "t")
        self.assertLess(h.index("потрапляють</ins><sup>1</sup>"), h.index("завдання</ins><sup>2</sup>"))


class RenderCliTest(unittest.TestCase):
    def run_cli(self, md, edits):
        d = Path(tempfile.mkdtemp())
        (d / "a.md").write_text(md, encoding="utf-8")
        (d / "e.json").write_text(json.dumps(edits, ensure_ascii=False), encoding="utf-8")
        p = subprocess.run([sys.executable, str(_path.SCRIPTS / "render.py"), str(d / "a.md"), str(d / "e.json")],
                           capture_output=True, text=True)
        return d, p

    def test_writes_fixed_and_review(self):
        d, p = self.run_cli("Зараз задачі тут.\n", [EDIT_ERROR])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual((d / "a.fixed.md").read_text(encoding="utf-8"), "Зараз завдання тут.\n")
        self.assertIn("ch-ins", (d / "a.review.html").read_text(encoding="utf-8"))

    def test_invalid_edits_write_nothing(self):
        d, p = self.run_cli("Зараз тут.\n", [EDIT_ERROR])
        self.assertEqual(p.returncode, 1)
        self.assertIn("edit 1", p.stderr)
        self.assertFalse((d / "a.fixed.md").exists())
        self.assertFalse((d / "a.review.html").exists())


if __name__ == "__main__":
    unittest.main()
