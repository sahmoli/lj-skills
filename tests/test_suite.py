"""Unit tests for the lj skill-suite lint harness.

Run:  python3 -m unittest discover -s tests
Covers: (1) guardrail regression — each SKILL.md still states its own soul;
        (2) test-your-test — the bad fixtures fail and the good fixtures pass.
"""
import os
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import fitz
import matplotlib.pyplot as plt
import numpy as np
import yaml
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SUITE, "lint"))

from checks import FAIL                  # noqa: E402
from lint_concept import lint_concept    # noqa: E402
from lint_journal import lint_journal    # noqa: E402
import run_checks                        # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def fails(findings):
    return [f for f in findings if f.severity == FAIL]


class GuardrailRegression(unittest.TestCase):
    def test_skill_structure_and_frontmatter(self):
        self.assertEqual(fails(run_checks.validate_skills(SUITE)), [],
                         "all installed skills must pass structure/frontmatter validation")

    def test_routing_contract_inventory(self):
        self.assertEqual(fails(run_checks.validate_routing_contracts(SUITE)), [],
                         "routing contracts must cover every real skill with positive/negative/ambiguous cases")

    def test_soul_phrases_present(self):
        self.assertEqual(fails(run_checks.guardrail_regression()), [],
                         "legacy phrase audit must never become a blocking prose gate")


class TestYourTest(unittest.TestCase):
    def test_bad_concept_fails(self):
        self.assertTrue(fails(lint_concept(os.path.join(FIX, "bad_concept.md"))),
                        "bad_concept.md must produce a FAIL")

    def test_good_concept_passes(self):
        self.assertEqual(fails(lint_concept(os.path.join(FIX, "good_concept.md"))), [],
                         "good_concept.md must have zero FAILs")

    def test_hub_concept_fake_confirmed_and_privacy_leak_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "empty-confirmed.md")
            with open(fake, "w", encoding="utf-8") as fh:
                fh.write(
                    "---\n"
                    "title: Empty Confirmed\n"
                    "type: zettel\n"
                    "provenance: juan-confirmed\n"
                    "privacy: private\n"
                    "publish_target: none\n"
                    "---\n\n"
                    "## 我的判断 (My Take)\n"
                    "<!-- 仅 Juan 可写 -->\n"
                )
            codes = {f.code for f in fails(lint_concept(fake))}
            self.assertIn("concept.fake_confirmed", codes)

            leak = os.path.join(tmp, "privacy-leak.md")
            with open(leak, "w", encoding="utf-8") as fh:
                fh.write(
                    "---\n"
                    "title: Private Target Leak\n"
                    "type: zettel\n"
                    "provenance: ai-draft\n"
                    "privacy: private\n"
                    "publish_target: notes\n"
                    "---\n\n"
                    "## 我的判断 (My Take)\n"
                    "暂未定稿。\n"
                )
            leak_codes = {f.code for f in fails(lint_concept(leak))}
            self.assertIn("concept.privacy_leak", leak_codes)

            good_hub = os.path.join(tmp, "good-hub.md")
            with open(good_hub, "w", encoding="utf-8") as fh:
                fh.write(
                    "---\n"
                    "title: Habitat Fragmentation\n"
                    "type: zettel\n"
                    "provenance: juan-confirmed\n"
                    "privacy: public-candidate\n"
                    "publish_target: notes\n"
                    "---\n\n"
                    "## 我的判断 (My Take)\n"
                    "必须区分生境总量丧失与控制总量后的空间破碎化本身。\n"
                )
            self.assertEqual(fails(lint_concept(good_hub)), [])

            wiki_dir = os.path.join(tmp, "20_wiki", "notes")
            os.makedirs(wiki_dir)
            legacy_in_hub = os.path.join(wiki_dir, "legacy-bypass.md")
            with open(legacy_in_hub, "w", encoding="utf-8") as fh:
                fh.write(
                    "---\n"
                    "title: Legacy Bypass\n"
                    "type: concept\n"
                    "status: draft\n"
                    "---\n\n"
                    "## Key Claims\n"
                    "- Claim with marker ^[extracted: test]\n"
                )
            bypass_codes = {f.code for f in fails(lint_concept(legacy_in_hub))}
            self.assertIn("concept.hub_frontmatter", bypass_codes)

    def test_bad_journal_fails(self):
        self.assertTrue(fails(lint_journal(os.path.join(FIX, "bad_journal.yaml"))),
                        "bad_journal.yaml must produce a FAIL")

    def test_good_journal_passes(self):
        self.assertEqual(fails(lint_journal(os.path.join(FIX, "good_journal.yaml"))), [],
                         "good_journal.yaml must have zero FAILs")


class OutputValidatorContracts(unittest.TestCase):
    def assert_validator_passes(self, relative_script, *fixture_args):
        command = [sys.executable, os.path.join(SUITE, relative_script)]
        command.extend(
            os.path.join(FIX, arg) if os.path.exists(os.path.join(FIX, arg)) else arg
            for arg in fixture_args
        )
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_validator_rejects(self, relative_script, *fixture_args):
        command = [sys.executable, os.path.join(SUITE, relative_script)]
        command.extend(
            os.path.join(FIX, arg) if os.path.exists(os.path.join(FIX, arg)) else arg
            for arg in fixture_args
        )
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_constraint_report(self):
        self.assert_validator_passes(
            "lj-question/scripts/validate_constraint.py", "good_constraint_report.md")
        self.assert_validator_rejects(
            "lj-question/scripts/validate_constraint.py", "bad_constraint_report.md")

    def test_blindspot_query(self):
        self.assert_validator_passes(
            "templates/scripts/validate_blindspot.py", "good_blindspot_query.md")
        self.assert_validator_rejects(
            "templates/scripts/validate_blindspot.py", "bad_blindspot_query.md")

    def test_book_note_and_coverage(self):
        command = [
            sys.executable,
            os.path.join(SUITE, "lj-read/scripts/validate_note.py"),
            os.path.join(FIX, "good_book_note.md"),
            "--coverage",
            os.path.join(FIX, "good_book_coverage.md"),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        bad_command = [
            sys.executable,
            os.path.join(SUITE, "lj-read/scripts/validate_note.py"),
            os.path.join(FIX, "bad_book_note.md"),
            "--coverage",
            os.path.join(FIX, "bad_book_coverage.md"),
        ]
        bad_result = subprocess.run(bad_command, capture_output=True, text=True, check=False)
        self.assertNotEqual(bad_result.returncode, 0, bad_result.stdout + bad_result.stderr)

    def test_paper_companion(self):
        self.assert_validator_passes(
            "lj-read/scripts/validate_companion.py", "good_paper_companion.md")
        self.assert_validator_rejects(
            "lj-read/scripts/validate_companion.py", "bad_paper_companion.md")

    def test_talk_outline(self):
        self.assert_validator_passes(
            "lj-talk/scripts/validate_outline.py", "good_talk_outline.md")
        self.assert_validator_rejects(
            "lj-talk/scripts/validate_outline.py", "bad_talk_outline.md")

    def test_weave_report(self):
        self.assert_validator_passes(
            "lj-concept/scripts/validate_weave.py", "good_weave_report.md")
        self.assert_validator_rejects(
            "lj-concept/scripts/validate_weave.py", "bad_weave_report.md")

    def test_dig_report_branches(self):
        self.assert_validator_passes(
            "lj-question/scripts/validate_dig.py", "good_dig_report.md")
        self.assert_validator_passes(
            "lj-question/scripts/validate_dig.py", "good_dig_halt.md")
        self.assert_validator_rejects(
            "lj-question/scripts/validate_dig.py", "bad_dig_report.md")

    def test_design_report(self):
        self.assert_validator_passes(
            "lj-design/scripts/validate_output.py", "good_design_report.md")
        self.assert_validator_rejects(
            "lj-design/scripts/validate_output.py", "bad_design_report.md")

    def test_sourcework_dossier(self):
        self.assert_validator_passes(
            "lj-evidence/scripts/validate_dossier.py", "good_sourcework_dossier.md", "--mode", "build")
        self.assert_validator_rejects(
            "lj-evidence/scripts/validate_dossier.py", "bad_sourcework_dossier.md", "--mode", "build")

    def test_roam_pool(self):
        self.assert_validator_passes(
            "lj-question/scripts/validate_pool.py", "good_roam_pool.md")
        self.assert_validator_rejects(
            "lj-question/scripts/validate_pool.py", "bad_roam_pool.md")

    def test_review_report(self):
        self.assert_validator_passes(
            "lj-review/scripts/validate_report.py", "good_review_report.md")
        self.assert_validator_rejects(
            "lj-review/scripts/validate_report.py", "bad_review_report.md")

    def test_referee_report_requires_confidentiality_gate(self):
        self.assert_validator_passes(
            "lj-review/scripts/validate_report.py", "good_referee_report.md")
        self.assert_validator_rejects(
            "lj-review/scripts/validate_report.py", "bad_referee_report.md")

    def test_response_report(self):
        self.assert_validator_passes(
            "lj-review/scripts/validate_report.py", "good_response_report.md", "--mode", "response")
        self.assert_validator_rejects(
            "lj-review/scripts/validate_report.py", "bad_response_report.md", "--mode", "response")

    def test_citecheck_reports(self):
        self.assert_validator_passes(
            "lj-evidence/scripts/validate_report.py", "good_citecheck_report.md", "--mode", "citation")
        self.assert_validator_passes(
            "lj-evidence/scripts/validate_report.py", "good_precedent_report.md", "--mode", "precedent")
        self.assert_validator_rejects(
            "lj-evidence/scripts/validate_report.py", "bad_citecheck_report.md", "--mode", "citation")
        self.assert_validator_passes(
            "lj-evidence/scripts/validate_report.py", "good_fabricated_citecheck_report.md", "--mode", "citation")
        self.assert_validator_rejects(
            "lj-evidence/scripts/validate_report.py", "bad_fabricated_citecheck_report.md", "--mode", "citation")

    def test_resolve_citation_from_cache_only(self):
        import hashlib
        from pathlib import Path

        script = os.path.join(SUITE, "lj-evidence/scripts/resolve_citation.py")
        help_result = subprocess.run(
            [sys.executable, script, "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(help_result.returncode, 0, help_result.stdout + help_result.stderr)

        doi = "10.1038/nature12373"
        crossref_url = f"https://api.crossref.org/works/{doi}?"
        openalex_url = f"https://api.openalex.org/works/doi:{doi}?"
        body = {
            "message": {
                "DOI": doi,
                "title": ["Example title"],
                "author": [{"given": "A", "family": "Example"}],
                "issued": {"date-parts": [[2013]]},
                "container-title": ["Nature"],
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            cache.mkdir()
            for service, url in (("crossref", crossref_url), ("openalex", openalex_url)):
                key = hashlib.sha256(f"{service}\n{url}".encode()).hexdigest()
                (cache / f"{key}.json").write_text(json.dumps({
                    "service": service,
                    "url": url,
                    "http_status": 200,
                    "body": body if service == "crossref" else {
                        "doi": f"https://doi.org/{doi}",
                        "title": "Example title",
                        "publication_year": 2013,
                        "authorships": [{"author": {"display_name": "A Example"}}],
                        "primary_location": {"source": {"display_name": "Nature"}},
                    },
                    "error": None,
                }), encoding="utf-8")
            out = Path(tmp) / "ledger.json"
            result = subprocess.run(
                [
                    sys.executable, script,
                    os.path.join(FIX, "citation-refs.json"),
                    "--out", str(out),
                    "--cache", str(cache),
                    "--from-cache-only",
                    "--services", "crossref,openalex",
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            ledger = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(ledger[0]["verdict"], "resolved")
            self.assertEqual(ledger[0]["best_match"]["doi"], doi)
            self.assertEqual(ledger[0]["integrity"]["status"], "clean")
            self.assertFalse(ledger[0]["integrity"]["is_retracted"])

    def test_evidence_v2_retraction_and_local_corpus(self):
        import hashlib
        from pathlib import Path

        resolve_script = os.path.join(SUITE, "lj-evidence/scripts/resolve_citation.py")
        discover_script = os.path.join(SUITE, "lj-evidence/scripts/discover_sources.py")
        local_script = os.path.join(SUITE, "lj-evidence/scripts/search_local_corpus.py")
        pdf_script = os.path.join(SUITE, "lj-evidence/scripts/pdf_to_md.py")

        for sc in (discover_script, local_script, pdf_script):
            hr = subprocess.run([sys.executable, sc, "--help"], capture_output=True, text=True, check=False)
            self.assertEqual(hr.returncode, 0, hr.stdout + hr.stderr)

        # Verify OpenAlex is_retracted=true surfaces as integrity.status == "retracted"
        doi = "10.1038/nature12373"
        openalex_url = f"https://api.openalex.org/works/doi:{doi}?"
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            cache.mkdir()
            key = hashlib.sha256(f"openalex\n{openalex_url}".encode()).hexdigest()
            (cache / f"{key}.json").write_text(json.dumps({
                "service": "openalex",
                "url": openalex_url,
                "http_status": 200,
                "body": {
                    "doi": f"https://doi.org/{doi}",
                    "title": "Example title",
                    "publication_year": 2013,
                    "is_retracted": True,
                    "authorships": [{"author": {"display_name": "A Example"}}],
                    "primary_location": {"source": {"display_name": "Nature"}},
                },
                "error": None,
            }), encoding="utf-8")
            out = Path(tmp) / "ledger.json"
            res = subprocess.run(
                [
                    sys.executable, resolve_script,
                    os.path.join(FIX, "citation-refs.json"),
                    "--out", str(out),
                    "--cache", str(cache),
                    "--from-cache-only",
                    "--services", "openalex",
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            ledger = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(ledger[0]["integrity"]["is_retracted"])
            self.assertEqual(ledger[0]["integrity"]["status"], "retracted")

            # Verify search_local_corpus.py finds physical page anchors
            corpus = Path(tmp) / "papers"
            corpus.mkdir()
            (corpus / "2025-demo-reading.md").write_text(
                "---\nslug: 2025-demo-reading\ntitle: \"Demo Reading Study\"\ndoi: \"10.1000/demo\"\n"
                "pdf_file: \"10_raw/papers/2025-demo-reading.pdf\"\n---\n\n"
                "## Page 1\n<!-- pdf-p0001 -->\nIntroductory background.\n\n"
                "## Page 4\n<!-- pdf-p0004 -->\nAI summaries can trigger an illusion of comprehension among novices.\n",
                encoding="utf-8",
            )
            sres = subprocess.run(
                [sys.executable, local_script, "--dir", str(corpus), "--query", "illusion of comprehension", "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(sres.returncode, 0, sres.stdout + sres.stderr)
            hits = json.loads(sres.stdout)["hits"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["page"], 4)
            self.assertIn("#page=4", hits[0]["pdf_link"])

            # Verify search_local_corpus.py NEVER fabricates page=1 for JATS XML or unanchored Markdown
            (corpus / "2026-jats-demo.md").write_text(
                "---\nslug: 2026-jats-demo\ntitle: \"JATS XML Demo\"\ndoi: \"10.1000/jats\"\n"
                "source_format: jats_xml\n---\n\n"
                "## Methods\n<!-- jats-sec:2-methods -->\nStructured JATS tables avoid multi-column pdf garbling.\n",
                encoding="utf-8",
            )
            (corpus / "2026-plain-demo.md").write_text(
                "---\nslug: 2026-plain-demo\ntitle: \"Unanchored Note\"\n---\n\n"
                "Unanchored note discussing biodiversity recovery kinetics.\n",
                encoding="utf-8",
            )
            jres = subprocess.run(
                [sys.executable, local_script, "--dir", str(corpus), "--query", "Structured JATS tables", "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(jres.returncode, 0, jres.stdout + jres.stderr)
            jhits = json.loads(jres.stdout)["hits"]
            self.assertEqual(len(jhits), 1)
            self.assertEqual(jhits[0]["locator_type"], "jats-section")
            self.assertIsNone(jhits[0]["page"])
            self.assertEqual(jhits[0]["pdf_link"], "")

            ures = subprocess.run(
                [sys.executable, local_script, "--dir", str(corpus), "--query", "biodiversity recovery kinetics", "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(ures.returncode, 0, ures.stdout + ures.stderr)
            uhits = json.loads(ures.stdout)["hits"]
            self.assertEqual(len(uhits), 1)
            self.assertEqual(uhits[0]["locator_type"], "unanchored")
            self.assertIsNone(uhits[0]["page"])
            self.assertEqual(uhits[0]["pdf_link"], "")

    def test_evidence_v21_verify_pdf_and_ingest_local(self):
        from pathlib import Path

        verify_script = os.path.join(SUITE, "lj-evidence/scripts/verify_pdf.py")
        fetch_script = os.path.join(SUITE, "lj-evidence/scripts/fetch_oa.py")
        ingest_script = os.path.join(SUITE, "lj-evidence/scripts/ingest_local.py")

        for sc in (verify_script, fetch_script, ingest_script):
            hr = subprocess.run([sys.executable, sc, "--help"], capture_output=True, text=True, check=False)
            self.assertEqual(hr.returncode, 0, hr.stdout + hr.stderr)

        # Load verify_pdf module to test three-state classification directly on synthetic PDFs
        spec = importlib.util.spec_from_file_location("verify_pdf_mod", verify_script)
        vmod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vmod)

        def make_pdf(path: Path, pages_text: list[str], pad_bytes: int = 22_000) -> None:
            doc = fitz.open()
            for t in pages_text:
                page = doc.new_page()
                if t:
                    page.insert_text((50, 72), t, fontsize=11)
            raw = doc.tobytes()
            doc.close()
            # Ensure PDF exceeds 20 KB threshold while keeping %%EOF in last 4 KB
            if len(raw) < pad_bytes:
                idx = raw.rfind(b"%%EOF")
                raw = raw[:idx] + (b"%" + b"A" * (pad_bytes - len(raw)) + b"\n") + raw[idx:]
            path.write_bytes(raw)

        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            # 1) Valid 1-page Letter (must PASS as verified, not falsely rejected for <2 pages)
            letter_pdf = td / "letter.pdf"
            make_pdf(letter_pdf, [
                "Brief Communication\nBehavioral plasticity buffers silent population erosion\n"
                "Smith et al. 2026\nDOI: 10.1002/fee.99999\n" + ("Empirical observation text. " * 20)
            ])
            v_ok = vmod.validate(letter_pdf, title="Behavioral plasticity buffers silent population erosion", doi="10.1002/fee.99999")
            self.assertEqual(v_ok["status"], "verified", v_ok)
            self.assertTrue(v_ok["short_paper"])

            # 2) Correction notice quoting target DOI & title (must route to needs-review, NOT verified)
            corr_pdf = td / "correction.pdf"
            make_pdf(corr_pdf, [
                "Author Correction: Behavioral plasticity buffers silent population erosion\n"
                "DOI: 10.1002/fee.99999\n" + ("Correction notice details regarding Table 1. " * 15)
            ])
            v_corr = vmod.validate(corr_pdf, title="Behavioral plasticity buffers silent population erosion", doi="10.1002/fee.99999")
            self.assertEqual(v_corr["status"], "needs-review", v_corr)
            self.assertTrue(v_corr["possible_correction"])

            # 3) Image-only scanned PDF (<100 extracted chars -> needs-review, NOT wrong-article)
            scan_pdf = td / "scan.pdf"
            make_pdf(scan_pdf, ["", ""])
            v_scan = vmod.validate(scan_pdf, title="Behavioral plasticity buffers silent population erosion", doi="10.1002/fee.99999")
            self.assertEqual(v_scan["status"], "needs-review", v_scan)
            self.assertIn("needs-ocr-review", v_scan["reason"])

            # 4) Publisher Media Kit (must be rejected)
            kit_pdf = td / "mediakit.pdf"
            make_pdf(kit_pdf, [
                "Wiley 2026 Media Kit and Advertising Rates\nSponsorship Opportunities & Rate Card\n"
                + ("Circulation and readership metrics for ecology journals. " * 20)
            ])
            v_kit = vmod.validate(kit_pdf, title="Behavioral plasticity buffers silent population erosion", doi="10.1002/fee.99999")
            self.assertEqual(v_kit["status"], "rejected", v_kit)

            # 5) End-to-end safe ingest_local.py: copy mode, exact DOI checks off [x], fuzzy title does NOT
            dl = td / "Downloads"
            dl.mkdir()
            papers = td / "papers"
            inbox = td / "inbox"
            inbox.mkdir()
            shutil.copy2(letter_pdf, dl / "random-download-name.pdf")
            fuzzy_pdf = dl / "fuzzy-no-doi.pdf"
            make_pdf(fuzzy_pdf, [
                "Human wildlife coexistence strategies in pastoral landscapes across Asia\n"
                "No DOI included in this accepted manuscript version.\n" + ("Pastoral livestock conflict text. " * 20)
            ])
            wanted_md = inbox / "20261124-wanted-test.md"
            wanted_md.write_text(
                "- [ ] **`2026-smith-silent-erosion.pdf`** — Smith et al. 2026 · *Behavioral plasticity buffers silent population erosion* (FEE)\n"
                "  - DOI / 出版社直链：https://doi.org/10.1002/fee.99999\n"
                "- [ ] **`2026-chen-coexistence.pdf`** — Chen et al. 2026 · *Human wildlife coexistence strategies in pastoral landscapes across Asia* (ConsLett)\n"
                "  - DOI / 出版社直链：https://doi.org/10.1111/conl.88888\n",
                encoding="utf-8",
            )
            ires = subprocess.run(
                [
                    sys.executable, ingest_script,
                    "--from-dir", str(dl),
                    "--out-dir", str(papers),
                    "--wanted-note", str(wanted_md),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(ires.returncode, 0, ires.stdout + ires.stderr)
            # Original in Downloads must remain intact (copy mode)
            self.assertTrue((dl / "random-download-name.pdf").exists())
            # Exact DOI paper filed + converted + provenance logged + checked off [x]
            self.assertTrue((papers / "2026-smith-silent-erosion.pdf").exists())
            self.assertTrue((papers / "2026-smith-silent-erosion.md").exists())
            self.assertTrue((papers / "_provenance.jsonl").exists())
            updated_wanted = wanted_md.read_text(encoding="utf-8")
            self.assertIn("- [x] **`2026-smith-silent-erosion.pdf`**", updated_wanted)
            # Fuzzy title-only match routed to _pending_match/ and NOT auto-checked off
            self.assertIn("- [ ] **`2026-chen-coexistence.pdf`**", updated_wanted)
            self.assertTrue(any((papers / "_pending_match").glob("2026-chen-coexistence*")))

            # 6) Refuse --move inside Zotero/storage
            zot = td / "Zotero" / "storage"
            zot.mkdir(parents=True)
            zres = subprocess.run(
                [sys.executable, ingest_script, "--from-dir", str(zot), "--out-dir", str(papers), "--move"],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(zres.returncode, 0)

    def test_annotate_builder_contract(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-annotate/scripts/selftest.py")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_viz_good_manifest(self):
        self.assert_validator_passes(
            "lj-viz/scripts/validate_manifest.py", "good_figure_manifest.yaml")

    def test_viz_curated_silhouette_registry(self):
        registry = os.path.join(
            SUITE, "lj-viz/assets/silhouettes/registry.yaml",
        )
        result = subprocess.run(
            [sys.executable, os.path.join(
                SUITE, "lj-viz/scripts/validate_silhouette_registry.py"), registry],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT: PASS", result.stdout)

    def test_viz_renders_silhouette_at_declared_size(self):
        source = os.path.join(
            SUITE, "lj-viz/assets/silhouettes/panthera-uncia__phylopic-cb44ff49.svg",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = os.path.join(temp_dir, "snow-leopard.png")
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/render_silhouette.py"),
                 source, output, "--width-mm", "18", "--dpi", "600"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(os.path.exists(output))
            with Image.open(output) as rendered:
                self.assertEqual(rendered.mode, "RGBA")
                self.assertAlmostEqual(rendered.width, round(18 / 25.4 * 600), delta=1)

    def test_viz_rejects_undisclosed_near_taxon_silhouette(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["visual_design"]["icons"] = {
            "mode": "semantic",
            "purpose": "taxon identity",
            "provenance": "PhyloPic registry",
            "silhouettes": [{
                "registry_id": "panthera-pardus-example",
                "intended_taxon": "Panthera uncia",
                "depicted_taxon": "Panthera pardus",
                "match_level": "relative",
                "approximation_disclosed": False,
            }],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "undisclosed-relative.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approximation_disclosed", result.stdout)

    def test_viz_accepts_manifest_canvas_without_hard_coding_a_venue(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["output"]["width_mm"] = 110
        contract["output"]["height_mm"] = 171
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "non-nature-canvas.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Nature", result.stdout)

    def test_viz_accepts_positive_intermediate_canvas_width(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["output"]["width_mm"] = 128
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "nature-column-and-a-half.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("outside Nature", result.stdout)

    def test_viz_typography_uses_declared_final_size_not_a_venue_range(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "accessible-type.yaml")
            contract["visual_design"]["typography"]["body_pt"] = 8
            contract["visual_design"]["typography"]["panel_label_pt"] = 9
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for invalid in (0, float("nan"), float("inf")):
                contract["visual_design"]["typography"]["body_pt"] = invalid
                with open(manifest, "w", encoding="utf-8") as handle:
                    yaml.safe_dump(contract, handle, sort_keys=False)
                result = subprocess.run(
                    [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                    capture_output=True, text=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("body_pt", result.stdout)
            contract["visual_design"]["typography"]["body_pt"] = 8
            contract["visual_design"]["typography"].pop("panel_label_pt")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("panel_label_pt", result.stdout)

    def test_viz_requires_nature_visual_contract(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract.pop("visual_design")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "missing-visual.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("visual_design", result.stdout)

    def test_viz_rejects_spacing_outside_shared_tokens(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["visual_design"]["spacing_mm"]["panel"] = 3.2
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "ad-hoc-spacing.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("spacing tokens", result.stdout)

    def test_viz_requires_collision_and_label_placement_contract(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["visual_design"].pop("placement")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "missing-placement.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("visual_design.placement", result.stdout)

    def test_viz_rejects_decorative_craft_defaults(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["visual_design"]["typography"]["coloured_text"] = True
        contract["visual_design"]["scaffolding"]["drop_shadows"] = True
        contract["visual_design"]["icons"]["mode"] = "decorative"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "ugly-defaults.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("coloured text", result.stdout)
        self.assertIn("drop_shadows", result.stdout)
        self.assertIn("decorative icons", result.stdout)

    def test_viz_style_preview_renders_before_and_after(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/render_style_preview.py"), temp_dir],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for name in ("lj-viz-before.png", "lj-viz-stress.png", "lj-viz-corpus-craft.png"):
                artifact = os.path.join(temp_dir, name)
                self.assertTrue(os.path.exists(artifact))
                self.assertGreater(os.path.getsize(artifact), 1000)

    def test_viz_visual_regression_and_cvd_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            render = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/render_style_preview.py"), temp_dir],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            artifact = os.path.join(temp_dir, "lj-viz-corpus-craft.png")
            baseline = os.path.join(SUITE, "lj-viz/assets/previews/lj-viz-corpus-craft.png")
            same = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/compare_render.py"), baseline, artifact],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(same.returncode, 0, same.stdout + same.stderr)
            altered = os.path.join(temp_dir, "altered.png")
            with Image.open(artifact).convert("RGB") as image:
                image.paste((255, 0, 255), (0, 0, image.width // 2, image.height // 2))
                image.save(altered)
            changed = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/compare_render.py"), artifact, altered],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(changed.returncode, 0)
            cvd = os.path.join(temp_dir, "cvd.png")
            review = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/render_cvd_preview.py"), artifact, cvd],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(review.returncode, 0, review.stdout + review.stderr)
            self.assertTrue(os.path.exists(cvd))
            with Image.open(artifact).convert("RGB") as original, Image.open(cvd).convert("RGB") as sheet:
                pane_width = min(original.width, 1200)
                scale = pane_width / original.width
                pane_height = round(original.height * scale)
                self.assertEqual(sheet.size, (pane_width * 2, (pane_height + 30) * 3))
                original_pane = np.asarray(sheet.crop((0, 30, pane_width, pane_height + 30))).astype(int)
                grayscale = np.asarray(sheet.crop((pane_width, 30, pane_width * 2, pane_height + 30)))
                self.assertLess(float(np.abs(grayscale[:, :, 0].astype(int) - grayscale[:, :, 1]).mean()), 0.01)
                second_row_y = pane_height + 60
                protanopia = np.asarray(
                    sheet.crop((0, second_row_y, pane_width, second_row_y + pane_height))
                ).astype(int)
                deuteranopia = np.asarray(
                    sheet.crop((pane_width, second_row_y, pane_width * 2, second_row_y + pane_height))
                ).astype(int)
                self.assertGreater(float(np.abs(original_pane - protanopia).mean()), 0.05)
                self.assertGreater(float(np.abs(original_pane - deuteranopia).mean()), 0.05)
                self.assertGreater(float(np.abs(protanopia - deuteranopia).mean()), 0.01)
                third_row_y = (pane_height + 30) * 2 + 30
                tritanopia = np.asarray(
                    sheet.crop((0, third_row_y, pane_width, third_row_y + pane_height))
                ).astype(int)
                self.assertGreater(float(np.abs(original_pane - tritanopia).mean()), 0.05)

    def test_viz_builtin_palettes_pass_declared_cvd_pairs(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_palette.py"), "--builtin"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RESULT: PASS", result.stdout)

    def test_viz_default_prop_cycle_is_neutral_not_taxonomic(self):
        theme_path = os.path.join(SUITE, "lj-viz/assets/theme_publication.py")
        spec = importlib.util.spec_from_file_location("ljviz_prop_theme", theme_path)
        theme = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme)
        cycle = theme.nature_rc()["axes.prop_cycle"].by_key()["color"]
        self.assertEqual(cycle, [theme.NEUTRALS["ink"]])

    def test_viz_python_and_r_palette_values_match(self):
        theme_path = os.path.join(SUITE, "lj-viz/assets/theme_publication.py")
        spec = importlib.util.spec_from_file_location("ljviz_palette_theme", theme_path)
        theme = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme)
        with open(os.path.join(SUITE, "lj-viz/assets/theme_publication.R"), encoding="utf-8") as handle:
            r_source = handle.read()
        for namespace, roles in theme.PALETTE_PROFILES.items():
            for role, colour in roles.items():
                self.assertIn(colour, r_source, f"R palette missing {namespace}.{role}={colour}")

    def test_viz_manifest_paths_are_relative_to_manifest_not_cwd(self):
        manifest = os.path.join(SUITE, "lj-viz/assets/previews/figure-manifest.yaml")
        with tempfile.TemporaryDirectory() as unrelated_cwd:
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                cwd=unrelated_cwd, capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_viz_conceptual_manifest_passes_and_legacy_quantitative_defaults(self):
        conceptual = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"),
             os.path.join(SUITE, "lj-viz/assets/conceptual-figure-manifest.example.yaml")],
            capture_output=True, text=True, check=False,
        )
        legacy = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"),
             os.path.join(FIX, "good_figure_manifest.yaml")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(conceptual.returncode, 0, conceptual.stdout + conceptual.stderr)
        self.assertEqual(legacy.returncode, 0, legacy.stdout + legacy.stderr)

    def test_viz_conceptual_manifest_rejects_dangling_evidence_and_fake_feedback(self):
        with open(os.path.join(SUITE, "lj-viz/assets/conceptual-figure-manifest.example.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["semantic_model"]["edges"][0]["evidence"] = ["missing-anchor"]
        contract["semantic_model"]["topology"]["feedback_loops"] = [["pressure", "buffering", "failure"]]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "broken-concept.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown source anchor", result.stdout)
        self.assertIn("closed directed cycle", result.stdout)

    def test_viz_mixed_manifest_requires_real_semantic_panel_binding(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        with open(os.path.join(SUITE, "lj-viz/assets/conceptual-figure-manifest.example.yaml"), encoding="utf-8") as handle:
            conceptual = yaml.safe_load(handle)
        contract.update({
            "figure_family": "mixed",
            "semantic_model": conceptual["semantic_model"],
            "representation": conceptual["representation"],
            "mixed_bindings": [{"semantic_id": "outcome", "panel_label": "a", "evidence_role": "quantifies outcome"}],
        })
        contract["output"]["formats"].append("svg")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "mixed.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            valid = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
            contract["mixed_bindings"][0]["panel_label"] = "missing-panel"
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            invalid = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("unknown panel", invalid.stdout)

    def test_viz_conceptual_svg_preflight_requires_editable_vector_labels(self):
        with open(os.path.join(SUITE, "lj-viz/assets/conceptual-figure-manifest.example.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        labels = contract["semantic_model"]["constraints"]["locked_labels"].values()
        text_nodes = "".join(f'<text x="10" y="20" style="font-size:7pt">{label}</text>' for label in labels)
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "concept.yaml")
            artifact = os.path.join(temp_dir, "concept.svg")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            with open(artifact, "w", encoding="utf-8") as handle:
                handle.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="178mm" height="125mm" '
                    'viewBox="0 0 178 125"><line x1="1" y1="1" x2="20" y2="20"/>' + text_nodes + '</svg>'
                )
            passed = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"), artifact,
                 "--manifest", manifest], capture_output=True, text=True, check=False,
            )
            with open(artifact, "w", encoding="utf-8") as handle:
                handle.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="178mm" height="125mm" '
                    'viewBox="0 0 178 125"><image href="draft.png" width="178" height="125"/>' + text_nodes + '</svg>'
                )
            raster_wrapper = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"), artifact,
                 "--manifest", manifest], capture_output=True, text=True, check=False,
            )
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        self.assertNotEqual(raster_wrapper.returncode, 0)
        self.assertIn("raster wrapper", raster_wrapper.stdout)

    def test_viz_quick_contract_distinguishes_planned_from_ship(self):
        example = os.path.join(SUITE, "lj-viz/assets/quick-manifest.example.yaml")
        planned = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_quick_manifest.py"), example],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
        self.assertIn("WARN:", planned.stdout)
        with open(example, encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["build"]["status"] = "success"
        contract["build"]["artifacts"] = [{"path": "missing.pdf"}]
        contract["qc"]["visual_craft_verdict"] = "ship"
        contract["qc"]["baseline_diff_reviewed"] = False
        contract["qc"]["technical_preflight"] = {"status": "fail", "report": "missing-preflight.txt"}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "quick.yaml")
            with open(path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            shipped = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_quick_manifest.py"), path],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(shipped.returncode, 0)
        self.assertIn("baseline_diff_reviewed", shipped.stdout)
        self.assertIn("technical_preflight.status: pass", shipped.stdout)

    def test_viz_quick_ship_rejects_counterfeit_or_stale_reports(self):
        with open(os.path.join(SUITE, "lj-viz/assets/quick-manifest.example.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        with tempfile.TemporaryDirectory() as temp_dir:
            for name, content in (
                ("baseline.pdf", b"baseline"), ("figure.pdf", b"artifact"),
                ("figure.py", b"print('figure')"), ("counterfeit.txt", b"not a qc report"),
            ):
                with open(os.path.join(temp_dir, name), "wb") as handle:
                    handle.write(content)
            contract["workflow"]["baseline_artifact"] = "baseline.pdf"
            contract["provenance"]["code"] = "figure.py"
            contract["build"] = {"status": "success", "artifacts": [{"path": "figure.pdf"}]}
            contract["qc"].update({
                "technical_preflight": {"status": "pass", "report": "counterfeit.txt"},
                "baseline_diff_reviewed": True,
                "baseline_diff_report": "counterfeit.txt",
                "visual_craft_verdict": "ship",
            })
            manifest = os.path.join(temp_dir, "quick.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_quick_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not contain RESULT: PASS", result.stdout)
        self.assertIn("not a compare_render report", result.stdout)

    def test_viz_full_ship_requires_successful_build(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["build"] = {"status": "planned", "artifacts": []}
        contract["qc"]["visual_craft_verdict"] = "ship"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "full.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires build.status: success", result.stdout)

    def test_viz_requires_reference_board_and_semantic_colour_namespace(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["reference_board"] = []
        contract["visual_design"]["palette"]["collision_check"] = False
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "no-reference-board.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference_board", result.stdout)
        self.assertIn("collision_check", result.stdout)

    def test_viz_nature_grid_uses_declared_physical_spacing(self):
        theme_path = os.path.join(SUITE, "lj-viz/assets/theme_publication.py")
        spec = importlib.util.spec_from_file_location("ljviz_test_theme", theme_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        theme = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme)
        with theme.publication_theme():
            figure = plt.figure(figsize=theme.figure_size(89, 70))
            grid = theme.nature_grid(
                figure, 1, 2, width_mm=89, height_mm=70, outer_mm=4, panel_mm=4,
            )
            left_axis = figure.add_subplot(grid[0, 0])
            right_axis = figure.add_subplot(grid[0, 1])
            left_axis.set(xlabel="Time", ylabel="Response")
            right_axis.set(xlabel="Effect")
            figure.canvas.draw()
            settings = figure.get_layout_engine().get()
            tight = figure.get_tightbbox(figure.canvas.get_renderer())
            left_outer = tight.x0 * 25.4
            right_outer = (figure.get_figwidth() - tight.x1) * 25.4
            panel_gap = (right_axis.get_position().x0 - left_axis.get_position().x1) * 89
            plt.close(figure)
        self.assertAlmostEqual(settings["w_pad"] * 25.4, 2, places=5)
        self.assertAlmostEqual(settings["rect"][0] * 89, 4, places=5)
        self.assertGreaterEqual(left_outer, 4)
        self.assertGreaterEqual(right_outer, 4)
        self.assertGreaterEqual(panel_gap, 4)

    def test_viz_palette_roles_pass_and_low_contrast_fails(self):
        good = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_palette.py"),
             os.path.join(FIX, "good_figure_manifest.yaml")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["visual_design"]["palette"]["ink"] = "#F7F7F7"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "low-contrast.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            bad = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_palette.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("ink contrast", bad.stdout)

    def test_viz_palette_rejects_cvd_collision_on_a_critical_pair(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["visual_design"]["palette"]["semantic"] = {
            "focal": "#4477AA", "comparison": "#4B78A5",
        }
        contract["visual_design"]["palette"]["critical_pairs"] = [["focal", "comparison"]]
        contract["encoding"]["colour_is_sole_carrier"] = True
        contract["encoding"]["redundant_channel"] = None
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "cvd-collision.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_palette.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("collapses under", result.stdout)

    def test_viz_census_does_not_require_inferential_n(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"),
             os.path.join(FIX, "good_census_manifest.yaml")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("sample size", result.stdout.lower())

    def test_viz_contract_requires_alternative_and_medium(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            content = handle.read()
        content = "\n".join(
            line for line in content.splitlines()
            if not line.startswith("alternative_explanation:")
            and not line.startswith("medium:")
            and not line.startswith("  code:")
        ) + "\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "incomplete.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                handle.write(content)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("alternative_explanation", result.stdout)
        self.assertIn("medium", result.stdout)
        self.assertIn("provenance.code", result.stdout)

    def test_viz_bad_bar_manifest(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"),
             os.path.join(FIX, "bad_bar_manifest.yaml")],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must start at zero", result.stdout)
        self.assertIn("uncertainty.type", result.stdout)
        self.assertIn("colour is the sole carrier", result.stdout)

    def test_viz_bad_map_manifest(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"),
             os.path.join(FIX, "bad_map_manifest.yaml")],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EPSG:3857", result.stdout)
        self.assertIn("coordinate jitter", result.stdout)

    def test_viz_success_cannot_name_a_counterfeit_artifact(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"),
             os.path.join(FIX, "bad_success_manifest.yaml")],
            capture_output=True, text=True, check=False, cwd=SUITE,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("successful build artifact is missing or empty", result.stdout)

    def test_viz_success_requires_real_sources_and_completed_ship_review(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["build"] = {"status": "success", "artifacts": [{"path": "artifact.png"}]}
        contract["provenance"]["code"] = "missing-code.py"
        contract["provenance"]["data"] = [{"path": "missing-data.csv", "columns": ["x"]}]
        contract["qc"]["technical_preflight"] = {"status": "pass", "report": "claimed-pass.txt"}
        contract["qc"]["visual_craft_verdict"] = "ship"
        with tempfile.TemporaryDirectory() as temp_dir:
            Image.new("RGB", (20, 20), "white").save(os.path.join(temp_dir, "artifact.png"))
            manifest = os.path.join(temp_dir, "false-ship.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                cwd=temp_dir, capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code source is missing", result.stdout)
        self.assertIn("data source is missing", result.stdout)
        self.assertIn("requires qc.final_size_reviewed", result.stdout)

    def test_viz_requires_existing_parseable_visual_vocabulary(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["visual_vocabulary"] = {
            "applicable": True,
            "scope": "paper",
            "path": "missing-vocabulary.yaml",
            "locked_channels": ["entity", "colour-role"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "missing-vocabulary-manifest.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                cwd=temp_dir, capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("visual_vocabulary.path does not exist", result.stdout)

    def test_viz_rejects_visual_vocabulary_colour_drift(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        with tempfile.TemporaryDirectory() as temp_dir:
            vocabulary = {
                "palette": {"namespace": "portfolio", "semantic_roles": {"focal": "#397DA7"}},
                "neutral_roles": {"ink": "#202124", "context": "#D9DDE2", "missing": "#8B9098"},
            }
            vocabulary_path = os.path.join(temp_dir, "visual-vocabulary.yaml")
            with open(vocabulary_path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(vocabulary, handle, sort_keys=False)
            contract["visual_vocabulary"] = {
                "applicable": True,
                "scope": "paper",
                "path": "visual-vocabulary.yaml",
                "locked_channels": ["entity", "colour-role"],
            }
            manifest = os.path.join(temp_dir, "drifted-vocabulary-manifest.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                cwd=temp_dir, capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("palette namespace does not match", result.stdout)

    def test_viz_preflight_pass_requires_a_real_report(self):
        with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
            contract = yaml.safe_load(handle)
        contract["qc"]["technical_preflight"] = {"status": "pass", "report": "missing-preflight.txt"}
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = os.path.join(temp_dir, "false-preflight-pass.yaml")
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/validate_manifest.py"), manifest],
                cwd=temp_dir, capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("technical preflight report is missing", result.stdout)

    def test_viz_preflight_missing_artifact(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"),
             os.path.join(FIX, "does-not-exist.pdf")],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or empty", result.stdout)

    def test_viz_preflight_rejects_vector_strokes_over_one_point(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "thick-stroke.pdf")
            document = fitz.open()
            page = document.new_page(width=200, height=100)
            page.draw_line(fitz.Point(20, 50), fitz.Point(180, 50), color=(0, 0, 0), width=1.5)
            document.save(artifact)
            document.close()
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"), artifact],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(">1 pt", result.stdout)

    def test_viz_preflight_detects_small_text_and_unembedded_font(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "bad.pdf")
            subprocess.run(
                [sys.executable, os.path.join(FIX, "viz_bad_preflight.py"), artifact],
                check=True,
            )
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"), artifact],
                capture_output=True, text=True, check=False,
            )
            self.assertIn("<5 pt", result.stdout)
            if shutil.which("pdffonts"):
                self.assertIn("font is not embedded", result.stdout)

    def test_viz_layout_audit_rejects_text_and_icon_overlap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "overlap.pdf")
            icon_path = os.path.join(temp_dir, "icon.png")
            Image.new("RGBA", (40, 20), (0, 0, 0, 255)).save(icon_path)
            document = fitz.open()
            page = document.new_page(width=200, height=100)
            page.insert_text((20, 48), "Snow leopard", fontsize=8)
            page.insert_text((20, 48), "portfolio", fontsize=8)
            page.insert_image(fitz.Rect(40, 36, 70, 51), filename=icon_path)
            document.save(artifact)
            document.close()
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_layout.py"), artifact],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("text overlap", result.stdout)
        self.assertIn("text overlaps small image/icon", result.stdout)

    def test_viz_layout_audit_requires_explicit_multipage_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "two-pages.pdf")
            document = fitz.open()
            for label in ("Page one", "Page two"):
                page = document.new_page(width=200, height=100)
                page.insert_text((20, 50), label, fontsize=8)
            document.save(artifact)
            document.close()
            unchecked = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_layout.py"), artifact],
                capture_output=True, text=True, check=False,
            )
            checked = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_layout.py"), artifact,
                 "--pages", "1-2"],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(unchecked.returncode, 0)
        self.assertIn("explicit --pages", unchecked.stdout)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertIn("layout_pages_checked=1,2", checked.stdout)

    def test_viz_svg_preflight_compares_physical_manifest_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "wrong-size.svg")
            with open(artifact, "w", encoding="utf-8") as handle:
                handle.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="70mm" '
                    'viewBox="0 0 100 70"><text x="5" y="8" style="font-size:6pt">a</text></svg>'
                )
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"), artifact,
                 "--manifest", os.path.join(FIX, "good_figure_manifest.yaml")],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SVG width", result.stdout)

    def test_viz_compound_icon_label_passes_layout_audit(self):
        spec = importlib.util.spec_from_file_location(
            "ljviz_theme", os.path.join(SUITE, "lj-viz/assets/theme_publication.py"))
        theme = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme)
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "compound.pdf")
            rgba = np.zeros((40, 80, 4), dtype=np.uint8)
            rgba[:, :, 3] = 255
            with theme.publication_theme("evidence"):
                fig, ax = plt.subplots(figsize=theme.figure_size(89, 50))
                ax.axis("off")
                theme.add_icon_label(
                    ax, rgba, "Snow leopard", (0.2, 0.5), zoom=0.12,
                    gap_mm=1.5, fontsize=6, box_alignment=(0, 0.5),
                )
                fig.savefig(artifact)
                plt.close(fig)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/audit_layout.py"), artifact],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("layout_text_icon_overlaps=0", result.stdout)

    def test_viz_canvas_grid_and_review_pack_preserve_declared_geometry(self):
        spec = importlib.util.spec_from_file_location(
            "ljviz_canvas_theme", os.path.join(SUITE, "lj-viz/assets/theme_publication.py"))
        theme = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme)
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "canvas.pdf")
            layout_path = os.path.join(temp_dir, "layout.json")
            with theme.publication_theme("evidence"):
                fig = plt.figure(figsize=theme.figure_size(89, 70))
                axes, layout = theme.canvas_grid(
                    fig, 1, 2, width_mm=89, height_mm=70,
                    outer_mm=9, panel_mm=4, width_ratios=[2, 1],
                )
                axes[0][0].plot([0, 1], [0, 1], lw=0.75)
                axes[0][1].scatter([0.5], [0.5], s=8)
                theme.write_layout_contract(layout, layout_path)
                fig.savefig(artifact)
                plt.close(fig)
            left, right = layout["panels"]
            self.assertAlmostEqual(left["left_mm"], 9)
            self.assertAlmostEqual(right["left_mm"] - left["left_mm"] - left["width_mm"], 4)
            metrics = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/craft_metrics.py"), artifact,
                 "--layout", layout_path], capture_output=True, text=True, check=False,
            )
            self.assertEqual(metrics.returncode, 0, metrics.stdout + metrics.stderr)
            self.assertIn("declared_gap_values_mm=[4.0]", metrics.stdout)
            review_dir = os.path.join(temp_dir, "review")
            review = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/render_review_sheet.py"),
                 artifact, review_dir, "--layout", layout_path],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(review.returncode, 0, review.stdout + review.stderr)
            for name in (
                "whole-composition-180dpi.png", "accessibility-contact-sheet.png",
                "print-at-100-percent.pdf", "review-manifest.json",
            ):
                self.assertTrue(os.path.exists(os.path.join(review_dir, name)))
            with open(os.path.join(review_dir, "review-manifest.json"), encoding="utf-8") as handle:
                report = json.load(handle)
            self.assertEqual(report["simulations"], [
                "grayscale", "Protanopia", "Deuteranopia", "Tritanopia",
            ])

    def test_viz_craft_metrics_detects_neighbour_label_intrusion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "intrusion.pdf")
            layout_path = os.path.join(temp_dir, "layout.json")
            points_per_mm = 72 / 25.4
            document = fitz.open()
            page = document.new_page(width=100 * points_per_mm, height=50 * points_per_mm)
            page.insert_text((40 * points_per_mm, 25 * points_per_mm),
                             "Very long neighbour label", fontsize=8)
            document.save(artifact)
            document.close()
            layout = {
                "canvas": {"width_mm": 100, "height_mm": 50},
                "panels": [
                    {"id": "a", "left_mm": 5, "bottom_mm": 5, "width_mm": 40, "height_mm": 40},
                    {"id": "b", "left_mm": 55, "bottom_mm": 5, "width_mm": 40, "height_mm": 40},
                ],
            }
            with open(layout_path, "w", encoding="utf-8") as handle:
                json.dump(layout, handle)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/craft_metrics.py"),
                 artifact, "--layout", layout_path],
                capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rendered text intrudes into panel a", result.stdout)

    def test_viz_craft_metrics_detects_gutter_spill_when_owner_centre_is_wrong(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "owner-centre.pdf")
            layout_path = os.path.join(temp_dir, "layout.json")
            points_per_mm = 72 / 25.4
            document = fitz.open()
            page = document.new_page(width=100 * points_per_mm, height=50 * points_per_mm)
            page.insert_text((35 * points_per_mm, 25 * points_per_mm), "Pallas's cat", fontsize=8)
            document.save(artifact)
            document.close()
            layout = {
                "canvas": {"width_mm": 100, "height_mm": 50},
                "panels": [
                    {"id": "a", "left_mm": 5, "bottom_mm": 5, "width_mm": 40, "height_mm": 40},
                    {"id": "b", "left_mm": 55, "bottom_mm": 5, "width_mm": 40, "height_mm": 40},
                ],
            }
            with open(layout_path, "w", encoding="utf-8") as handle:
                json.dump(layout, handle)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/craft_metrics.py"),
                 artifact, "--layout", layout_path], capture_output=True, text=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("spills across boundary between panels a and b", result.stdout)

    def test_viz_preflight_detects_missing_multi_panel_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "bad.pdf")
            manifest = os.path.join(temp_dir, "manifest.yaml")
            subprocess.run(
                [sys.executable, os.path.join(FIX, "viz_bad_preflight.py"), artifact],
                check=True,
            )
            with open(os.path.join(FIX, "good_figure_manifest.yaml"), encoding="utf-8") as handle:
                contract = yaml.safe_load(handle)
            contract["panels"].append({
                "label": "b", "role": "validation", "mark": "point",
                "quantity_semantics": "estimate", "axis_policy": "null-centred",
                "axis_min": -2, "zero_is_meaningful": True,
            })
            with open(manifest, "w", encoding="utf-8") as handle:
                yaml.safe_dump(contract, handle, sort_keys=False)
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"),
                 artifact, "--manifest", manifest],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("panel labels not observed", result.stdout)

    def test_viz_preflight_detects_low_raster_dpi(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "bad.png")
            subprocess.run(
                [sys.executable, os.path.join(FIX, "viz_bad_preflight.py"), artifact],
                check=True,
            )
            result = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"), artifact,
                 "--manifest", os.path.join(FIX, "good_figure_manifest.yaml")],
                capture_output=True, text=True, check=False,
            )
            self.assertIn("effective raster resolution", result.stdout)

    def test_viz_python_build_and_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "effect.pdf")
            build = subprocess.run(
                [sys.executable, os.path.join(FIX, "viz_e2e_python.py"), artifact],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            check = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"),
                 artifact, "--manifest", os.path.join(FIX, "good_figure_manifest.yaml")],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertIn("RESULT: PASS", check.stdout)

    @unittest.skipUnless(shutil.which("Rscript"), "Rscript unavailable")
    def test_viz_r_build_and_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = os.path.join(temp_dir, "gradient.pdf")
            build = subprocess.run(
                ["Rscript", os.path.join(FIX, "viz_e2e_r.R"), artifact],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            check = subprocess.run(
                [sys.executable, os.path.join(SUITE, "lj-viz/scripts/preflight_figure.py"), artifact],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertIn("RESULT: PASS", check.stdout)


if __name__ == "__main__":
    unittest.main()
