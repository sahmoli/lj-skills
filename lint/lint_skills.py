"""Structural and routing-contract checks for the lj skill suite."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

from checks import FAIL, WARN, Finding

try:
    import yaml
except ImportError:  # pragma: no cover - fallback is intentionally small
    yaml = None


ALLOWED_FRONTMATTER = {"name", "description"}

CONSTITUTION_TARGET = "../_shared/honesty-constitution.md"


def _skill_dirs(suite: str) -> dict[str, str]:
    out = {}
    for name in sorted(os.listdir(suite)):
        path = os.path.join(suite, name)
        if name.startswith("lj-") and os.path.isfile(os.path.join(path, "SKILL.md")):
            out[name] = path
    return out


def _frontmatter(path: str):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.S)
    if not match:
        raise ValueError("missing --- frontmatter block")
    raw = match.group(1)
    if yaml is not None:
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError("frontmatter is not a mapping")
        return data, text

    name = re.search(r"(?m)^name:\s*([^\n]+)$", raw)
    desc = re.search(r"(?ms)^description:\s*(?:>-?\s*\n((?:  .*\n?)+)|([^\n]+))", raw)
    if not name or not desc:
        raise ValueError("fallback parser could not read name/description")
    description = desc.group(1) or desc.group(2)
    return {"name": name.group(1).strip(), "description": description.strip()}, text


def _official_validator() -> str | None:
    override = os.environ.get("LJ_QUICK_VALIDATE")
    if override:
        return override
    candidate = os.path.expanduser("~/.codex/skills/.system/skill-creator/scripts/quick_validate.py")
    return candidate if os.path.isfile(candidate) else None


def _manifest_skills(suite: str) -> tuple[set[str], str | None]:
    """Read the core profile from the explicit inventory through its backend."""
    install = os.path.join(suite, "scripts", "install_skills.py")
    proc = subprocess.run(
        [sys.executable, install, "--profile", "core", "--list"], cwd=suite, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode == 0:
        return {line.strip() for line in proc.stdout.splitlines() if line.strip()}, None
    return set(), "installer --list failed: " + " ".join(proc.stderr.splitlines())


def validate_skills(suite: str):
    findings = []
    skills = _skill_dirs(suite)
    validator = _official_validator()
    constitution = os.path.join(suite, "_shared", "honesty-constitution.md")
    if not os.path.isfile(constitution):
        findings.append(Finding(FAIL, "skill.constitution", "_shared/honesty-constitution.md", "missing suite constitution"))
    for name, skill_dir in skills.items():
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as handle:
            skill_text = handle.read()
        constitution_refs = re.findall(
            r"\[[^\]]+\]\((\.\./_shared/honesty-constitution\.md)\)", skill_text
        )
        # Compatibility entries may route through one local template or compat body.
        if not constitution_refs:
            for relative in re.findall(r"\]\((\.\./(?:(?:templates|_compat)/[^)]+\.md|lj-[^/]+/SKILL\.md))\)", skill_text):
                source_target = os.path.normpath(os.path.join(skill_dir, relative))
                if relative.startswith("../_compat/"):
                    canonical = os.path.basename(relative).removesuffix(".md")
                    source_target = os.path.join(suite, canonical, "SKILL.md")
                if os.path.isfile(source_target):
                    with open(source_target, encoding="utf-8") as handle:
                        if "../_shared/honesty-constitution.md" in handle.read():
                            constitution_refs.append(CONSTITUTION_TARGET)
                            break
        if not constitution_refs:
            findings.append(Finding(FAIL, "skill.constitution_link", f"{name}/SKILL.md", "shared-rule link missing"))
        else:
            target = os.path.normpath(os.path.join(skill_dir, constitution_refs[0]))
            if not os.path.isfile(target):
                findings.append(Finding(FAIL, "skill.constitution_link", f"{name}/SKILL.md", "shared-rule link target is missing"))

    for name, skill_dir in skills.items():
        rel = f"{name}/SKILL.md"
        path = os.path.join(skill_dir, "SKILL.md")
        try:
            data, text = _frontmatter(path)
        except Exception as exc:
            findings.append(Finding(FAIL, "skill.frontmatter", rel, str(exc)))
            continue

        extra = set(data) - ALLOWED_FRONTMATTER
        if extra:
            findings.append(Finding(FAIL, "skill.frontmatter_keys", rel, f"unsupported keys: {sorted(extra)}"))
        if data.get("name") != name:
            findings.append(Finding(FAIL, "skill.name", rel, f"expected {name!r}, got {data.get('name')!r}"))
        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            findings.append(Finding(FAIL, "skill.description", rel, "description must be a non-empty task trigger"))
        if "TODO" in text:
            findings.append(Finding(FAIL, "skill.todo", rel, "template TODO remains"))

        agent = os.path.join(skill_dir, "agents", "openai.yaml")
        if not os.path.isfile(agent):
            findings.append(Finding(FAIL, "skill.agent_metadata", name, "agents/openai.yaml missing"))
        else:
            with open(agent, encoding="utf-8") as handle:
                agent_text = handle.read()
            if f"${name}" not in agent_text:
                findings.append(Finding(FAIL, "skill.agent_prompt", name, f"default prompt must invoke ${name}"))

        refs = set(re.findall(r"`((?:\.\./)?lj-[a-z0-9-]+/references/[A-Za-z0-9._/-]+|references/[A-Za-z0-9._/-]+)`", text))
        refs.update(re.findall(r"\]\(((?:\.\./)?(?:_shared|lj-[a-z0-9-]+)/(?:[A-Za-z0-9._/-]+)|references/[A-Za-z0-9._/-]+)\)", text))
        for ref in sorted(refs):
            target = os.path.normpath(os.path.join(skill_dir, ref))
            if not os.path.exists(target):
                findings.append(Finding(FAIL, "skill.reference", rel, f"missing relative resource: {ref}"))

        if validator:
            child_env = os.environ.copy()
            child_env["PYTHONUTF8"] = "1"
            proc = subprocess.run(
                [sys.executable, validator, skill_dir],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=child_env,
                check=False,
            )
            if proc.returncode:
                msg = " ".join(proc.stdout.strip().splitlines())
                findings.append(Finding(FAIL, "skill.quick_validate", name, msg or "official validator failed"))
    if not validator:
        findings.append(Finding(WARN, "skill.quick_validate", "suite", "official validator unavailable; internal checks only"))

    listed, manifest_error = _manifest_skills(suite)
    inventory_path = os.path.join(suite, "config", "skill-inventory.json")
    try:
        with open(inventory_path, encoding="utf-8") as handle:
            inventory = json.load(handle)
        profiles = inventory["profiles"]
        expected = set(profiles["core"])
        optional_set = set(inventory.get("optional", []))
        if not expected:
            findings.append(Finding(FAIL, "skill.profile_sizes", "config/skill-inventory.json", "core profile cannot be empty"))
        if expected & optional_set:
            findings.append(Finding(FAIL, "skill.profile_overlap", "config/skill-inventory.json", f"core and optional overlap: {sorted(expected & optional_set)}"))
        if set(profiles["full"]) != expected | optional_set:
            findings.append(Finding(FAIL, "skill.full_profile", "config/skill-inventory.json", "full must equal core plus optional"))
        if set(profiles["full"]) != set(skills):
            findings.append(Finding(FAIL, "skill.inventory_closure", "config/skill-inventory.json", f"full={sorted(profiles['full'])} skills_on_disk={sorted(skills)}"))
        for profile, entries in profiles.items():
            missing = set(entries) - set(skills)
            if missing:
                findings.append(Finding(FAIL, "skill.profile_source", profile, f"missing source skills: {sorted(missing)}"))
        # Profile link-closure check: core skills and their references must not link into optional-only skills
        for cname in sorted(expected & set(skills)):
            cdir = skills[cname]
            md_files = [os.path.join(cdir, "SKILL.md")]
            rdir = os.path.join(cdir, "references")
            if os.path.isdir(rdir):
                for root_d, _, fns in os.walk(rdir):
                    md_files.extend(os.path.join(root_d, fn) for fn in fns if fn.endswith(".md"))
            for mf in md_files:
                mtxt = open(mf, encoding="utf-8", errors="ignore").read()
                for opt_name in sorted(optional_set):
                    if re.search(rf"(?:\.\./)+{re.escape(opt_name)}/", mtxt):
                        rel_mf = os.path.relpath(mf, suite)
                        findings.append(Finding(FAIL, "skill.profile_leak", rel_mf, f"core skill links to optional skill {opt_name}; move shared file to _shared/"))
    except Exception as exc:
        expected = set()
        findings.append(Finding(FAIL, "skill.inventory", "config/skill-inventory.json", str(exc)))
    if manifest_error and not manifest_error.startswith("WARN:"):
        findings.append(Finding(FAIL, "skill.install_manifest", "install.sh", manifest_error))
    elif manifest_error:
        findings.append(Finding(WARN, "skill.install_manifest", "install.sh", manifest_error.removeprefix("WARN: ")))
    if listed != expected:
        findings.append(Finding(FAIL, "skill.install_manifest", "install.sh", f"core listed={sorted(listed)} expected={sorted(expected)}"))
    if any(name.endswith("-workspace") for name in listed):
        findings.append(Finding(FAIL, "skill.install_workspace", "install.sh", "runtime workspace exposed as a skill"))

    dependency_path = os.path.join(suite, "evals", "external-dependencies.json")
    try:
        with open(dependency_path, encoding="utf-8") as handle:
            dependencies = json.load(handle)
        if not isinstance(dependencies, list):
            raise ValueError("manifest root must be a list")
        seen_dependencies = set()
        for item in dependencies:
            required = {"name", "kind", "used_by", "availability", "fallback"}
            if not isinstance(item, dict) or not required.issubset(item):
                findings.append(Finding(FAIL, "skill.external_dependency", "evals/external-dependencies.json", f"malformed item: {item!r}"))
                continue
            dependency = item["name"]
            if dependency in seen_dependencies:
                findings.append(Finding(FAIL, "skill.external_dependency", dependency, "duplicate manifest entry"))
            seen_dependencies.add(dependency)
            if not item["fallback"].strip():
                findings.append(Finding(FAIL, "skill.external_dependency", dependency, "fallback must be non-empty"))
            for consumer in item["used_by"]:
                if consumer not in skills:
                    findings.append(Finding(FAIL, "skill.external_dependency", dependency, f"unknown consumer: {consumer}"))
                    continue
                with open(os.path.join(skills[consumer], "SKILL.md"), encoding="utf-8") as handle:
                    main_text = handle.read()
                reference_text = ""
                reference_dir = os.path.join(skills[consumer], "references")
                if os.path.isdir(reference_dir):
                    for root, _, files in os.walk(reference_dir):
                        for filename in files:
                            if filename.endswith(".md"):
                                with open(os.path.join(root, filename), encoding="utf-8") as handle:
                                    reference_text += handle.read()
                if dependency not in main_text + reference_text:
                    findings.append(Finding(FAIL, "skill.external_dependency", dependency, f"not named by declared consumer {consumer}"))
    except Exception as exc:
        findings.append(Finding(FAIL, "skill.external_dependency", "evals/external-dependencies.json", str(exc)))
    return findings


def validate_routing_contracts(suite: str):
    findings = []
    path = os.path.join(suite, "evals", "routing-cases.json")
    if not os.path.isfile(path):
        return [Finding(FAIL, "routing.missing", "evals/routing-cases.json", "tracked routing contract missing")]
    try:
        with open(path, encoding="utf-8") as handle:
            cases = json.load(handle)
    except Exception as exc:
        return [Finding(FAIL, "routing.json", path, str(exc))]

    skills = _skill_dirs(suite)
    if set(cases) != set(skills):
        findings.append(Finding(FAIL, "routing.inventory", path, f"cases={sorted(cases)} skills={sorted(skills)}"))
    seen_prompts = set()
    for name, contract in cases.items():
        positives = contract.get("positive", [])
        negatives = contract.get("negative", [])
        ambiguous = contract.get("ambiguous", [])
        if len(positives) < 2 or len(negatives) < 2 or len(ambiguous) < 1:
            findings.append(Finding(FAIL, "routing.coverage", name, "need >=2 positive, >=2 negative, and >=1 ambiguous cases"))
        for group_name, prompts in (("positive", positives), ("negative", negatives), ("ambiguous", ambiguous)):
            for prompt in prompts:
                if not isinstance(prompt, str) or len(prompt.strip()) < 8:
                    findings.append(Finding(FAIL, "routing.case", name, f"weak {group_name} case: {prompt!r}"))
                    continue
                key = prompt.strip().lower()
                if key in seen_prompts:
                    findings.append(Finding(FAIL, "routing.duplicate", name, f"duplicate case: {prompt}"))
                seen_prompts.add(key)
    return findings
