import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("save_note", ROOT / "_shared/save_note.py")
notes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notes)


class NoteOutputTests(unittest.TestCase):
    def test_unicode_filename_time_conversion_and_provenance_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = notes.save_note("# 判断\n\n观察不等于推断。", "观察/解释：区别?", "lj-reframe",
                                   Path(temp), ["https://example.org/original"],
                                   {"coverage": "partial"}, datetime(2026, 10, 20, 7, 30, tzinfo=timezone.utc))
            self.assertEqual(path.name, "20261020T153000--观察-解释：区别__reframe.md")
            text = path.read_text(encoding="utf-8")
            self.assertIn('date: "2026-10-20T15:30:00+08:00"', text)
            self.assertIn('coverage: "partial"', text)
            self.assertIn('https://example.org/original', text)
            self.assertTrue(text.endswith("观察不等于推断。\n"))
            self.assertEqual(len(list(Path(temp).iterdir())), 1)

    def test_same_second_different_title_cannot_duplicate_or_overwrite_identifier(self):
        with tempfile.TemporaryDirectory() as temp:
            time = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
            first = notes.save_note("原文", "第一篇", "lj-read", Path(temp), now=time)
            with self.assertRaises(FileExistsError):
                notes.save_note("新文", "另一篇", "lj-reframe", Path(temp), now=time)
            self.assertIn("原文", first.read_text(encoding="utf-8"))
            self.assertEqual(len(list(Path(temp).iterdir())), 1)

    def test_unsafe_or_incomplete_input_cannot_create_a_note(self):
        with tempfile.TemporaryDirectory() as temp:
            for kwargs in ({"body": ""}, {"title": "<>:/"}, {"skill": "../lj-read"},
                           {"metadata": {"identifier": "spoofed"}}, {"body": "---\ntitle: existing\n---"},
                           {"now": datetime(2026, 10, 20)}):
                params = {"body": "正文", "title": "主题", "skill": "lj-read", "dest": Path(temp)}
                params.update(kwargs)
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    notes.save_note(**params)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_every_entrypoint_and_compat_copy_can_resolve_output_contract(self):
        for entry in ROOT.glob("lj-*/SKILL.md"):
            with self.subTest(entry=entry.parent.name):
                self.assertIn("../_shared/note-output.md", entry.read_text(encoding="utf-8"))
                self.assertTrue((entry.parent / "../_shared/note-output.md").is_file())
        settings = json.loads((ROOT / "_shared/note-settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["windows_directory"], "~/Documents/lj-notes")
        self.assertEqual(settings["env_override"], "LJ_NOTES_DIR")


if __name__ == "__main__":
    unittest.main()
