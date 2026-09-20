#!/usr/bin/env python3
"""Read source files for the survey: imports by package, pattern counts, outlines of key files, and script doc lines."""
from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path

FAMILIES = {
    "py": "python", "pyi": "python", "ts": "js", "tsx": "js", "js": "js", "jsx": "js", "mjs": "js", "cjs": "js",
    "vue": "js", "svelte": "js", "go": "go", "rs": "rust", "rb": "ruby",
}

PYTHON_STDLIB = frozenset(getattr(sys, "stdlib_module_names", ())) or frozenset(
    "__future__ abc argparse array ast asyncio base64 collections concurrent contextlib copy csv ctypes dataclasses "
    "datetime decimal enum errno functools glob gzip hashlib heapq html http importlib inspect io itertools json "
    "logging math multiprocessing operator os pathlib pickle platform queue random re select shlex shutil signal "
    "socket sqlite3 ssl stat string struct subprocess sys tempfile textwrap threading time tomllib traceback types "
    "typing unittest urllib uuid warnings weakref xml zipfile zlib".split()
)

NODE_BUILTINS = frozenset(
    "assert async_hooks buffer child_process cluster console constants crypto dgram diagnostics_channel dns domain "
    "events fs http http2 https inspector module net os path perf_hooks process punycode querystring readline repl "
    "stream string_decoder sys timers tls trace_events tty url util v8 vm wasi worker_threads zlib".split()
)

# Standard-library modules whose use says something about how the code works.
STDLIB_SIGNALS = {
    "python": frozenset("sqlite3 subprocess asyncio threading multiprocessing concurrent socket ssl ctypes pickle shelve dataclasses abc enum argparse signal mmap importlib tkinter unittest".split()),
    "js": frozenset("child_process worker_threads cluster fs net http https crypto stream events".split()),
    "go": frozenset("os/exec net/http database/sql sync context unsafe reflect plugin net/rpc encoding/json".split()),
    "rust": frozenset("std::thread std::sync std::process std::net std::fs std::ffi core::ffi".split()),
    "ruby": frozenset("socket open3 thread fiber fiddle".split()),
}

# Import names that differ from the package name they are declared under.
IMPORT_ALIASES = {
    "PIL": "pillow", "yaml": "pyyaml", "sklearn": "scikit-learn", "cv2": "opencv-python", "dotenv": "python-dotenv",
    "jwt": "pyjwt", "dateutil": "python-dateutil", "bs4": "beautifulsoup4", "attr": "attrs", "tortoise": "tortoise-orm",
    "jose": "python-jose", "multipart": "python-multipart", "magic": "python-magic", "websocket": "websocket-client",
    "serial": "pyserial", "Crypto": "pycryptodome", "OpenSSL": "pyopenssl", "fitz": "pymupdf", "docx": "python-docx",
    "github": "pygithub", "googleapiclient": "google-api-python-client", "nacl": "pynacl", "zmq": "pyzmq",
    "pkg_resources": "setuptools", "gi": "pygobject", "ldap": "python-ldap", "slugify": "python-slugify",
    "MySQLdb": "mysqlclient", "psycopg2": "psycopg2-binary", "prometheus_client": "prometheus-client",
    "telegram": "python-telegram-bot", "socketio": "python-socketio", "engineio": "python-engineio",
    "usb": "pyusb", "Levenshtein": "python-levenshtein", "memcache": "python-memcached",
    "google.protobuf": "protobuf", "typing_extensions": "typing-extensions", "jwcrypto": "jwcrypto",
    "azure.identity": "azure-identity", "azure.storage.blob": "azure-storage-blob", "aiohttp_cors": "aiohttp-cors",
    "sentry_sdk": "sentry-sdk", "email_validator": "email-validator", "pydantic_settings": "pydantic-settings", "dns": "dnspython",
    "opentelemetry": "opentelemetry-api", "dateparser": "dateparser", "ruamel.yaml": "ruamel.yaml",
}

# Declared packages that are tools, not imports; their absence from the import graph means nothing.
TOOL_PACKAGES = frozenset(
    "uvicorn gunicorn hypercorn daphne aerich alembic pip setuptools wheel build twine ruff black isort flake8 pylint "
    "mypy pyright basedpyright pytest coverage tox nox pre-commit ipython jupyter sphinx mkdocs bandit poetry pdm hatch "
    "hatchling typescript vite webpack esbuild rollup parcel eslint prettier jest vitest ts-node tsx nodemon "
    "concurrently cross-env rimraf turbo nx lerna husky lint-staged playwright cypress storybook tailwindcss postcss "
    "autoprefixer sass dotenv-cli npm-run-all serve http-server wait-on supervisor watchdog pip-tools uv autoflake debugpy "
    "email-validator python-multipart uvloop httptools watchfiles setuptools-git-versioning setuptools-scm pylint".split()
)
GENERIC_COMPONENTS = frozenset("python python3 py client api sdk lib core tools utils js ts node cloud google aws azure plugin extra extras binary".split())
BUILTIN_BASES = frozenset("object str int float dict list tuple set bytes bool type Any".split())
TOOL_PREFIXES = ("pytest-", "types-", "@types/", "eslint-", "prettier-", "babel-", "@babel/", "vite-", "webpack-", "rollup-", "@vitejs/", "@storybook/", "@playwright/", "mypy-", "flake8-", "sphinx-", "mkdocs-", "@typescript-eslint/", "@tailwindcss/", "@eslint/", "typescript-")

TRIVIAL_DECORATORS = frozenset("property staticmethod classmethod overload wraps cached_property".split())

IDIOMS = {
    "python": (
        ("Depends(", re.compile(r"\bDepends\(")),
        ("env config", re.compile(r"os\.environ\b|os\.getenv\(|BaseSettings\b|load_dotenv\(")),
        ("getLogger/structlog", re.compile(r"getLogger\(|\bstructlog\b")),
        ("HTTPException", re.compile(r"\bHTTPException\(")),
        ("custom exceptions", re.compile(r"^\s*class \w+\((?:\w+\.)*(?:\w*Error|\w*Exception)\)", re.M)),
        ("raw SQL execute(", re.compile(r"\.execute(?:many)?\(\s*(?:f?[\"']|\w+_sql|sql|query)")),
        ("TypeVar/Generic", re.compile(r"\bTypeVar\(|\bGeneric\[")),
        ("Protocol/ABC", re.compile(r"\bProtocol\b|\bABC\b|@abstractmethod")),
        ("frozen dataclasses", re.compile(r"@dataclass\([^)]*frozen=True|frozen=True")),
        ("pydantic validators", re.compile(r"@(?:field_|model_|root_)?validator\(")),
        ("global state", re.compile(r"^\s*global \w+", re.M)),
        ("match statements", re.compile(r"^\s*match .+:\s*$", re.M)),
        ("generators (yield)", re.compile(r"^\s*yield\b", re.M)),
        ("background tasks", re.compile(r"BackgroundTasks\b|create_task\(|apply_async\(|\.delay\(")),
    ),
    "js": (
        ("React hooks", re.compile(r"\buse(?:State|Effect|Memo|Callback|Ref|Reducer|Context|LayoutEffect)\(")),
        ("custom hooks", re.compile(r"(?:function|const)\s+use[A-Z]\w*")),
        ("createContext", re.compile(r"createContext[<(]")),
        ("routes", re.compile(r"\b(?:app|router|server|fastify)\.(?:get|post|put|patch|delete|use|route)\(")),
        ("async", re.compile(r"\basync\b")),
        ("process.env", re.compile(r"process\.env\b|import\.meta\.env\b")),
        ("TS interfaces/types", re.compile(r"^\s*(?:export\s+)?(?:interface|type)\s+\w+", re.M)),
        ("classes", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+\w+", re.M)),
        ("custom errors", re.compile(r"class \w+ extends \w*Error\b")),
        ("zod schemas", re.compile(r"\bz\.(?:object|string|number|array|enum)\(")),
        ("react-query", re.compile(r"\buse(?:Query|Mutation|InfiniteQuery)\(")),
        ("redux", re.compile(r"createSlice\(|useSelector\(|useDispatch\(")),
        ("Nest/Angular decorators", re.compile(r"@(?:Injectable|Controller|Module|Component|Get|Post)\(")),
        ("styled-components", re.compile(r"\bstyled\.\w+`|\bstyled\(")),
        ("tailwind classes", re.compile(r"className=[\"'][^\"']*\b(?:flex|grid|px-\d|py-\d|text-\w)")),
        ("'use client'/'use server'", re.compile(r"[\"']use (?:client|server)[\"']")),
        ("JSX", re.compile(r"<[A-Z]\w*[\s/>]")),
        ("event emitters", re.compile(r"\.on\([\"']\w+[\"']|emit\([\"']")),
    ),
    "go": (
        ("interfaces", re.compile(r"^type \w+ interface", re.M)),
        ("structs", re.compile(r"^type \w+ struct", re.M)),
        ("goroutines", re.compile(r"\bgo (?:func|\w+(?:\.\w+)?)\(")),
        ("channels", re.compile(r"\bchan\b")),
        ("context.Context", re.compile(r"context\.Context\b")),
        ("http handlers", re.compile(r"http\.Handle(?:Func)?\(|\.(?:GET|POST|PUT|DELETE|PATCH|Handle|HandleFunc)\(")),
        ("error wrapping", re.compile(r"fmt\.Errorf\(|errors\.(?:Is|As|Join|Wrap)\(")),
        ("sync primitives", re.compile(r"sync\.(?:Mutex|RWMutex|WaitGroup|Once|Map)\b")),
        ("database/sql or ORM", re.compile(r"sql\.(?:DB|Open)\b|gorm\.|sqlx\.|pgx\.|ent\.")),
        ("generics", re.compile(r"\[[A-Z]\w* (?:any|comparable|constraints\.)")),
        ("cobra/cli", re.compile(r"cobra\.Command\{|cli\.Command\{|flag\.\w+\(")),
    ),
    "rust": (
        ("traits", re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?trait \w+", re.M)),
        ("impl blocks", re.compile(r"^\s*impl(?:<[^>]+>)? ", re.M)),
        ("async fn", re.compile(r"\basync fn\b")),
        ("derives", re.compile(r"#\[derive\(")),
        ("Arc/Mutex", re.compile(r"\bArc<|\bMutex<|\bRwLock<")),
        ("unsafe", re.compile(r"\bunsafe\b")),
        ("dyn Trait", re.compile(r"\bdyn \w+")),
        ("Result returns", re.compile(r"-> (?:\w+::)*Result<")),
        ("macros defined", re.compile(r"macro_rules!")),
        ("tokio", re.compile(r"\btokio::")),
    ),
    "ruby": (
        ("classes", re.compile(r"^\s*class \w+", re.M)),
        ("modules", re.compile(r"^\s*module \w+", re.M)),
        ("ActiveRecord", re.compile(r"< (?:ApplicationRecord|ActiveRecord::Base)\b")),
        ("controllers", re.compile(r"< (?:ApplicationController|ActionController::\w+)\b")),
        ("Sidekiq/ActiveJob", re.compile(r"include Sidekiq::(?:Worker|Job)|< ApplicationJob\b")),
        ("concerns", re.compile(r"extend ActiveSupport::Concern")),
    ),
}

TEST_IDIOMS = {
    "python": (
        ("pytest fixtures", re.compile(r"@pytest\.fixture|@fixture\b")),
        ("parametrize", re.compile(r"parametrize\(")),
        ("mock/patch", re.compile(r"\bpatch\(|\bpatch\.object\(|MagicMock\b|AsyncMock\b|mocker\.")),
        ("TestClient/AsyncClient", re.compile(r"TestClient\(|AsyncClient\(")),
        ("HTTP mocking", re.compile(r"\brespx\b|\bresponses\.|requests_mock|httpretty|aioresponses")),
        ("factories", re.compile(r"\w+Factory\b")),
        ("hypothesis", re.compile(r"from hypothesis|@given\(")),
        ("unittest.TestCase", re.compile(r"\(\s*(?:unittest\.)?(?:Isolated(?:Async)?)?TestCase\s*\)")),
        ("markers", re.compile(r"@pytest\.mark\.\w+")),
        ("snapshot", re.compile(r"\bsnapshot\b|syrupy")),
    ),
    "js": (
        ("describe/it", re.compile(r"^\s*(?:describe|it|test)\(", re.M)),
        ("mocks", re.compile(r"\b(?:jest|vi)\.(?:mock|fn|spyOn)\(")),
        ("testing-library render", re.compile(r"\brender\(|\bscreen\.")),
        ("msw", re.compile(r"\bmsw\b|setupServer\(")),
        ("supertest", re.compile(r"\bsupertest\b|request\(app\)")),
        ("nock", re.compile(r"\bnock\(")),
        ("playwright/cypress", re.compile(r"\bpage\.\w+\(|\bcy\.\w+\(")),
        ("snapshots", re.compile(r"toMatch(?:Inline)?Snapshot\(")),
    ),
    "go": (
        ("table tests", re.compile(r"tests := \[\]struct|for _, (?:tt|tc|c) := range")),
        ("testify", re.compile(r"\bassert\.\w+\(|\brequire\.\w+\(")),
        ("httptest", re.compile(r"httptest\.")),
        ("gomock/mockery", re.compile(r"gomock\.|mocks\.")),
    ),
    "rust": (
        ("#[test]", re.compile(r"#\[(?:tokio::)?test\]")),
        ("proptest", re.compile(r"proptest!|quickcheck")),
    ),
    "ruby": (
        ("rspec", re.compile(r"^\s*(?:describe|context|it)\b", re.M)),
        ("factory_bot", re.compile(r"FactoryBot\.|\bcreate\(:")),
        ("webmock/vcr", re.compile(r"WebMock|VCR\.")),
    ),
}

JS_DEFINITION = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(function\*?|class|abstract class|const|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)")
JS_ROUTE = re.compile(r"^\s*(?:app|router|server|fastify)\.(get|post|put|patch|delete|use|route|listen)\(\s*((?:['\"`][^'\"`]*['\"`])?)")
JS_DECORATED = re.compile(r"^\s*@(Get|Post|Put|Patch|Delete|Controller|Injectable|Module|Component|Input|Output)\(([^)]*)\)")
JS_DEFAULT = re.compile(r"^export default (?:async\s+)?(?:function\s+)?([A-Za-z_$][\w$]*)")
GO_FUNC = re.compile(r"^func\s+(?:\(\s*\w+\s+\*?(\w+)\s*\)\s*)?(\w+)\(")
GO_TYPE = re.compile(r"^type\s+(\w+)\s+(struct|interface)")
GO_ROUTE = re.compile(r"(?:HandleFunc|Handle|GET|POST|PUT|DELETE|PATCH)\(\s*(\"[^\"]*\")")
RUST_ITEM = re.compile(r"^\s{0,4}(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(fn|struct|enum|trait|impl|mod|type)\s+([\w<>:'&, ]+?)(?:\s*[({<;=]|\s+for\s+([\w<>:]+)|\s+where|\s*$)")
RUBY_ITEM = re.compile(r"^\s{0,2}(class|module|def)\s+([\w:.?!]+)(?:\s*<\s*([\w:]+))?")
GENERIC_ITEM = re.compile(r"^\s*(def|class|function|func|fn|module|struct|interface|sub|proc|defmodule|defn|object|trait)\s+([\w:.]+)")

SCRIPT_DIRS = frozenset({"scripts", "script", "bin", "tools", "tool", "hack", "ci", "dev", "devtools", ".github/scripts"})
COMMENT_SKIP = re.compile(r"^(#!|# -\*-|#\s*shellcheck|#\s*vim:|#\s*coding|//\s*eslint|#\s*(?:set|export)\s|#\s*-{3,}|#\s*={3,}|#\s*\*+\s*$|#\s*Copyright|#\s*Licensed|#\s*SPDX)", re.I)


@dataclass(frozen=True)
class FileFacts:
    path: str
    external: tuple[str, ...] = ()
    internal: tuple[str, ...] = ()
    stdlib: tuple[str, ...] = ()
    decorators: tuple[tuple[str, int], ...] = ()
    bases: tuple[tuple[str, int], ...] = ()
    idioms: tuple[tuple[str, int], ...] = ()
    definitions: int = 0
    typed_definitions: int = 0
    async_definitions: int = 0


@dataclass(frozen=True)
class Example:
    count: int
    path: str


@dataclass
class CodeFacts:
    """Aggregate of every analyzed file; counts are files unless the name says otherwise."""
    analyzed: int = 0
    external: Counter = field(default_factory=Counter)
    external_test_only: Counter = field(default_factory=Counter)
    external_dirs: dict = field(default_factory=dict)
    hubs: Counter = field(default_factory=Counter)
    stdlib: dict = field(default_factory=dict)
    decorators: Counter = field(default_factory=Counter)
    bases: Counter = field(default_factory=Counter)
    idioms: Counter = field(default_factory=Counter)
    test_idioms: Counter = field(default_factory=Counter)
    examples: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)
    dirs: Counter = field(default_factory=Counter)
    definition_files: int = 0
    typed_files: int = 0


@dataclass(frozen=True)
class Resolver:
    files: frozenset
    python_roots: tuple
    internal_names: frozenset
    go_module: str
    declared: dict
    components: dict

    @classmethod
    def build(cls, files, declared_names, go_module: str = "") -> "Resolver":
        names = set()
        for rel in files:
            if not rel.endswith((".py", ".pyi")):
                continue
            parts = rel.split("/")
            names.add(parts[0] if len(parts) > 1 else parts[0].rsplit(".", 1)[0])
            if len(parts) > 2 and parts[0] in ("src", "lib", "python"):
                names.add(parts[1])
        declared = {normalize(name): name for name in declared_names}
        components: dict = {}
        for position in (0, -1):
            for key in declared:
                parts = key.split("-")
                if len(parts) >= 2 and len(parts[position]) >= 3 and parts[position] not in GENERIC_COMPONENTS:
                    components.setdefault(parts[position], key)
        return cls(frozenset(files), ("", "src/", "lib/", "python/"), frozenset(names), go_module, declared, components)

    def python_module_path(self, module: str, names=()) -> str:
        dotted = module.replace(".", "/")
        for prefix in self.python_roots:
            for name in names:
                for candidate in (f"{prefix}{dotted}/{name}.py", f"{prefix}{dotted}/{name}/__init__.py"):
                    if candidate in self.files:
                        return candidate
            for candidate in (f"{prefix}{dotted}.py", f"{prefix}{dotted}/__init__.py"):
                if candidate in self.files:
                    return candidate
        return ""

    def package_key(self, family: str, module: str) -> str:
        """Map an import to the declared package name when one matches, else to its normalized top-level name."""
        parts = module.split(".") if family == "python" else [module]
        for depth in range(min(len(parts), 3), 0, -1):
            prefix = ".".join(parts[:depth])
            dashed = prefix.replace(".", "-")
            for candidate in (IMPORT_ALIASES.get(prefix, ""), dashed, re.sub(r"[-_]?v\d+$", "", dashed)):
                if candidate and normalize(candidate) in self.declared:
                    return normalize(candidate)
        top = normalize(IMPORT_ALIASES.get(parts[0], parts[0]))
        return top if top in self.declared else self.components.get(top, top)


def normalize(name: str) -> str:
    return name.lower().replace("_", "-").strip()


def is_tool(name: str) -> bool:
    key = normalize(name)
    return key in TOOL_PACKAGES or key.startswith(TOOL_PREFIXES)


def family_of(rel: str) -> str:
    name = rel.rsplit("/", 1)[-1]
    return FAMILIES.get(name.rsplit(".", 1)[-1].lower() if "." in name[1:] else "", "")


ANALYZERS = {"python": lambda *a: analyze_python(*a), "js": lambda *a: analyze_js(*a), "go": lambda *a: analyze_go(*a), "rust": lambda *a: analyze_rust(*a), "ruby": lambda *a: analyze_ruby(*a)}


def analyze(rel: str, text: str, resolver: Resolver, test: bool = False) -> FileFacts:
    """Facts for one file; a test file is scanned for test idioms instead of production ones."""
    family = family_of(rel)
    analyzer = ANALYZERS.get(family)
    if analyzer is None:
        return FileFacts(rel)
    facts = analyzer(rel, text, resolver)
    idioms = list(idiom_counts(family, text, TEST_IDIOMS if test else IDIOMS))
    if facts.async_definitions and not test:
        idioms.append(("async def", facts.async_definitions))
    return replace(facts, idioms=tuple(idioms))


def idiom_counts(family: str, text: str, table) -> tuple:
    found = []
    for label, pattern in table.get(family, ()):
        count = len(pattern.findall(text))
        if count:
            found.append((label, count))
    return tuple(found)


def analyze_python(rel: str, text: str, resolver: Resolver) -> FileFacts:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return FileFacts(rel)
    external, internal, stdlib = [], [], []
    package_dir = rel.rsplit("/", 1)[0] if "/" in rel else ""

    def classify(module: str, names) -> None:
        top = module.split(".")[0]
        if top in PYTHON_STDLIB:
            stdlib.append(top)
        elif path := resolver.python_module_path(module, names):
            internal.append(path)
        elif top in resolver.internal_names or (package_dir and resolver.python_module_path(f"{package_dir.replace('/', '.')}.{module}", names)):
            internal.append(resolver.python_module_path(f"{package_dir.replace('/', '.')}.{module}", names) or module)
        else:
            keys = [resolver.package_key("python", f"{module}.{name}") for name in names] + [resolver.package_key("python", module)]
            external.append(next((k for k in keys if k in resolver.declared), keys[-1]))

    decorators, bases = Counter(), Counter()
    definitions = typed = async_definitions = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                classify(alias.name, ())
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            if node.level:
                base = package_dir.split("/") if package_dir else []
                base = base[: len(base) - (node.level - 1)] if node.level > 1 else base
                module = ".".join(base + ([node.module] if node.module else []))
                internal.append(resolver.python_module_path(module, names) or module)
            else:
                classify(node.module or "", names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions += 1
            typed += node.returns is not None
            async_definitions += isinstance(node, ast.AsyncFunctionDef)
            for decorator in node.decorator_list:
                decorators[decorator_name(decorator)] += 1
        elif isinstance(node, ast.ClassDef):
            for decorator in node.decorator_list:
                decorators[decorator_name(decorator)] += 1
            for base in node.bases:
                bases[base_name(base)] += 1
    return FileFacts(
        rel, tuple(external), tuple(p for p in internal if p != rel), tuple(stdlib),
        tuple(decorators.items()), tuple(bases.items()), (), definitions, typed, async_definitions,
    )


def decorator_name(node: ast.expr) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    return "@" + ast.unparse(target)


def base_name(node: ast.expr) -> str:
    return ast.unparse(node.value if isinstance(node, ast.Subscript) else node)


JS_IMPORT = re.compile(
    r"""(?:^|[^\w.$])(?:import|export)\s*(?:[^'";]*?\s+from\s*)?['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\(\s*['"]([^'"]+)['"]\s*\)""",
    re.M,
)
JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".d.ts")


def resolve_js(rel: str, specifier: str, resolver: Resolver) -> str:
    base = str(Path(rel).parent / specifier) if specifier.startswith(".") else specifier
    if specifier.startswith(("@/", "~/", "src/")):
        base = "src/" + specifier.split("/", 1)[1] if not specifier.startswith("src/") else specifier
    normalized = str(Path(base)).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    candidates = [normalized] + [normalized + ext for ext in JS_EXTENSIONS] + [f"{normalized}/index{ext}" for ext in JS_EXTENSIONS]
    return next((c for c in candidates if c in resolver.files), normalized)


def analyze_js(rel: str, text: str, resolver: Resolver) -> FileFacts:
    external, internal, stdlib = [], [], []
    for match in JS_IMPORT.finditer(text):
        specifier = next(g for g in match.groups() if g)
        if specifier.startswith((".", "@/", "~/", "src/", "#")):
            internal.append(resolve_js(rel, specifier, resolver))
        elif specifier.startswith("node:") or specifier.split("/")[0] in NODE_BUILTINS:
            stdlib.append(specifier.removeprefix("node:").split("/")[0])
        else:
            parts = specifier.split("/")
            external.append(resolver.package_key("js", "/".join(parts[:2]) if specifier.startswith("@") else parts[0]))
    decorators = Counter("@" + m.group(1) for m in re.finditer(r"^\s*@(\w+)\(", text, re.M))
    bases = Counter(m.group(1) for m in re.finditer(r"\bclass\s+\w+\s+extends\s+([\w.]+)", text))
    definitions = len(re.findall(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|class)\s+\w+|=>", text, re.M))
    return FileFacts(rel, tuple(external), tuple(p for p in internal if p != rel), tuple(stdlib), tuple(decorators.items()), tuple(bases.items()), (), definitions)


GO_IMPORT_BLOCK = re.compile(r"^import\s*\((.*?)^\)", re.M | re.S)
GO_IMPORT_LINE = re.compile(r'^import\s+(?:\w+\s+)?"([^"]+)"', re.M)


def analyze_go(rel: str, text: str, resolver: Resolver) -> FileFacts:
    paths = GO_IMPORT_LINE.findall(text)
    for block in GO_IMPORT_BLOCK.findall(text):
        paths += re.findall(r'"([^"]+)"', block)
    external, internal, stdlib = [], [], []
    for path in paths:
        if resolver.go_module and (path == resolver.go_module or path.startswith(resolver.go_module + "/")):
            package = path[len(resolver.go_module):].strip("/")
            internal.append(package + "/" if package else "./")
        elif "." not in path.split("/")[0]:
            stdlib.append(path)
        else:
            external.append(resolver.package_key("go", "/".join(path.split("/")[:3])))
    bases = Counter(m.group(1) for m in re.finditer(r"^\s+(\*?[A-Z]\w*(?:\.[A-Z]\w*)?)\s*$", text, re.M))
    definitions = len(GO_FUNC.findall(text))
    return FileFacts(rel, tuple(external), tuple(internal), tuple(stdlib), (), tuple(bases.items()), (), definitions)


RUST_USE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?use\s+([\w:]+)", re.M)


def analyze_rust(rel: str, text: str, resolver: Resolver) -> FileFacts:
    external, internal, stdlib = [], [], []
    for match in RUST_USE.finditer(text):
        parts = match.group(1).split("::")
        if parts[0] in ("crate", "self", "super"):
            module = parts[1] if len(parts) > 1 and parts[0] == "crate" else ""
            candidates = (f"src/{module}.rs", f"src/{module}/mod.rs") if module else ()
            internal.append(next((c for c in candidates if c in resolver.files), "crate::" + "::".join(parts[1:2])))
        elif parts[0] in ("std", "core", "alloc"):
            stdlib.append("::".join(parts[:2]))
        else:
            external.append(resolver.package_key("rust", parts[0]))
    bases = Counter(m.group(1) for m in re.finditer(r"^\s*impl(?:<[^>]+>)?\s+([\w:]+)(?:<[^>]+>)?\s+for\s+", text, re.M))
    decorators = Counter("#[" + m.group(1) + "]" for m in re.finditer(r"#\[(\w+(?:::\w+)*)", text))
    definitions = len(re.findall(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+\w+", text, re.M))
    async_definitions = len(re.findall(r"\basync fn\b", text))
    return FileFacts(rel, tuple(external), tuple(p for p in internal if p != rel), tuple(stdlib), tuple(decorators.items()), tuple(bases.items()), (), definitions, 0, async_definitions)


RUBY_REQUIRE = re.compile(r"^\s*require(_relative)?\s+['\"]([^'\"]+)['\"]", re.M)


def analyze_ruby(rel: str, text: str, resolver: Resolver) -> FileFacts:
    external, internal, stdlib = [], [], []
    for relative, name in RUBY_REQUIRE.findall(text):
        candidate = f"lib/{name}.rb"
        if relative:
            internal.append(str(Path(rel).parent / f"{name}.rb"))
        elif candidate in resolver.files:
            internal.append(candidate)
        elif name.split("/")[0] in STDLIB_SIGNALS["ruby"] or name in ("json", "set", "time", "date", "uri", "net/http", "fileutils", "logger", "yaml", "csv", "erb", "digest", "securerandom", "tempfile", "pathname", "optparse", "open-uri"):
            stdlib.append(name)
        else:
            external.append(resolver.package_key("ruby", name.split("/")[0]))
    bases = Counter(m.group(1) for m in re.finditer(r"^\s*class\s+[\w:]+\s*<\s*([\w:]+)", text, re.M))
    definitions = len(re.findall(r"^\s*def\s+\w+", text, re.M))
    return FileFacts(rel, tuple(external), tuple(p for p in internal if p != rel), tuple(stdlib), (), tuple(bases.items()), (), definitions)


def aggregate(facts, is_test) -> CodeFacts:
    """Fold per-file facts into project-wide counts; tests count for hubs and test idioms only."""
    total = CodeFacts()

    def note(kind: str, label: str, count: int, path: str) -> None:
        """Remember the heaviest file for each item, and the first three files so small counts can be listed in full."""
        key = (kind, label)
        if count > total.examples.get(key, Example(0, "")).count:
            total.examples[key] = Example(count, path)
        if len(total.files.setdefault(key, [])) < 3:
            total.files[key].append(path)

    for fact in facts:
        family = family_of(fact.path)
        if not family:
            continue
        for hub in set(fact.internal):
            total.hubs[hub] += 1
        if is_test(fact.path):
            for key in set(fact.external):
                total.external_test_only[key] += 1
            for label, count in fact.idioms:
                total.test_idioms[label] += 1
                note("test", label, count, fact.path)
            continue
        total.analyzed += 1
        directory = "/".join(fact.path.split("/")[:2]) if fact.path.count("/") >= 2 else fact.path.rsplit("/", 1)[0] if "/" in fact.path else ""
        total.dirs[directory] += 1
        for key in set(fact.external):
            total.external[key] += 1
            total.external_dirs.setdefault(key, Counter())[directory] += 1
        for module in set(fact.stdlib):
            if module in STDLIB_SIGNALS.get(family, ()):
                total.stdlib.setdefault(module, []).append(fact.path)
        for name, count in fact.decorators:
            if name.lstrip("@").rsplit(".", 1)[-1] not in TRIVIAL_DECORATORS:
                total.decorators[name] += 1
                note("decorator", name, count, fact.path)
        for name, count in fact.bases:
            if name not in BUILTIN_BASES:
                total.bases[name] += 1
                note("base", name, count, fact.path)
        for label, count in fact.idioms:
            total.idioms[label] += 1
            note("idiom", label, count, fact.path)
        if fact.definitions:
            total.definition_files += 1
            total.typed_files += fact.typed_definitions * 2 >= fact.definitions
    for key in list(total.external_test_only):
        if key in total.external:
            del total.external_test_only[key]
    return total


def outline(rel: str, text: str, cap: int) -> list[str]:
    """Top-level definitions with line numbers; a tiny or shell file shows its statements instead."""
    family = family_of(rel)
    source_lines = text.splitlines()
    if not family or len(source_lines) <= cap + 3:
        statements = [f"  L{n} {line.strip()[:110]}" for n, line in enumerate(source_lines, 1) if line.strip() and not line.strip().startswith(("#", "//", "from ", "import ", "use ", "require"))]
        return statements[:cap]
    if family == "python":
        lines = python_outline(text)
    elif family == "js":
        lines = js_outline(text)
    elif family == "go":
        lines = go_outline(text)
    elif family == "rust":
        lines = regex_outline(text, RUST_ITEM, lambda m: f"{m.group(1)} {m.group(2).strip()}" + (f" for {m.group(3)}" if m.group(3) else ""))
    elif family == "ruby":
        lines = regex_outline(text, RUBY_ITEM, lambda m: f"{m.group(1)} {m.group(2)}" + (f" < {m.group(3)}" if m.group(3) else ""))
    else:
        lines = regex_outline(text, GENERIC_ITEM, lambda m: f"{m.group(1)} {m.group(2)}")
    if len(lines) > cap:
        lines = lines[: cap - 1] + [f"  ... +{len(lines) - cap + 1} more definitions"]
    return lines


def python_outline(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return regex_outline(text, GENERIC_ITEM, lambda m: f"{m.group(1)} {m.group(2)}")
    lines = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = decorator_summary(node)
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            lines.append(f"  L{node.lineno} {decorators + ' ' if decorators else ''}{prefix} {node.name}({signature(node)})")
        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases)
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            shown = ", ".join(methods[:5]) + (f", +{len(methods) - 5}" if len(methods) > 5 else "")
            decorators = decorator_summary(node)
            lines.append(f"  L{node.lineno} {decorators + ' ' if decorators else ''}class {node.name}({bases})" + (f": {shown}" if methods else ""))
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            lines.append(f"  L{node.lineno} {node.targets[0].id} = {ast.unparse(node.value.func)}(...)")
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            lines.append(f"  L{node.lineno} {ast.unparse(node.value)[:90]}")
        elif isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
            first = ast.unparse(node.body[0])[:70] if node.body else ""
            lines.append(f"  L{node.lineno} __main__: {first}")
    return lines


def decorator_summary(node) -> str:
    counts = Counter(decorator_name(d) for d in node.decorator_list)
    return " ".join(f"{name}x{n}" if n > 1 else name for name, n in counts.items())


def signature(node) -> str:
    args = node.args
    names = [a.arg for a in args.posonlyargs + args.args]
    if args.vararg:
        names.append("*" + args.vararg.arg)
    names += [a.arg for a in args.kwonlyargs]
    if args.kwarg:
        names.append("**" + args.kwarg.arg)
    return ", ".join(names[:6]) + (", ..." if len(names) > 6 else "")


def js_outline(text: str) -> list[str]:
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        if match := JS_DEFINITION.match(line):
            kind, name = match.groups()
            if kind in ("const", "let", "var") and not re.search(r"=\s*(?:async\s*)?(?:\(|function|\w+\s*=>|new\s+\w+|create\w*\(|express\(|Router\(|new\s)", line):
                continue
            lines.append(f"  L{number} {kind} {name}")
        elif match := JS_ROUTE.match(line):
            lines.append(f"  L{number} {match.group(0).strip().split('.')[0]}.{match.group(1)}({match.group(2)})")
        elif match := JS_DECORATED.match(line):
            lines.append(f"  L{number} @{match.group(1)}({match.group(2)[:40]})")
        elif match := JS_DEFAULT.match(line):
            lines.append(f"  L{number} export default {match.group(1)}")
    return lines


def go_outline(text: str) -> list[str]:
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        if match := GO_FUNC.match(line):
            receiver, name = match.groups()
            lines.append(f"  L{number} func {'(' + receiver + ').' if receiver else ''}{name}")
        elif match := GO_TYPE.match(line):
            lines.append(f"  L{number} type {match.group(1)} {match.group(2)}")
        elif match := GO_ROUTE.search(line):
            lines.append(f"  L{number} route {match.group(1)}")
    return lines


def regex_outline(text: str, pattern: re.Pattern, render) -> list[str]:
    return [f"  L{number} {render(match)}" for number, line in enumerate(text.splitlines(), 1) if (match := pattern.match(line))]


def is_script_path(rel: str) -> bool:
    parts = rel.split("/")
    if len(parts) == 1:
        return rel.endswith((".sh", ".bash", ".zsh"))
    inside = parts[0] in SCRIPT_DIRS or "/".join(parts[:2]) in SCRIPT_DIRS
    return inside and len(parts) <= 4 and not parts[-1].startswith((".", "_")) and not parts[-1].endswith((".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sql", ".conf", ".env", ".lock"))


def doc_line(text: str) -> str:
    """The first line of a script that says what it does: a module docstring or the first real comment."""
    head = text[:4000].splitlines()[:40]
    for index, raw in enumerate(head):
        line = raw.strip()
        if match := re.match(r"^[rRuUbB]*(\"\"\"|''')\s*(.*)$", line):
            body = match.group(2).split(match.group(1))[0].strip()
            if not body and index + 1 < len(head):
                body = head[index + 1].strip().strip("\"'")
            return body[:100]
        if line.startswith(("#", "//", "--", "REM ")) and not COMMENT_SKIP.match(line):
            body = re.sub(r"^(?:#+|/+|-+|REM)\s*", "", line).strip()
            if len(body) > 3:
                return body[:100]
        if line and not line.startswith(("#", "//", "--", "import ", "from ", "use ", "package ", "set ", "export ", "source ", ".", "'use", '"use', "require")):
            return ""
    return ""
