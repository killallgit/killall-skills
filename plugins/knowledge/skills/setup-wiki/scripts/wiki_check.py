#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REQUIRED_PATHS = (
    "AGENTS.md",
    "KNOWLEDGE.md",
    "WIKI-OPERATIONS.md",
    "wiki.json",
    "raw/manifest.jsonl",
    "wiki/index.md",
    "wiki/overview.md",
    "claims/claims.jsonl",
    "ontology/schema.yaml",
    "ontology/candidates.yaml",
    "ontology/aliases.yaml",
    "evals/questions.yaml",
    "runs/log.jsonl",
)
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


@dataclass(frozen=True)
class CheckResult:
    errors: tuple
    warnings: tuple


def _json_lines(path, label, errors):
    records = []
    if not path.exists():
        return records
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"{label} has invalid JSON on line {line_number}")
            continue
        if not isinstance(record, dict):
            errors.append(f"{label} line {line_number} is not an object")
            continue
        records.append(record)
    return records


def _section_values(text, section):
    values = []
    active = False
    for line in text.splitlines():
        if line == f"{section}:":
            active = True
            continue
        if active and line and not line.startswith(" "):
            break
        if active:
            match = re.match(r"\s+-\s+(?:id:\s*)?([a-zA-Z0-9_-]+)\s*$", line)
            if match:
                values.append(match.group(1))
    return set(values)


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _check_unique_ids(records, kind, errors):
    seen = set()
    for record in records:
        identifier = record.get("id")
        if not identifier:
            errors.append(f"{kind} is missing id")
            continue
        if identifier in seen:
            errors.append(f"duplicate {kind} id: {identifier}")
        seen.add(identifier)
    return seen


def _page_slugs(vault):
    slugs = {}
    for page in (vault / "wiki").rglob("*.md"):
        slugs.setdefault(page.stem, []).append(page)
        slugs.setdefault(page.relative_to(vault / "wiki").with_suffix("").as_posix(), []).append(page)
    return slugs


def _page_ids(vault, errors, page_types):
    identifiers = set()
    for page in (vault / "wiki").rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        match = re.match(r"---\s*\n(.*?)\n---", text, re.DOTALL)
        metadata = match.group(1) if match else ""
        relative = page.relative_to(vault).as_posix()
        identifier_match = re.search(r"^id:\s*([^\s#]+)\s*$", metadata, re.MULTILINE)
        type_match = re.search(r"^type:\s*([^\s#]+)\s*$", metadata, re.MULTILINE)
        if not identifier_match:
            errors.append(f"{relative} is missing page id")
        else:
            identifier = identifier_match.group(1)
            if identifier in identifiers:
                errors.append(f"duplicate page id: {identifier}")
            identifiers.add(identifier)
        if not type_match:
            errors.append(f"{relative} is missing page type")
        elif type_match.group(1) not in page_types:
            errors.append(f"{relative} has unknown page type: {type_match.group(1)}")
    return identifiers


def _check_links(vault, errors, warnings):
    slugs = _page_slugs(vault)
    inbound = {path: 0 for paths in slugs.values() for path in paths}
    for page in (vault / "wiki").rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        for target in WIKILINK.findall(text):
            target = target.strip()
            matches = slugs.get(target, [])
            if not matches:
                errors.append(
                    f"{page.relative_to(vault).as_posix()} links to missing page: {target}"
                )
                continue
            for match in matches:
                inbound[match] = inbound.get(match, 0) + 1
    for page, count in inbound.items():
        if count == 0 and page.name not in {"index.md"}:
            warnings.append(f"orphan page: {page.relative_to(vault).as_posix()}")


def check_vault(vault):
    vault = Path(vault).expanduser().resolve()
    errors = []
    warnings = []

    for relative in REQUIRED_PATHS:
        if not (vault / relative).exists():
            errors.append(f"missing required path: {relative}")
    config_path = vault / "wiki.json"
    if not config_path.exists():
        return CheckResult(tuple(errors), tuple(warnings))
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append("wiki.json is invalid JSON")
        return CheckResult(tuple(errors), tuple(warnings))

    projects = config.get("projects", [])
    if not projects:
        errors.append("wiki.json has no projects")
    for project_value in projects:
        project = Path(project_value).expanduser().resolve()
        pointer = project / ".wiki.json"
        if not pointer.exists():
            errors.append(f"project is missing .wiki.json pointer: {project}")
            continue
        try:
            pointer_data = json.loads(pointer.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"project has invalid .wiki.json pointer: {project}")
            continue
        if Path(pointer_data.get("vault", "")).expanduser().resolve() != vault:
            errors.append(f"project pointer targets another vault: {project}")

    sources = _json_lines(vault / "raw" / "manifest.jsonl", "raw/manifest.jsonl", errors)
    source_ids = _check_unique_ids(sources, "source", errors)
    for source in sources:
        relative_path = source.get("path")
        if not relative_path:
            errors.append(f"source {source.get('id', '<unknown>')} is missing path")
            continue
        source_path = (vault / relative_path).resolve()
        try:
            source_path.relative_to(vault)
        except ValueError:
            errors.append(f"source {source.get('id', '<unknown>')} escapes vault")
            continue
        if not source_path.is_file():
            errors.append(
                f"source {source.get('id', '<unknown>')} path is missing: {relative_path}"
            )
            continue
        expected_hash = source.get("sha256")
        actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if expected_hash != actual_hash:
            errors.append(
                f"source {source.get('id', '<unknown>')} hash does not match {relative_path}"
            )

    schema_path = vault / "ontology" / "schema.yaml"
    schema = schema_path.read_text(encoding="utf-8") if schema_path.exists() else ""
    predicates = _section_values(schema, "relation_types")
    states = _section_values(schema, "claim_states")
    page_types = _section_values(schema, "page_types")
    claims = _json_lines(vault / "claims" / "claims.jsonl", "claims/claims.jsonl", errors)
    _check_unique_ids(claims, "claim", errors)
    page_ids = _page_ids(vault, errors, page_types)
    for claim in claims:
        identifier = claim.get("id", "<unknown>")
        if not claim.get("statement"):
            errors.append(f"claim {identifier} is missing statement")
        if claim.get("status") not in states:
            errors.append(f"claim {identifier} has unknown status: {claim.get('status')}")
        if not _parse_date(claim.get("observed_at")):
            errors.append(f"claim {identifier} has invalid observed_at")
        for source_id in claim.get("source_ids", []):
            if source_id not in source_ids:
                errors.append(
                    f"claim {identifier} references missing source: {source_id}"
                )
        predicate = claim.get("predicate")
        if predicate and predicate not in predicates:
            errors.append(f"claim {identifier} uses unknown predicate: {predicate}")
        for endpoint in ("subject_id", "object_id"):
            entity_id = claim.get(endpoint)
            if entity_id and entity_id not in page_ids:
                errors.append(
                    f"claim {identifier} references missing entity: {entity_id}"
                )
        valid_from = _parse_date(claim.get("valid_from"))
        valid_to = _parse_date(claim.get("valid_to"))
        if claim.get("valid_from") and not valid_from:
            errors.append(f"claim {identifier} has invalid valid_from")
        if claim.get("valid_to") and not valid_to:
            errors.append(f"claim {identifier} has invalid valid_to")
        if valid_from and valid_to and valid_to < valid_from:
            errors.append(f"claim {identifier} has valid_to before valid_from")

    _check_links(vault, errors, warnings)
    eval_path = vault / "evals" / "questions.yaml"
    if eval_path.exists() and "questions: []" in eval_path.read_text(encoding="utf-8"):
        warnings.append("evaluation question set is empty")
    return CheckResult(tuple(errors), tuple(warnings))


def main():
    parser = argparse.ArgumentParser(description="Validate an agent wiki vault.")
    parser.add_argument("vault", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    result = check_vault(args.vault)
    for warning in result.warnings:
        print(f"WARN {warning}")
    for error in result.errors:
        print(f"ERROR {error}")
    print(f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)")
    raise SystemExit(1 if result.errors else 0)


if __name__ == "__main__":
    main()
