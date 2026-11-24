"""Independent acceptance tests for profile migration and installed resource closure."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock


SUITE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lj_installer_migration_acceptance", SUITE / "scripts/install_skills.py"
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def entrypoints(dest: Path) -> list[str]:
    return sorted(path.parent.name for path in dest.rglob("SKILL.md"))


def remove_directory_link(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    else:
        os.rmdir(path)


class InstallMigrationAcceptanceTests(unittest.TestCase):
    def assert_maintained_links_resolve(self, dest: Path) -> None:
        documents = (
            list(dest.glob("lj-*/SKILL.md"))
            + list((dest / "_compat").glob("*.md"))
            + list((dest / "templates").glob("*.md"))
        )
        markdown_links = re.compile(r"\]\(([^)]+)\)")
        resource_literals = re.compile(r"`([^`\r\n]+\.(?:md|py))`")
        for document in documents:
            text = document.read_text(encoding="utf-8")
            candidates = [match.split("#", 1)[0] for match in markdown_links.findall(text)]
            candidates.extend(
                item for item in resource_literals.findall(text)
                if "/" in item or "\\" in item
            )
            for raw in candidates:
                target = raw.strip()
                if (not target or "://" in target or target.startswith("#")
                        or "<" in target or ">" in target or Path(target).is_absolute()):
                    continue
                resolved = dest / target if target.startswith("templates/") else document.parent / target
                self.assertTrue(
                    resolved.exists(),
                    f"broken maintained resource in {document}: {raw}",
                )

    def test_adopt_untracked_baseline_twenty_then_switch_to_core(self):
        """The pre-state installer layout can be adopted without leaving old entrypoints."""
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            dest.mkdir()
            for name in data["profiles"]["full"] + data["shared"]:
                installer.create_link(SUITE / name, dest / name)
            foreign = dest / "user-owned.txt"
            foreign.write_text("keep me", encoding="utf-8")
            self.assertFalse((dest / installer.STATE_NAME).exists())

            installer.install_dest(
                dest, data["profiles"]["core"], "link", False, False, data,
                adopt_existing=True,
            )

            self.assertEqual(entrypoints(dest), sorted(data["profiles"]["core"]))
            self.assertEqual(foreign.read_text(encoding="utf-8"), "keep me")
            state = json.loads((dest / installer.STATE_NAME).read_text(encoding="utf-8"))
            shadow_roots = {
                Path(relative).parts[0]
                for name in data["profiles"]["core"]
                for relative in data.get("resource_closure", {}).get(name, [])
                if Path(relative).parts[0] not in data["profiles"]["core"]
            }
            expected_managed = (
                set(data["profiles"]["core"] + data["shared"])
                | shadow_roots
                | {Path(relative).parts[0] for relative in data["templates"]}
                | {Path(relative).parts[0] for relative in data.get("template_closure", [])}
            )
            self.assertEqual(set(state["managed"]), expected_managed)

    def test_installed_profiles_have_exact_entries_templates_and_closed_resources(self):
        data = installer.inventory()
        for profile in ("core", "full"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp) / "skills"
                installer.install_dest(
                    dest, data["profiles"][profile], "copy", False, False, data
                )
                self.assertEqual(entrypoints(dest), sorted(data["profiles"][profile]))
                for relative in data["templates"]:
                    self.assertTrue((dest / relative).exists(), relative)
                self.assertFalse((dest / "_compat").exists())
                self.assert_maintained_links_resolve(dest)

    def test_retargeted_removed_link_rejects_before_any_mutation(self):
        data = installer.inventory()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            dest = base / "skills"
            installer.install_dest(
                dest, data["profiles"]["full"], "link", False, False, data
            )
            retargeted = dest / "lj-concept"
            remove_directory_link(retargeted)
            foreign = base / "foreign-concept"
            foreign.mkdir()
            installer.create_link(foreign, retargeted)
            other_removed = dest / "lj-journal"
            self.assertTrue(other_removed.exists())

            with self.assertRaisesRegex(RuntimeError, "retargeted link or junction"):
                installer.install_dest(
                    dest, data["profiles"]["core"], "link", False, False, data
                )

            self.assertTrue(
                other_removed.exists(),
                "preflight must reject before removing another managed entry",
            )
            self.assertEqual(retargeted.resolve(), foreign.resolve())

    def test_resource_only_source_change_refreshes_managed_shadow(self):
        """A changed resource digest replaces an unmodified installed resource shadow."""
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            mock_root = base / "source"
            dest = base / "dest"
            (mock_root / "lj-new").mkdir(parents=True)
            (mock_root / "lj-new/SKILL.md").write_text(
                "---\nname: lj-new\ndescription: Test skill.\n---\n", encoding="utf-8"
            )
            resource = mock_root / "lj-old/references/method.md"
            resource.parent.mkdir(parents=True)
            resource.write_text("version one\n", encoding="utf-8")
            data = {
                "profiles": {"core": ["lj-new"], "full": ["lj-new"], "legacy": ["lj-old"]},
                "optional": [],
                "shared": [],
                "templates": [],
                "resource_closure": {"lj-new": ["lj-old/references/method.md"]},
            }

            with mock.patch.object(installer, "ROOT", mock_root):
                installer.install_dest(dest, ["lj-new"], "copy", False, False, data)
                installed = dest / "lj-old/references/method.md"
                self.assertEqual(installed.read_text(encoding="utf-8"), "version one\n")
                resource.write_text("version two\n", encoding="utf-8")
                installer.install_dest(dest, ["lj-new"], "copy", False, False, data)
                self.assertEqual(installed.read_text(encoding="utf-8"), "version two\n")


if __name__ == "__main__":
    unittest.main()
