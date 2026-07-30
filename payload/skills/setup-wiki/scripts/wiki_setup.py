import json
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path


DIRECTORIES = (
    "raw",
    "wiki/entities",
    "wiki/concepts",
    "wiki/decisions",
    "wiki/procedures",
    "wiki/sources",
    "claims",
    "ontology",
    "queues/ingest",
    "queues/review",
    "queues/contradictions",
    "indexes",
    "evals",
    "journal",
    "runs",
    "scripts",
    "hooks",
)

TEMPLATE_TARGETS = {
    "AGENTS.md": "AGENTS.md",
    "KNOWLEDGE.md": "KNOWLEDGE.md",
    "WIKI-OPERATIONS.md": "WIKI-OPERATIONS.md",
    "wiki-index.md": "wiki/index.md",
    "wiki-overview.md": "wiki/overview.md",
    "ontology-schema.yaml": "ontology/schema.yaml",
    "ontology-candidates.yaml": "ontology/candidates.yaml",
    "ontology-aliases.yaml": "ontology/aliases.yaml",
    "eval-questions.yaml": "evals/questions.yaml",
    "hooks/wiki-session-start.py": "hooks/wiki-session-start.py",
    "hooks/wiki-session-end.py": "hooks/wiki-session-end.py",
}


@dataclass(frozen=True)
class ScaffoldResult:
    created: tuple
    preserved: tuple
    pointers: tuple


def _write_json(path, value):
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _render(text, name, purpose):
    return (
        text.replace("{{WIKI_NAME}}", name)
        .replace("{{PURPOSE}}", purpose)
        .replace("{{TODAY}}", date.today().isoformat())
    )


def _templates_dir():
    return Path(__file__).resolve().parent.parent / "templates"


def _validate_pointer(project, vault):
    pointer = project / ".wiki.json"
    if not pointer.exists():
        return
    try:
        current = json.loads(pointer.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"invalid project wiki pointer: {pointer}") from error
    current_vault = current.get("vault")
    if current_vault and Path(current_vault).expanduser().resolve() != vault:
        raise ValueError(f"{pointer} already points to another vault")


def scaffold_vault(vault, name, purpose, projects, excludes):
    vault = Path(vault).expanduser().resolve()
    projects = tuple(Path(project).expanduser().resolve() for project in projects)
    if not projects:
        raise ValueError("at least one project is required")
    if not name.strip():
        raise ValueError("wiki name is required")
    if vault.exists() and not vault.is_dir():
        raise ValueError(f"vault path is not a directory: {vault}")
    for project in projects:
        if not project.is_dir():
            raise ValueError(f"project path is not a directory: {project}")
        _validate_pointer(project, vault)

    created = []
    preserved = []
    vault.mkdir(parents=True, exist_ok=True)
    for relative in DIRECTORIES:
        directory = vault / relative
        directory.mkdir(parents=True, exist_ok=True)

    config_path = vault / "wiki.json"
    config = {
        "version": 1,
        "name": name,
        "purpose": purpose,
        "projects": [str(project) for project in projects],
        "excludes": list(excludes),
    }
    if config_path.exists():
        existing = json.loads(config_path.read_text(encoding="utf-8"))
        if existing != config:
            raise ValueError(f"existing vault configuration differs: {config_path}")
        preserved.append(config_path)
    else:
        _write_json(config_path, config)
        created.append(config_path)

    templates = _templates_dir()
    for source_name, target_name in TEMPLATE_TARGETS.items():
        target = vault / target_name
        if target.exists():
            preserved.append(target)
            continue
        rendered = _render(
            (templates / source_name).read_text(encoding="utf-8"),
            name,
            purpose,
        )
        target.write_text(rendered, encoding="utf-8")
        created.append(target)

    for relative in ("raw/manifest.jsonl", "claims/claims.jsonl", "runs/log.jsonl"):
        target = vault / relative
        if target.exists():
            preserved.append(target)
        else:
            target.touch()
            created.append(target)

    pointers = []
    for project in projects:
        pointer = project / ".wiki.json"
        if not pointer.exists():
            _write_json(
                pointer,
                {
                    "version": 1,
                    "vault": str(vault),
                    "scope": str(project),
                    "excludes": list(excludes),
                },
            )
            created.append(pointer)
        else:
            preserved.append(pointer)
        pointers.append(pointer)

    validator_source = Path(__file__).resolve().parent / "wiki_check.py"
    if validator_source.exists():
        validator_target = vault / "scripts" / "wiki-check.py"
        if validator_target.exists():
            preserved.append(validator_target)
        else:
            shutil.copy2(validator_source, validator_target)
            created.append(validator_target)

    return ScaffoldResult(tuple(created), tuple(preserved), tuple(pointers))
