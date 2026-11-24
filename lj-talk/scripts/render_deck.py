#!/usr/bin/env python3
"""Render a PowerPoint deck locally and leave an auditable receipt.

This is deliberately a renderer, rather than a PDF copier: every successful
receipt records the conversion backend and hashes the supplied PPTX.  It never
uses an existing PDF next to the input as evidence that rendering happened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone


VERSION = "1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_soffice() -> str | None:
    return (shutil.which("soffice") or shutil.which("soffice.exe") or
            next((str(p) for p in (Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "LibreOffice").glob("**/soffice.exe")), None))


def _write_receipt(output_dir: Path, source: Path | None, status: str,
                   renderer: str | None, **extra: object) -> Path:
    receipt = {
        "schema": "lj-talk-render-receipt/v1",
        "renderer_version": VERSION,
        "status": status,
        "renderer": renderer,
        "source_pptx": str(source.resolve()) if source else None,
        "source_sha256": sha256(source) if source and source.is_file() else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    out = output_dir / "render-receipt.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def _render_with_pywin32_direct(source: Path, pdf: Path) -> None:
    """Use DispatchEx so this process owns only the PowerPoint instance it quits."""
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pywin32 is not installed") from exc
    app = None
    presentation = None
    try:
        app = win32com.client.DispatchEx("PowerPoint.Application")
        # No visible UI is needed for a headless export.
        presentation = app.Presentations.Open(str(source.resolve()), ReadOnly=True, Untitled=False, WithWindow=False)
        # ppSaveAsPDF=32; fixed format is implemented by PowerPoint itself.
        presentation.SaveAs(str(pdf.resolve()), 32)
    finally:
        if presentation is not None:
            presentation.Close()
        if app is not None:
            # DispatchEx normally gives us a private server.  Retain this guard
            # anyway: if Office reuses an existing application with open decks,
            # rendering must never close that user's work.
            if app.Presentations.Count == 0:
                app.Quit()
    if not pdf.is_file() or pdf.stat().st_size == 0:
        raise RuntimeError("PowerPoint returned without creating a PDF")


def _render_with_pywin32(source: Path, pdf: Path, timeout: int) -> str:
    """Run COM in a throwaway Python process so a stuck Office call is bounded.

    We intentionally do not enumerate or terminate POWERPNT.EXE: another user's
    presentation must remain untouched.  A timeout is reported as a failed render
    and may need manual Office recovery instead of guessing process ownership.
    """
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--_com-worker",
         str(source.resolve()), str(pdf.resolve())],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-500:]
        raise RuntimeError("PowerPoint COM conversion failed" + (f": {detail}" if detail else ""))
    if not pdf.is_file() or pdf.stat().st_size == 0:
        raise RuntimeError("PowerPoint worker returned without creating a PDF")
    return "powerpoint-com-dispatchex"


def _render_with_libreoffice(source: Path, pdf: Path, timeout: int) -> str:
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice is unavailable")
    with tempfile.TemporaryDirectory(prefix="lj-talk-lo-profile-") as profile:
        result = subprocess.run(
            [soffice, "--headless", f"-env:UserInstallation=file:///{Path(profile).as_posix()}",
             "--convert-to", "pdf", "--outdir", str(pdf.parent), str(source)],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    produced = pdf.parent / (source.stem + ".pdf")
    if produced != pdf and produced.is_file():
        produced.replace(pdf)
    if result.returncode or not pdf.is_file() or pdf.stat().st_size == 0:
        detail = (result.stderr or result.stdout).strip()[-500:]
        raise RuntimeError("LibreOffice conversion failed" + (f": {detail}" if detail else ""))
    return "libreoffice-headless"


def pdf_to_pngs(pdf: Path, output_dir: Path, dpi: int = 144) -> list[Path]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required to rasterize rendered PDF") from exc
    pages: list[Path] = []
    document = fitz.open(pdf)
    try:
        for index, page in enumerate(document, 1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            target = output_dir / f"slide-{index:03d}.png"
            pixmap.save(str(target))
            pages.append(target)
    finally:
        document.close()
    return pages


def make_contact_sheet(pages: list[Path], target: Path) -> None:
    from PIL import Image, ImageDraw
    if not pages:
        raise RuntimeError("rendered PDF had no pages")
    thumbs = []
    for page in pages:
        with Image.open(page) as image:
            copy = image.convert("RGB")
            copy.thumbnail((480, 270))
            thumbs.append(copy)
    cols = min(3, len(thumbs)); rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 500, rows * 310), "white")
    draw = ImageDraw.Draw(sheet)
    for i, image in enumerate(thumbs):
        x, y = (i % cols) * 500, (i // cols) * 310
        sheet.paste(image, (x + 10, y + 26))
        draw.text((x + 10, y + 5), f"Slide {i + 1}", fill="black")
    sheet.save(target)


def _pptx_slide_count(source: Path) -> int:
    try:
        from pptx import Presentation
        return len(Presentation(source).slides)
    except Exception as exc:
        raise RuntimeError(f"could not inspect source PPTX slide count: {exc}") from exc


def _owned_previous_outputs(output_dir: Path) -> set[str] | None:
    """Return names owned by a prior successful receipt, or None if untrusted."""
    receipt = output_dir / "render-receipt.json"
    if not receipt.exists():
        return set()
    try:
        record = json.loads(receipt.read_text(encoding="utf-8"))
        if record.get("schema") != "lj-talk-render-receipt/v1" or record.get("status") not in {"success", "failed"}:
            return None
        # A fresh failed run owns only its receipt and is safe to retry.  A
        # failed rerun after a prior success retains the prior artifact fields.
        if record.get("status") == "failed" and not any(key in record for key in ("page_pngs", "output_pdf", "contact_sheet")):
            return {"render-receipt.json"}
        pages = record.get("page_pngs")
        if (not isinstance(pages, list) or not all(isinstance(p, str) and re.fullmatch(r"slide-\d{3}\.png", p) for p in pages) or
                Path(record.get("output_pdf", "")).name != "rendered-deck.pdf" or
                record.get("contact_sheet") != "contact-sheet.png"):
            return None
        return {"render-receipt.json", "rendered-deck.pdf", "contact-sheet.png", *pages}
    except (OSError, ValueError, TypeError):
        return None


def _retained_artifact_fields(output_dir: Path) -> dict[str, object]:
    """Copy verified previous artifact references into a failure receipt."""
    if not _owned_previous_outputs(output_dir):
        return {}
    try:
        record = json.loads((output_dir / "render-receipt.json").read_text(encoding="utf-8"))
        keys = ("output_pdf", "page_pngs", "contact_sheet", "page_count", "output_pdf_sha256")
        return {key: record[key] for key in keys if key in record}
    except (OSError, ValueError, TypeError):
        return {}


def _preflight_publish(output_dir: Path, page_count: int) -> set[str]:
    """Refuse to overwrite untracked files in a caller-selected destination."""
    owned = _owned_previous_outputs(output_dir)
    expected = {"render-receipt.json", "rendered-deck.pdf", "contact-sheet.png",
                *(f"slide-{i:03d}.png" for i in range(1, page_count + 1))}
    if owned is None:
        collisions = sorted(name for name in expected if (output_dir / name).exists())
        if collisions:
            raise RuntimeError("output directory contains untracked renderer target(s): " + ", ".join(collisions))
        return set()
    collisions = sorted(name for name in expected if (output_dir / name).exists() and name not in owned)
    if collisions:
        raise RuntimeError("output directory contains untracked renderer target(s): " + ", ".join(collisions))
    return owned


def _publish(staging: Path, output_dir: Path, pages: list[Path], previous_owned: set[str]) -> tuple[Path, list[Path], Path]:
    """Publish only tracked renderer-owned filenames after a complete render."""
    for name in previous_owned:
        if re.fullmatch(r"slide-\d{3}\.png", name):
            candidate = output_dir / name
            if candidate.exists(): candidate.unlink()
    pdf = output_dir / "rendered-deck.pdf"; (staging / "rendered-deck.pdf").replace(pdf)
    published_pages = []
    for page in pages:
        destination = output_dir / page.name; page.replace(destination); published_pages.append(destination)
    contact = output_dir / "contact-sheet.png"; (staging / "contact-sheet.png").replace(contact)
    return pdf, published_pages, contact


def render(source: Path, output_dir: Path, timeout: int, backend: str = "auto") -> dict[str, object]:
    source = source.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    if not source.is_file() or source.suffix.lower() != ".pptx":
        raise ValueError("input must be an existing .pptx file")
    source_hash_before = sha256(source)
    expected_pages = _pptx_slide_count(source)
    receipt_writable = _owned_previous_outputs(output_dir) is not None
    previous_owned: set[str] = set()
    staging = Path(tempfile.mkdtemp(prefix=".lj-talk-render-", dir=output_dir))
    pdf = staging / "rendered-deck.pdf"
    errors: list[str] = []
    renderer = None
    try:
        previous_owned = _preflight_publish(output_dir, expected_pages)
        choices = ([backend] if backend != "auto" else ["powerpoint", "libreoffice"])
        for choice in choices:
            try:
                # Every backend gets an empty target.  A partial PDF from a
                # failed attempt must never satisfy the next backend's checks.
                for candidate in {pdf, staging / f"{source.stem}.pdf"}:
                    if candidate.exists(): candidate.unlink()
                if choice == "powerpoint": renderer = _render_with_pywin32(source, pdf, timeout)
                elif choice == "libreoffice": renderer = _render_with_libreoffice(source, pdf, timeout)
                else: raise ValueError(f"unknown backend: {choice}")
                break
            except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
                errors.append(f"{choice}: {exc}")
        if renderer is None:
            raise RuntimeError("No local PowerPoint renderer succeeded: " + "; ".join(errors))
        pages = pdf_to_pngs(pdf, staging)
        if len(pages) != expected_pages:
            raise RuntimeError(f"rendered PDF has {len(pages)} pages; source PPTX has {expected_pages} slides")
        make_contact_sheet(pages, staging / "contact-sheet.png")
        if sha256(source) != source_hash_before:
            raise RuntimeError("source PPTX changed during rendering; output was not published")
        final_pdf, final_pages, contact = _publish(staging, output_dir, pages, previous_owned)
        _write_receipt(output_dir, source, "success", renderer,
                       output_pdf=str(final_pdf.resolve()), page_pngs=[p.name for p in final_pages],
                       contact_sheet=contact.name, page_count=len(final_pages), output_pdf_sha256=sha256(final_pdf))
        return {"pdf": final_pdf, "pages": final_pages, "contact_sheet": contact, "renderer": renderer}
    except Exception as exc:
        if receipt_writable:
            _write_receipt(output_dir, source, "failed", renderer,
                           errors=errors + [str(exc)], **_retained_artifact_fields(output_dir))
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _make_probe_pptx(target: Path) -> None:
    """Create a disposable, content-free deck for an end-to-end renderer probe."""
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise RuntimeError("python-pptx is required for --check") from exc
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    box = slide.shapes.add_textbox(914400, 914400, 7315200, 914400)
    box.text_frame.text = "Renderer health check"
    presentation.save(target)


def check(timeout: int) -> int:
    """Perform a bounded real conversion of a synthetic one-slide PPTX."""
    try:
        import win32com.client  # type: ignore # noqa: F401
    except ImportError:
        if not find_soffice():
            print("CHECK: no supported local renderer is available (install pywin32 or LibreOffice)", file=sys.stderr)
            return 1
    with tempfile.TemporaryDirectory(prefix="lj-talk-render-check-") as temp:
        root = Path(temp)
        probe = root / "probe.pptx"
        try:
            _make_probe_pptx(probe)
            result = render(probe, root / "out", timeout)
            if len(result["pages"]) != 1:
                raise RuntimeError(f"health-check produced {len(result['pages'])} pages")
            print(f"CHECK: real one-slide conversion succeeded via {result['renderer']}")
            return 0
        except Exception as exc:
            print(f"CHECK: real conversion failed: {exc}", file=sys.stderr)
            return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="PPTX to render")
    parser.add_argument("--output-dir", type=Path, default=Path("rendered"))
    parser.add_argument("--backend", choices=("auto", "powerpoint", "libreoffice"), default="auto")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--check", action="store_true", help="report local renderer availability")
    parser.add_argument("--_com-worker", nargs=2, metavar=("PPTX", "PDF"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._com_worker:
        try:
            _render_with_pywin32_direct(Path(args._com_worker[0]), Path(args._com_worker[1]))
            return 0
        except Exception as exc:
            print(f"COM WORKER ERROR: {exc}", file=sys.stderr)
            return 1
    if args.check:
        return check(args.timeout)
    if args.input is None:
        parser.error("input is required unless --check is supplied")
    try:
        result = render(args.input, args.output_dir, args.timeout, args.backend)
        print(json.dumps({"status": "success", "renderer": result["renderer"], "output_dir": str(args.output_dir.resolve())}))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
