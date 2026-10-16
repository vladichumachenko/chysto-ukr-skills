import unittest

import _path  # noqa: F401
from render import EditError, apply_edits, validate_edits
from textmodel import split_blocks

MD = "Зараз задачі кладуться в чергу.\n\n```\nзадачі кладуться\n```\n"


def edit(**kw):
    base = dict(id=1, block=0, before="задачі", after="завдання", type="rusism",
                level="error", reason="r", source="lt")
    base.update(kw)
    return base


class ApplyTest(unittest.TestCase):
    def test_apply_error_edit(self):
        e = [edit(before="задачі кладуться", after="завдання потрапляють")]
        self.assertEqual(apply_edits(MD, e), MD.replace("задачі кладуться в", "завдання потрапляють в", 1))

    def test_advice_not_applied(self):
        self.assertEqual(apply_edits(MD, [edit(level="advice", source="lt-soft")]), MD)

    def test_edit_into_code_block_rejected(self):
        with self.assertRaisesRegex(EditError, r"edit 1"):
            apply_edits(MD, [edit(block=2)])

    def test_ambiguous_before_rejected(self):
        with self.assertRaisesRegex(EditError, r"edit 7.*2 times"):
            apply_edits("так от, так от\n", [edit(id=7, before="так от", after="отож", type="calque",
                                                  source="chysto")])

    def test_missing_before_rejected(self):
        with self.assertRaisesRegex(EditError, r"edit 3.*not found"):
            apply_edits("abc\n", [edit(id=3, before="xyz", after="q")])

    def test_inside_inline_code_rejected(self):
        with self.assertRaises(EditError):
            apply_edits("Ось `задачі` тут\n", [edit(id=4)])

    def test_overlapping_edits_rejected(self):
        with self.assertRaisesRegex(EditError, r"overlap"):
            apply_edits("Зараз задачі кладуться.\n",
                        [edit(id=1, before="задачі кладуться", after="x"), edit(id=2, before="кладуться", after="y")])

    def test_several_edits_in_one_block(self):
        out = apply_edits("Перша задачі, друга кладуться.\n",
                          [edit(id=1), edit(id=2, before="кладуться", after="потрапляють")])
        self.assertEqual(out, "Перша завдання, друга потрапляють.\n")

    def test_validation_happens_before_any_change(self):
        with self.assertRaises(EditError):
            apply_edits(MD, [edit(id=1), edit(id=2, before="немає")])

    def test_unknown_type_or_level_rejected(self):
        with self.assertRaisesRegex(EditError, r"edit 1.*type"):
            validate_edits(split_blocks(MD), [edit(type="style")])
        with self.assertRaisesRegex(EditError, r"edit 1.*level"):
            validate_edits(split_blocks(MD), [edit(level="maybe")])

    def test_bad_block_id_rejected(self):
        with self.assertRaisesRegex(EditError, r"edit 1.*block"):
            apply_edits(MD, [edit(block=99)])


class MarkupAndInputTest(unittest.TestCase):
    def test_edit_cannot_eat_heading_marker(self):
        with self.assertRaisesRegex(EditError, r"edit 1.*markup"):
            apply_edits("## Так от\n", [edit(before="## Так", after="Отож", type="calque")])

    def test_edit_cannot_eat_list_marker(self):
        with self.assertRaisesRegex(EditError, r"edit 1.*markup"):
            apply_edits("- задачі тут\n", [edit(before="- задачі")])

    def test_error_edit_without_after_rejected(self):
        e = edit()
        del e["after"]
        with self.assertRaisesRegex(EditError, r"edit 1.*after"):
            apply_edits("Ці задачі.\n", [e])

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(EditError, r"edit 1.*duplicate"):
            apply_edits("Ці задачі кладуться.\n", [edit(), edit(before="кладуться", after="x")])

    def test_crlf_preserved(self):
        md = "Ці задачі.\r\n\r\nДругий.\r\n"
        self.assertEqual(apply_edits(md, [edit()]), "Ці завдання.\r\n\r\nДругий.\r\n")


if __name__ == "__main__":
    unittest.main()
