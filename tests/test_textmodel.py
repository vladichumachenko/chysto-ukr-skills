import unittest

import _path  # noqa: F401
from textmodel import join_blocks, protected_spans, split_blocks


class TextModelTest(unittest.TestCase):
    def test_roundtrip_is_exact(self):
        md = "# Title\n\nPara one.\nline two\n\n```go\nx := задача\n```\n\nPara `задача` two.\n"
        self.assertEqual(join_blocks(split_blocks(md)), md)

    def test_roundtrip_without_trailing_newline_and_extra_blanks(self):
        md = "a\n\n\n\nb"
        self.assertEqual(join_blocks(split_blocks(md)), md)

    def test_code_fence_is_one_code_block(self):
        kinds = [b.kind for b in split_blocks("a\n\n```\nb\n\nc\n```\n")]
        self.assertIn("code", kinds)
        self.assertEqual(sum(k == "code" for k in kinds), 1)

    def test_heading_kind(self):
        self.assertEqual(split_blocks("## Де я\n")[0].kind, "heading")

    def test_block_ids_are_positions(self):
        blocks = split_blocks("a\n\nb\n")
        self.assertEqual([b.id for b in blocks], list(range(len(blocks))))

    def test_protected_spans_cover_inline_code_math_url(self):
        t = "x `задача` y $P=ρ$ z https://ex.com/задача w [лінк](https://a.ua/задача)"
        spans = protected_spans(t)
        for frag in ("`задача`", "$P=ρ$", "https://ex.com/задача", "https://a.ua/задача"):
            s = t.index(frag)
            self.assertTrue(any(a <= s and s + len(frag) <= b for a, b in spans), frag)

    def test_plain_text_has_no_spans(self):
        self.assertEqual(protected_spans("просто текст без коду"), [])


if __name__ == "__main__":
    unittest.main()


class FenceTest(unittest.TestCase):
    def kinds_with(self, md, word="задача"):
        return [b.kind for b in split_blocks(md) if word in b.text]

    def test_nested_fence_four_backticks(self):
        md = "Текст.\n\n````md\n```go\nзадача\n```\n````\n\nКінець.\n"
        self.assertEqual(self.kinds_with(md), ["code"])
        self.assertEqual(join_blocks(split_blocks(md)), md)

    def test_indented_code_block(self):
        md = "Текст.\n\n    задача := 1\n    ще рядок\n\nКінець.\n"
        self.assertEqual(self.kinds_with(md), ["code"])

    def test_fence_inside_list_item(self):
        md = "- пункт\n\n  ```\n  задача\n\n  ще\n  ```\n\nКінець.\n"
        self.assertEqual(self.kinds_with(md), ["code"])

    def test_fence_inside_blockquote(self):
        md = "> цитата\n>\n> ```\n> задача\n> ```\n"
        self.assertNotIn("text", self.kinds_with(md))

    def test_crlf_roundtrip(self):
        md = "Рядок один.\r\n\r\n```\r\nзадача\r\n```\r\n"
        self.assertEqual(join_blocks(split_blocks(md)), md)
        self.assertEqual(self.kinds_with(md), ["code"])
