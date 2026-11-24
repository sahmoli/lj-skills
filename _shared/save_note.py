#!/usr/bin/env python3
"""Save an LJ Markdown note with a portable Denote-style filename (stdlib only)."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import unicodedata

SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")
RESERVED = {"title", "date", "tags", "identifier", "skill"}


def default_directory() -> Path:
    settings = json.loads(Path(__file__).with_name("note-settings.json").read_text(encoding="utf-8"))
    if settings.get("schema_version") != 1:
        raise ValueError("unsupported note settings version")
    env_key = settings.get("env_override", "LJ_NOTES_DIR")
    override = os.environ.get(env_key, "").strip()
    if override:
        path = Path(override).expanduser()
    elif os.name == "nt":
        path = Path(settings["windows_directory"]).expanduser()
    else:
        path = Path(settings["other_directory"]).expanduser()
    if not path.is_absolute():
        raise ValueError("note directory must be absolute")
    if os.name == "nt" and not Path(path.anchor).is_dir():
        raise OSError(f"note drive unavailable: {path.anchor}")
    return path


def filename_title(title: str) -> str:
    title = unicodedata.normalize("NFC", title)
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title)
    title = re.sub(r"\s+", "-", title.strip())
    title = re.sub(r"-{2,}|_{2,}", "-", title)
    title = title.strip(" .-_")[:80].rstrip(" .-_")
    if not title:
        raise ValueError("title has no usable filename characters")
    return title


def save_note(body: str, title: str, skill: str, dest: Path | None = None,
              sources: list[str] | None = None, metadata: dict | None = None,
              now: datetime | None = None) -> Path:
    if not re.fullmatch(r"lj-[a-z0-9]+(?:-[a-z0-9]+)*", skill):
        raise ValueError("skill must be an lj- skill name")
    body = body.strip()
    if not body:
        raise ValueError("note body is empty")
    if body.splitlines()[0].strip() == "---":
        raise ValueError("input must be Markdown body; merge header fields with --metadata-json")
    metadata = {} if metadata is None else metadata
    if not isinstance(metadata, dict) or RESERVED.intersection(metadata):
        raise ValueError("extra metadata must be an object without reserved header fields")
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key) for key in metadata):
        raise ValueError("invalid metadata key")
    moment = datetime.now(SHANGHAI) if now is None else now
    if moment.tzinfo is None:
        raise ValueError("note time must have an explicit timezone")
    moment = moment.astimezone(SHANGHAI)
    identifier = moment.strftime("%Y%m%dT%H%M%S")
    tag = skill.removeprefix("lj-")
    filename = f"{identifier}--{filename_title(title)}__{tag}.md"
    dest = default_directory() if dest is None else Path(dest)
    if not dest.is_absolute():
        raise ValueError("destination must be absolute")
    dest.mkdir(parents=True, exist_ok=True)
    header = {"title": title.strip(), "date": moment.isoformat(timespec="seconds"),
              "tags": [tag], "identifier": identifier, "skill": skill}
    if sources:
        header["sources"] = sources
    header.update(metadata)
    text = "---\n" + "".join(f"{key}: {json.dumps(value, ensure_ascii=False, allow_nan=False)}\n"
                               for key, value in header.items()) + "---\n\n" + body + "\n"
    path = dest / filename
    lock = dest / f".{identifier}.lock"
    # Coordinate simultaneous saves so identifiers remain unique across titles.
    lock.mkdir()
    try:
        if next(dest.glob(f"{identifier}--*.md"), None) is not None:
            raise FileExistsError(f"identifier already exists; retry with a new actual time: {identifier}")
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        if path.read_bytes() != text.encode("utf-8"):
            raise OSError(f"saved note readback failed: {path}")
    finally:
        lock.rmdir()
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--dest", type=Path)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--metadata-json", type=Path)
    args = parser.parse_args()
    try:
        extra = json.loads(args.metadata_json.read_text(encoding="utf-8")) if args.metadata_json else None
        path = save_note(args.input.read_text(encoding="utf-8"), args.title, args.skill,
                         args.dest, args.source, extra)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Note not saved: {exc}\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
