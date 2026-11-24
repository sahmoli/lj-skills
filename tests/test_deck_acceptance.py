"""Independent structural acceptance checks for the local lj-talk deck tools.

These use only temporary, synthetic files.  They examine OOXML and hashes rather
than matching presentation prose, so they test editability and provenance rather
than a particular talk's wording.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from PIL import Image
from pptx import Presentation


ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "lj-talk" / "scripts" / "deck.py"
RENDER = ROOT / "lj-talk" / "scripts" / "render_deck.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeckAcceptance(unittest.TestCase):
    def make_assets_and_plan(self, directory: Path, count: int = 3) -> tuple[Path, Path, Path]:
        one, two = directory / "one.png", directory / "two.png"
        Image.new("RGB", (80, 40), (25, 50, 75)).save(one)
        Image.new("RGB", (40, 80), (180, 90, 30)).save(two)
        slides = []
        for n in range(count):
            slides.append({
                "id": f"s-{n + 1:02d}", "section": "main", "kind": "content",
                "title": f"Synthetic observation {n + 1}", "body": ["Synthetic supporting statement"],
                "notes": f"private production intent {n + 1}",
                "sources": [{"citation": "Synthetic source", "locator": f"row {n + 1}"}],
                "images": [{"id": "a", "path": one.name, "fit": "contain", "role": "illustrative"}] if n != 1 else
                          [{"id": "b", "path": two.name, "fit": "crop", "role": "evidence"}],
            })
        plan = directory / "plan.json"
        plan.write_text(json.dumps({"deck_id": "synthetic-deck", "title": "Synthetic", "slides": slides}), encoding="utf-8")
        return plan, one, two

    def command(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([sys.executable, str(DECK), *args], text=True, capture_output=True, cwd=ROOT)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result

    def test_build_embeds_original_bytes_and_keeps_notes_off_canvas(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); plan, one, _ = self.make_assets_and_plan(folder); out = folder / "deck.pptx"
            self.command("build", "--plan", str(plan), "--output", str(out))
            with zipfile.ZipFile(out) as package:
                media = [package.read(name) for name in package.namelist() if name.startswith("ppt/media/")]
                slide_xml = b"".join(package.read(name) for name in package.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
                notes_xml = b"".join(package.read(name) for name in package.namelist() if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml"))
            self.assertIn(one.read_bytes(), media, "asset should be embedded without regeneration")
            self.assertNotIn(b"private production intent", slide_xml)
            self.assertIn(b"private production intent", notes_xml)

    def test_asset_change_marks_only_affected_logical_slide(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); plan, one, _ = self.make_assets_and_plan(folder); out = folder / "deck.pptx"
            self.command("build", "--plan", str(plan), "--output", str(out))
            before = json.loads((Path(str(out) + ".deck-state.json")).read_text(encoding="utf-8"))
            Image.new("RGB", (80, 40), (1, 2, 3)).save(one)
            self.command("build", "--plan", str(plan), "--output", str(out))
            after = json.loads((Path(str(out) + ".deck-state.json")).read_text(encoding="utf-8"))
            changed = {x["id"] for x, y in zip(before["slides"], after["slides"]) if x["dependency_hash"] != y["dependency_hash"]}
            self.assertEqual(changed, {"s-01", "s-03"})
            self.assertEqual(set(after.get("changed_slide_ids", [])), changed,
                             "state must truthfully identify logical slides invalidated by dependencies")

    def test_unchanged_build_is_idempotent_and_existing_deck_is_protected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); plan, _, _ = self.make_assets_and_plan(folder); out = folder / "deck.pptx"
            self.command("build", "--plan", str(plan), "--output", str(out)); first = digest(out)
            self.command("build", "--plan", str(plan), "--output", str(out)); self.assertEqual(digest(out), first)
            state = Path(str(out) + ".deck-state.json"); state.unlink()
            result = self.command("build", "--plan", str(plan), "--output", str(out), expect=1)
            self.assertIn("refusing", result.stderr.lower())

    def test_title_edit_preserves_media_and_unrelated_shape_formatting(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); plan, _, _ = self.make_assets_and_plan(folder); source = folder / "deck.pptx"; edited = folder / "edited.pptx"
            self.command("build", "--plan", str(plan), "--output", str(source))
            with zipfile.ZipFile(source) as package:
                media_before = {n: hashlib.sha256(package.read(n)).hexdigest() for n in package.namelist() if n.startswith("ppt/media/")}
            self.command("edit", "--input", str(source), "--output", str(edited), "--slide-id", "s-01", "--shape-name", "s-01:title", "--text", "Edited title")
            with zipfile.ZipFile(edited) as package:
                media_after = {n: hashlib.sha256(package.read(n)).hexdigest() for n in package.namelist() if n.startswith("ppt/media/")}
            self.assertEqual(media_after, media_before)
            presentation = Presentation(edited)
            unrelated = next(s for s in presentation.slides[0].shapes if s.name == "s-01:body")
            self.assertTrue(unrelated.has_text_frame and unrelated.text_frame.paragraphs[0].runs[0].font.size)

    def test_replace_image_preserves_picture_geometry_crop_and_stack_position(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); plan, _, two = self.make_assets_and_plan(folder); source = folder / "deck.pptx"; edited = folder / "replaced.pptx"
            replacement = folder / "replacement.png"; Image.new("RGB", (30, 100), (20, 220, 80)).save(replacement)
            self.command("build", "--plan", str(plan), "--output", str(source))
            old = Presentation(source).slides[1]
            old_shape = next(s for s in old.shapes if s.name == "s-02:image:b")
            old_geometry = (old_shape.left, old_shape.top, old_shape.width, old_shape.height)
            old_index = list(old.shapes).index(old_shape)
            self.command("replace-image", "--input", str(source), "--output", str(edited), "--slide-id", "s-02", "--shape-name", "s-02:image:b", "--image", str(replacement), "--fit", "crop")
            new = Presentation(edited).slides[1]; new_shape = next(s for s in new.shapes if s.name == "s-02:image:b")
            new_geometry = (new_shape.left, new_shape.top, new_shape.width, new_shape.height)
            self.assertEqual(new_geometry, old_geometry)
            self.assertEqual(list(new.shapes).index(new_shape), old_index)
            self.assertGreater(new_shape.crop_top + new_shape.crop_bottom + new_shape.crop_left + new_shape.crop_right, 0)

    def test_forty_page_main_appendix_uses_stable_ids_and_distinct_display_numbers(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); plan, _, _ = self.make_assets_and_plan(folder, 40)
            data = json.loads(plan.read_text(encoding="utf-8"))
            for item in data["slides"][32:]: item["section"] = "appendix"
            plan.write_text(json.dumps(data), encoding="utf-8"); out = folder / "deck.pptx"
            self.command("build", "--plan", str(plan), "--output", str(out))
            state = json.loads(Path(str(out) + ".deck-state.json").read_text(encoding="utf-8"))
            self.assertEqual([x["id"] for x in state["slides"]], [x["id"] for x in data["slides"]])
            self.assertEqual([x["number"] for x in state["slides"]], list(range(1, 41)))
            rendered = Presentation(out)
            rendered_slides = list(rendered.slides)
            def footer(slide):
                return next(s.text for s in slide.shapes if s.name.endswith(":footer"))
            self.assertEqual([footer(s) for s in rendered_slides[:32]], [f"{i} / 32" for i in range(1, 33)])
            self.assertEqual([footer(s) for s in rendered_slides[32:]], [f"A{i} / A8" for i in range(1, 9)])


class RendererPostprocessAcceptance(unittest.TestCase):
    def load_renderer(self):
        spec = importlib.util.spec_from_file_location("render_deck", RENDER)
        module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
        return module

    def test_receipt_hashes_actual_source_and_postprocesses_generated_pdf(self):
        # Engineering-only test: PDF is generated here to test PNG/contact-sheet
        # postprocessing. It does not assert or represent a PowerPoint conversion.
        module = self.load_renderer()
        import fitz
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); pptx = folder / "input.pptx"; pptx.write_bytes(b"synthetic pptx bytes")
            pdf = folder / "rendered.pdf"; doc = fitz.open(); doc.new_page(width=200, height=100); doc.save(pdf); doc.close()
            pages = module.pdf_to_pngs(pdf, folder); module.make_contact_sheet(pages, folder / "sheet.png")
            receipt = module._write_receipt(folder, pptx, "success", "engineering-test", page_count=len(pages))
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(data["source_sha256"], digest(pptx)); self.assertTrue((folder / "sheet.png").is_file())

    def test_stale_pdf_is_not_published_when_engineering_mock_fails_to_render(self):
        # Engineering-only mock of the COM boundary.  This specifically tests
        # staging/receipt failure semantics, not PowerPoint itself.
        module = self.load_renderer()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); source = folder / "source.pptx"
            probe = Presentation(); probe.slides.add_slide(probe.slide_layouts[6]); probe.save(source)
            output = folder / "output"; output.mkdir(); stale = output / "rendered-deck.pdf"; stale.write_bytes(b"old")
            original = module._render_with_pywin32
            module._render_with_pywin32 = lambda source, pdf, timeout: "engineering-mock"  # does not create PDF
            try:
                with self.assertRaises(RuntimeError): module.render(source, output, 1, "powerpoint")
            finally:
                module._render_with_pywin32 = original
            self.assertEqual(stale.read_bytes(), b"old")
            receipt = json.loads((output / "render-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "failed")

    def test_publish_preserves_untracked_files_and_refuses_target_collision(self):
        # Engineering-only COM-boundary mock: checks destination ownership, not
        # PowerPoint conversion.  It makes a one-page PDF in the staging target.
        module = self.load_renderer()
        import fitz
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); source = folder / "source.pptx"
            probe = Presentation(); probe.slides.add_slide(probe.slide_layouts[6]); probe.save(source)
            def fake_engine(_source, pdf, _timeout):
                document = fitz.open(); document.new_page(width=200, height=100); document.save(pdf); document.close()
                return "engineering-mock"
            original = module._render_with_pywin32; module._render_with_pywin32 = fake_engine
            try:
                output = folder / "output"; output.mkdir()
                unknown = output / "slide-not-renderer.png"; unknown.write_bytes(b"keep-me")
                module.render(source, output, 1, "powerpoint")
                self.assertEqual(unknown.read_bytes(), b"keep-me")
                collision = output / "slide-001.png"; collision.write_bytes(b"untracked-collision")
                (output / "render-receipt.json").unlink()
                with self.assertRaisesRegex(RuntimeError, "untracked renderer target"):
                    module.render(source, output, 1, "powerpoint")
                self.assertEqual(collision.read_bytes(), b"untracked-collision")
            finally:
                module._render_with_pywin32 = original

    def test_failure_receipt_retries_without_losing_tracked_or_unknown_files(self):
        # Engineering-only COM-boundary mock: a successful render is followed
        # by a failed one, then a safe retry in the same destination.
        module = self.load_renderer()
        import fitz
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); source = folder / "source.pptx"
            probe = Presentation(); probe.slides.add_slide(probe.slide_layouts[6]); probe.save(source)
            output = folder / "output"; output.mkdir()
            unknown = output / "slide-not-renderer.png"; unknown.write_bytes(b"keep-me")
            def succeeds(_source, pdf, _timeout):
                document = fitz.open(); document.new_page(width=200, height=100); document.save(pdf); document.close()
                return "engineering-mock"
            original = module._render_with_pywin32
            try:
                module._render_with_pywin32 = succeeds
                module.render(source, output, 1, "powerpoint")
                prior_pdf = (output / "rendered-deck.pdf").read_bytes()
                module._render_with_pywin32 = lambda _source, _pdf, _timeout: "engineering-mock"
                with self.assertRaises(RuntimeError): module.render(source, output, 1, "powerpoint")
                failed = json.loads((output / "render-receipt.json").read_text(encoding="utf-8"))
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["page_pngs"], ["slide-001.png"])
                self.assertEqual((output / "rendered-deck.pdf").read_bytes(), prior_pdf)
                module._render_with_pywin32 = succeeds
                module.render(source, output, 1, "powerpoint")
                self.assertEqual(json.loads((output / "render-receipt.json").read_text(encoding="utf-8"))["status"], "success")
                self.assertEqual(unknown.read_bytes(), b"keep-me")
            finally:
                module._render_with_pywin32 = original

    def test_malformed_receipt_is_rejected_without_key_error(self):
        module = self.load_renderer()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp); (output / "render-receipt.json").write_text('{"schema":"lj-talk-render-receipt/v1","status":"success"}', encoding="utf-8")
            self.assertIsNone(module._owned_previous_outputs(output))


if __name__ == "__main__":
    unittest.main()
