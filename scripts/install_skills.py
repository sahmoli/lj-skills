#!/usr/bin/env python3
"""Install explicitly inventoried lj-skills without traversing junctions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "config" / "skill-inventory.json"
STATE_NAME = ".lj-skills-install-state.json"
IGNORED_DIR_NAMES = {"__pycache__"}
IGNORED_FILE_SUFFIXES = {".pyc", ".pyo"}
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def replace_staged_directory(staged: Path, target: Path) -> None:
    """Allow a briefly locked Windows copy to settle; preserve other errors."""
    for attempt in range(6):
        try:
            os.replace(staged, target)
            return
        except OSError as exc:
            if os.name != "nt" or getattr(exc, "winerror", None) not in {5, 32, 33} or attempt == 5:
                raise
            time.sleep(0.05 * (2 ** attempt))


def inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def declared_name(skill_dir: Path) -> str | None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return None
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def is_reparse(path: Path) -> bool:
    try:
        attrs = path.lstat().st_file_attributes
    except (AttributeError, FileNotFoundError):
        return path.is_symlink()
    return bool(attrs & 0x400)


def tree_digest(path: Path) -> str:
    """Hash a managed directory tree, ignoring transient Python bytecode caches."""
    digest = hashlib.sha256()
    for current, dirs, files in os.walk(path, followlinks=False):
        base = Path(current)
        kept = []
        for name in sorted(dirs):
            if name in IGNORED_DIR_NAMES:
                continue
            child = base / name
            rel = child.relative_to(path).as_posix()
            if is_reparse(child):
                link = os.readlink(child) if child.is_symlink() else "reparse"
                digest.update(f"L\0{rel}\0{link}".encode())
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            if Path(name).suffix in IGNORED_FILE_SUFFIXES:
                continue
            child = base / name
            digest.update(f"F\0{child.relative_to(path).as_posix()}\0".encode())
            with child.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
    return digest.hexdigest()


def resource_digest(root_name: str, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        source = ROOT / relative
        digest.update(relative.encode())
        digest.update(tree_digest(source).encode() if source.is_dir() else source.read_bytes())
    return digest.hexdigest()


def safe_target(dest: Path, name: str) -> Path:
    if not name or Path(name).is_absolute() or len(Path(name).parts) != 1 or name in {".", ".."}:
        raise RuntimeError(f"unsafe managed name: {name!r}")
    resolved_dest = dest.resolve()
    target = resolved_dest / name
    if target.parent != resolved_dest:
        raise RuntimeError(f"target escapes destination: {target}")
    return target


def read_state(dest: Path) -> dict:
    path = dest / STATE_NAME
    if not path.is_file():
        return {"schema_version": 1, "managed": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1 or not isinstance(state.get("managed"), dict):
        raise RuntimeError(f"unsupported installer state: {path}")
    return state


def remove_managed(dest: Path, name: str, record: dict, dry_run: bool) -> None:
    target = safe_target(dest, name)
    if not target.exists() and not is_reparse(target):
        return
    if is_reparse(target):
        source = Path(record.get("source", ""))
        if not source or target.resolve() != source.resolve():
            raise RuntimeError(f"refusing to remove retargeted link or junction: {target}")
        if not dry_run:
            target.unlink() if target.is_symlink() else os.rmdir(target)
        return
    if record.get("mode") not in {"copy", "resource"} or not target.is_dir():
        raise RuntimeError(f"refusing to remove unrecognized target: {target}")
    if tree_digest(target) != record.get("digest"):
        raise RuntimeError(f"refusing to overwrite modified managed directory: {target}")
    if not dry_run:
        shutil.rmtree(target)


def create_link(source: Path, target: Path) -> str:
    try:
        os.symlink(source, target, target_is_directory=True)
        return "link"
    except OSError:
        if os.name != "nt":
            raise
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(target), str(source)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return "junction"


def install_one(source: Path, target: Path, mode: str, dry_run: bool) -> dict:
    if dry_run:
        return {"mode": mode, "source": str(source)}
    if mode == "link":
        actual_mode = create_link(source, target)
        return {"mode": actual_mode, "source": str(source)}
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    staged = temp_dir / target.name
    try:
        shutil.copytree(source, staged, symlinks=True, ignore=COPY_IGNORE)
        replace_staged_directory(staged, target)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return {"mode": "copy", "source": str(source), "digest": tree_digest(target)}


def install_resource_shadow(root_name: str, paths: list[str], target: Path, dry_run: bool) -> dict:
    """Materialize selected non-skill resource directories (such as templates/)."""
    if dry_run:
        return {"mode": "resource", "source": str(ROOT / root_name), "paths": paths,
                "source_digest": resource_digest(root_name, paths)}
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{root_name}-", dir=target.parent))
    staged = temp_dir / root_name
    staged.mkdir()
    try:
        for relative in paths:
            source = ROOT / relative
            destination = staged / Path(relative).relative_to(root_name)
            if source.is_dir():
                shutil.copytree(source, destination, symlinks=True, ignore=COPY_IGNORE)
            elif source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            else:
                raise RuntimeError(f"inventoried resource is missing: {source}")
        replace_staged_directory(staged, target)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return {"mode": "resource", "source": str(ROOT / root_name), "paths": paths,
            "source_digest": resource_digest(root_name, paths),
            "digest": tree_digest(target)}


def selected_names(data: dict, profile: str, optional: list[str]) -> list[str]:
    if profile not in data["profiles"]:
        raise ValueError(f"unknown profile: {profile}")
    unknown = sorted(set(optional) - set(data["optional"]))
    if unknown:
        raise ValueError("unknown optional skill(s): " + ", ".join(unknown))
    return list(dict.fromkeys(data["profiles"][profile] + optional))


def install_dest(dest: Path, names: list[str], mode: str, uninstall: bool, dry_run: bool,
                 data: dict, adopt_existing: bool = False) -> None:
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
    state = read_state(dest) if dest.exists() else {"schema_version": 1, "managed": {}}
    managed = state["managed"]
    shadows: dict[str, list[str]] = {}
    if not uninstall:
        for skill in names:
            for relative in data.get("resource_closure", {}).get(skill, []):
                root_name = Path(relative).parts[0]
                if root_name not in names:
                    shadows.setdefault(root_name, []).append(relative)
        for relative in data.get("templates", []):
            shadows.setdefault(Path(relative).parts[0], []).append(relative)
        for relative in data.get("template_closure", []):
            root_name = Path(relative).parts[0]
            if root_name not in names:
                shadows.setdefault(root_name, []).append(relative)
    desired = [] if uninstall else names + data.get("shared", []) + sorted(shadows)
    known = set().union(
        *map(set, data["profiles"].values()),
        data.get("shared", []),
        data.get("retired_names", []),
        (Path(path).parts[0] for path in data.get("templates", [])),
    )
    if adopt_existing:
        for name in sorted(known - {"_compat", "templates"}):
            target = safe_target(dest, name)
            source = ROOT / name
            if name not in managed and source.exists() and (target.exists() or is_reparse(target)):
                if is_reparse(target) and target.resolve() == source.resolve():
                    managed[name] = {"mode": "junction" if not target.is_symlink() else "link",
                                     "source": str(source)}
    for name in list(managed):
        safe_target(dest, name)
        if name not in known:
            raise RuntimeError(f"state contains a name outside inventory: {name}")
    # Preflight the complete operation before mutating any target.
    for name in sorted(set(managed) - set(desired)):
        target = safe_target(dest, name)
        record = managed[name]
        if target.exists() or is_reparse(target):
            if is_reparse(target):
                if target.resolve() != Path(record.get("source", "")).resolve():
                    raise RuntimeError(f"refusing to remove retargeted link or junction: {target}")
                continue
            if record.get("mode") not in {"copy", "resource"} or tree_digest(target) != record.get("digest"):
                raise RuntimeError(f"refusing to overwrite modified managed directory: {target}")
    for name in desired:
        target = safe_target(dest, name)
        if not (target.exists() or is_reparse(target)) or name in managed:
            continue
        source = ROOT / name
        if (adopt_existing and name in known and source.exists() and is_reparse(target)
                and target.resolve() == source.resolve()):
            managed[name] = {"mode": "junction" if not target.is_symlink() else "link",
                             "source": str(source)}
        else:
            raise RuntimeError(f"refusing to overwrite unknown target: {target}")
    for name in desired:
        target = safe_target(dest, name)
        record = managed.get(name)
        if not record or not (target.exists() or is_reparse(target)):
            continue
        if is_reparse(target):
            if target.resolve() != Path(record.get("source", "")).resolve():
                raise RuntimeError(f"refusing to overwrite retargeted link or junction: {target}")
        elif record.get("mode") in {"copy", "resource"} and tree_digest(target) != record.get("digest"):
            raise RuntimeError(f"refusing to overwrite modified managed directory: {target}")
        elif record.get("mode") not in {"copy", "resource"}:
            raise RuntimeError(f"refusing to overwrite unrecognized target: {target}")
    for name in sorted(set(managed) - set(desired)):
        print(f"  remove  {name}")
        remove_managed(dest, name, managed[name], dry_run)
        managed.pop(name, None)
    for name in desired:
        if name in shadows:
            target = safe_target(dest, name)
            if target.exists() or is_reparse(target):
                record = managed.get(name)
                expected_paths = sorted(set(shadows[name]))
                if (record.get("mode") == "resource" and record.get("paths") == expected_paths
                        and record.get("source_digest") == resource_digest(name, expected_paths)
                        and tree_digest(target) == record.get("digest")):
                    print(f"  ok      {name} (resources only)")
                    continue
                remove_managed(dest, name, record, dry_run)
            print(f"  resource {name}")
            paths = sorted(set(shadows[name]))
            managed[name] = install_resource_shadow(name, paths, target, dry_run)
            continue
        source, target = ROOT / name, safe_target(dest, name)
        if not source.is_dir():
            raise RuntimeError(f"inventoried source directory is missing: {source}")
        if name.startswith("lj-") and declared_name(source) != name:
            raise RuntimeError(f"frontmatter name mismatch: {source}")
        if target.exists() or is_reparse(target):
            record = managed.get(name)
            if (mode == "link" and record.get("mode") in {"link", "junction"} and is_reparse(target)
                    and target.resolve() == source.resolve()):
                print(f"  ok      {name}")
                continue
            if (mode == "copy" and record.get("mode") == "copy"
                    and tree_digest(target) == record.get("digest")
                    and tree_digest(source) == record.get("digest")):
                print(f"  ok      {name}")
                continue
            remove_managed(dest, name, record, dry_run)
        print(f"  {mode:7} {name}")
        managed[name] = install_one(source, target, mode, dry_run)
    if not dry_run:
        path = dest / STATE_NAME
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("link", "copy"), default="link")
    parser.add_argument("--profile", choices=("core", "full"), default="core")
    parser.add_argument("--optional", action="append", default=[], metavar="SKILL")
    parser.add_argument("--dest", action="append", default=[], type=Path)
    parser.add_argument("--with-agents", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--adopt-existing", action="store_true",
                        help="adopt only known links/junctions that resolve to this repository")
    parser.add_argument("--dry-run", "-n", action="store_true")
    parser.add_argument("--list", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data = inventory()
    try:
        names = selected_names(data, args.profile, args.optional)
    except ValueError as exc:
        parser.error(str(exc))
    if args.list:
        print("\n".join(names))
        return 0
    dests = list(args.dest)
    if args.with_agents:
        dests.append(Path.home() / ".agents" / "skills")
    env_dests = os.environ.get("LJ_DESTS")
    if env_dests:
        dests.extend(Path(item) for item in env_dests.split(os.pathsep) if item)
    if not dests:
        auto = [
            Path(os.environ.get("CLAUDE_SKILLS_DIR", Path.home() / ".claude" / "skills")),
            Path(os.environ.get("CODEX_SKILLS_DIR", Path.home() / ".codex" / "skills")),
            Path(os.environ.get("ANTIGRAVITY_SKILLS_DIR", Path.home() / ".gemini" / "config" / "skills")),
        ]
        dests.extend(path for path in auto if path.parent.is_dir())
    if not dests:
        parser.error("no installed tool target found; pass --dest DIR")
    for dest in dict.fromkeys(path.resolve() for path in dests):
        print(f"==> {dest}")
        install_dest(dest, names, args.mode, args.uninstall, args.dry_run, data,
                     args.adopt_existing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
