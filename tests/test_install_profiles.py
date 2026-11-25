import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock


SUITE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lj_installer", SUITE / "scripts/install_skills.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallProfileTests(unittest.TestCase):
    def assert_local_links_resolve(self, dest):
        markdown = (
            list(dest.glob("lj-*/SKILL.md"))
            + list(dest.glob("lj-*/references/**/*.md"))
            + list((dest / "templates").glob("*.md"))
        )
        for document in markdown:
            text = document.read_text(encoding="utf-8")
            for raw in re.findall(r"\]\(([^)]+)\)", text):
                target = raw.split("#", 1)[0]
                if not target or "://" in target or target.startswith("#"):
                    continue
                self.assertTrue((document.parent / target).exists(),
                                f"broken installed link in {document}: {raw}")

    def test_inventory_profiles_are_exact_and_self_contained(self):
        data = installer.inventory()
        self.assertEqual(len(data["profiles"]["core"]), 7)
        self.assertEqual(len(data["profiles"]["full"]), 12)
        self.assertEqual(set(data["profiles"]["full"]),
                         set(data["profiles"]["core"]) | set(data["optional"]))
        self.assertNotIn("legacy", data["profiles"])
        with self.assertRaises(ValueError):
            installer.selected_names(data, "legacy", [])

    def test_core_copy_has_seven_self_contained_entrypoints_and_templates(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            installer.install_dest(dest, data["profiles"]["core"], "copy", False, False, data)
            entries = sorted(path.parent.name for path in dest.glob("lj-*/SKILL.md"))
            self.assertEqual(entries, sorted(data["profiles"]["core"]))
            self.assertTrue((dest / "lj-question/references/question-engine.md").is_file())
            self.assertTrue((dest / "lj-question/references/roam-engine.md").is_file())
            self.assertTrue((dest / "lj-evidence/scripts/fetch_oa.py").is_file())
            self.assertTrue((dest / "lj-evidence/scripts/pdf_to_md.py").is_file())
            self.assertTrue((dest / "lj-read/references/paper-engine.md").is_file())
            self.assertFalse((dest / "lj-ask").exists())
            self.assertFalse((dest / "lj-wiki").exists())
            self.assertTrue((dest / "templates/delegation.md").is_file())
            self.assertTrue((dest / "templates/references/delegation-brief.md").is_file())
            self.assertTrue((dest / "templates/scripts/validate_blindspot.py").is_file())

    def test_profile_switch_and_uninstall_preserve_unknown_files(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            installer.install_dest(dest, data["profiles"]["core"], "copy", False, False, data)
            unknown = dest / "unrelated.txt"
            unknown.write_text("keep", encoding="utf-8")
            installer.install_dest(dest, data["profiles"]["full"], "copy", False, False, data)
            self.assertEqual(len(list(dest.glob("lj-*/SKILL.md"))), 12)
            self.assertTrue((dest / "lj-concept/references/weave-engine.md").is_file())
            installer.install_dest(dest, [], "copy", True, False, data)
            self.assertEqual(unknown.read_text(encoding="utf-8"), "keep")
            self.assertEqual(list(dest.glob("lj-*")), [])

    def test_pycache_does_not_falsely_flag_modified_managed_copy(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            installer.install_dest(dest, data["profiles"]["core"], "copy", False, False, data)
            cache_dir = dest / "lj-viz" / "scripts" / "__pycache__"
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "validate_manifest.cpython-312.pyc").write_bytes(b"bytecode")
            installer.install_dest(dest, data["profiles"]["full"], "copy", False, False, data)
            self.assertEqual(len(list(dest.glob("lj-*/SKILL.md"))), 12)

    def test_modified_managed_copy_is_not_overwritten(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            installer.install_dest(dest, data["profiles"]["core"], "copy", False, False, data)
            (dest / "lj-design/user-note.txt").write_text("mine", encoding="utf-8")
            evidence_marker = dest / "lj-evidence/SKILL.md"
            with self.assertRaisesRegex(RuntimeError, "modified managed directory"):
                installer.install_dest(dest, data["profiles"]["full"], "copy", False, False, data)
            self.assertTrue(evidence_marker.is_file(), "preflight must fail before any mutation")

    def test_retired_managed_directories_are_pruned_cleanly(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            installer.install_dest(dest, data["profiles"]["core"], "copy", False, False, data)
            retired = dest / "lj-wiki"
            retired.mkdir()
            (retired / "SKILL.md").write_text("old", encoding="utf-8")
            state_path = dest / installer.STATE_NAME
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["managed"]["lj-wiki"] = {
                "mode": "copy",
                "source": str(SUITE / "lj-wiki"),
                "digest": installer.tree_digest(retired),
            }
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            installer.install_dest(dest, data["profiles"]["full"], "copy", False, False, data)
            self.assertFalse(retired.exists())

    def test_adopt_existing_accepts_exact_repo_link_and_rejects_foreign_link(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            dest.mkdir()
            installer.create_link(SUITE / "lj-design", dest / "lj-design")
            installer.install_dest(dest, data["profiles"]["core"], "link", False, False,
                                   data, adopt_existing=True)
            state = json.loads((dest / installer.STATE_NAME).read_text(encoding="utf-8"))
            self.assertIn("lj-design", state["managed"])
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            foreign = Path(temp) / "foreign"
            dest.mkdir()
            foreign.mkdir()
            installer.create_link(foreign, dest / "lj-design")
            with self.assertRaisesRegex(RuntimeError, "unknown target"):
                installer.install_dest(dest, data["profiles"]["core"], "link", False, False,
                                       data, adopt_existing=True)

    def test_state_cannot_escape_destination(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            dest.mkdir()
            (dest / installer.STATE_NAME).write_text(
                json.dumps({"schema_version": 1, "managed": {"../escape": {"mode": "copy"}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "unsafe managed name"):
                installer.install_dest(dest, data["profiles"]["core"], "copy", False, False, data)

    def test_all_profiles_have_closed_local_links(self):
        data = installer.inventory()
        for profile in ("core", "full"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp) / "skills"
                installer.install_dest(dest, data["profiles"][profile], "copy", False, False, data)
                self.assert_local_links_resolve(dest)

    def test_main_auto_detects_antigravity_skills_dir(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing_claude = root / "missing-claude" / "skills"
            missing_codex = root / "missing-codex" / "skills"
            agy_parent = root / "gemini-config"
            agy_parent.mkdir()
            agy_skills = agy_parent / "skills"
            env = {
                "CLAUDE_SKILLS_DIR": str(missing_claude),
                "CODEX_SKILLS_DIR": str(missing_codex),
                "ANTIGRAVITY_SKILLS_DIR": str(agy_skills),
            }
            with mock.patch.dict(os.environ, env, clear=False), \
                 mock.patch.object(installer, "install_dest") as install_mock:
                rc = installer.main(["copy", "--profile", "core", "--dry-run"])
            self.assertEqual(rc, 0)
            install_mock.assert_called_once()
            self.assertEqual(install_mock.call_args.args[0], agy_skills.resolve())


if __name__ == "__main__":
    unittest.main()
