"""Checks for scripts/source_analysis.py: import classification, aggregation, outlines, and script doc lines."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import source_analysis as sa  # noqa: E402


def test_python_imports_are_classified_and_mapped_to_declared_names() -> None:
    # Asserts stdlib, resolved internal paths (absolute and relative), and external packages under their declared names.
    resolver = sa.Resolver.build({"pkg/cli.py", "pkg/db.py", "tests/test_cli.py"}, ["eyepop-eyeballs", "pillow", "google-cloud-storage", "auth0-python"])
    text = "import sqlite3\nfrom pkg import db\nfrom .db import open_db\nimport eyeballs\nfrom PIL import Image\nfrom google.cloud import storage\nfrom auth0.authentication import GetToken\nimport yaml\n"
    facts = sa.analyze("pkg/cli.py", text, resolver)
    assert facts.stdlib == ("sqlite3",)
    assert facts.internal == ("pkg/db.py", "pkg/db.py")
    assert facts.external == ("eyepop-eyeballs", "pillow", "google-cloud-storage", "auth0-python", "pyyaml")


def test_js_imports_resolve_relative_paths_and_split_scoped_packages() -> None:
    # Asserts relative specifiers resolve to files (with extension or index), scoped packages keep two segments, builtins are stdlib.
    resolver = sa.Resolver.build({"src/app.ts", "src/lib/api.ts", "src/components/Button/index.tsx"}, ["@scope/pkg", "lodash"])
    text = "import { api } from './lib/api';\nimport Button from './components/Button';\nimport { z } from '@scope/pkg/sub';\nimport fs from 'node:fs';\nconst get = require('lodash/get');\n"
    facts = sa.analyze("src/app.ts", text, resolver)
    assert facts.internal == ("src/lib/api.ts", "src/components/Button/index.tsx")
    assert facts.external == ("@scope/pkg", "lodash")
    assert facts.stdlib == ("fs",)


def test_go_imports_split_module_stdlib_and_external() -> None:
    # Asserts module-internal packages become directory keys, dot-less paths are stdlib, and external keys keep host/org/repo.
    resolver = sa.Resolver.build({"cmd/svc/main.go", "internal/store/store.go"}, ["github.com/gin-gonic/gin"], go_module="example.com/svc")
    text = 'package main\n\nimport (\n\t"context"\n\t"example.com/svc/internal/store"\n\t"github.com/gin-gonic/gin/binding"\n)\n'
    facts = sa.analyze("cmd/svc/main.go", text, resolver)
    assert facts.internal == ("internal/store/",)
    assert facts.stdlib == ("context",)
    assert facts.external == ("github.com/gin-gonic/gin",)


def test_aggregate_counts_hubs_and_keeps_test_idioms_apart() -> None:
    # Asserts trivial decorators and builtin bases are dropped, test files feed only hubs, test-only libraries, and test idioms.
    resolver = sa.Resolver.build({"pkg/api.py", "pkg/db.py", "tests/test_api.py"}, ["fastapi", "pytest"])
    production = sa.analyze("pkg/api.py", "from fastapi import APIRouter\nfrom pkg import db\n\nclass Item(str, BaseModel):\n    @property\n    def x(self): ...\n\n@router.get('/')\ndef read() -> int: ...\n", resolver)
    test = sa.analyze("tests/test_api.py", "import pytest\nfrom pkg import db\n\n@pytest.fixture\ndef conn(): ...\n", resolver, test=True)
    facts = sa.aggregate([production, test], lambda path: path.startswith("tests/"))
    assert facts.analyzed == 1
    assert dict(facts.hubs) == {"pkg/db.py": 2}
    assert dict(facts.decorators) == {"@router.get": 1}
    assert dict(facts.bases) == {"BaseModel": 1}
    assert dict(facts.external) == {"fastapi": 1}
    assert dict(facts.external_test_only) == {"pytest": 1}
    assert dict(facts.test_idioms) == {"pytest fixtures": 1}
    assert facts.examples[("test", "pytest fixtures")].path == "tests/test_api.py"
    assert facts.files[("decorator", "@router.get")] == ["pkg/api.py"]


def test_python_outline_lists_definitions_and_wiring_with_line_numbers() -> None:
    # Asserts top-level assignments of calls, decorated defs, classes with their methods, wiring calls, and the main guard each get a line.
    text = "app = FastAPI()\n\n@router.get('/x')\nasync def read(item_id):\n    return 1\n\nclass Repo(Base):\n    def get(self): ...\n    def save(self): ...\n\napp.include_router(router)\nif __name__ == '__main__':\n    main()\n"
    assert sa.outline("pkg/main.py", text + "\n" * 20, 12) == [
        "  L1 app = FastAPI(...)",
        "  L4 @router.get async def read(item_id)",
        "  L7 class Repo(Base): get, save",
        "  L11 app.include_router(router)",
        "  L12 __main__: main()",
    ]


def test_tiny_or_shell_files_outline_as_their_statements() -> None:
    # Asserts a short shell entrypoint shows its commands rather than an empty definition list.
    assert sa.outline("scripts/entrypoint.sh", "#!/bin/sh\n# start the api\nset -e\nexec gunicorn app:app\n", 12) == ["  L3 set -e", "  L4 exec gunicorn app:app"]


def test_doc_line_skips_shebang_and_shell_options_and_reads_docstrings() -> None:
    # Asserts the first substantive comment or docstring line is returned, and nothing when code comes first.
    assert sa.doc_line("#!/usr/bin/env bash\nset -euo pipefail\n# Seed the database with demo rows\npsql < seed.sql\n") == "Seed the database with demo rows"
    assert sa.doc_line('"""Export the OpenAPI schema.\n\nMore detail.\n"""\nimport sys\n') == "Export the OpenAPI schema."
    assert sa.doc_line("#!/bin/sh\nexec gunicorn app:app\n# too late\n") == ""


def test_is_script_path_accepts_script_directories_and_root_shell_files_only() -> None:
    # Asserts scripts/ and bin/ entries and root shell files count, while docs inside scripts/ and package code do not.
    assert sa.is_script_path("scripts/seed.sh")
    assert sa.is_script_path("bin/cli")
    assert sa.is_script_path("deploy.sh")
    assert not sa.is_script_path("scripts/README.md")
    assert not sa.is_script_path("scripts/.env")
    assert not sa.is_script_path("src/app.py")
