import json
import subprocess

import pytest

from trim_comments import (
    Comment, edited_paths, find_comments, is_generated, load_scope, reviewer_model, targets, touched_files,
    worker_model,
)

PY = '''#!/usr/bin/env python3
# /// script
# dependencies = ["x"]
# ///
import os  # noqa: F401
x = 1  # the answer
# increment
y = x + 1
s = "# not a comment"
'''


def test_python_skips_shebang_directives_script_block_and_strings():
    assert find_comments("a.py", PY) == [Comment(6, "the answer"), Comment(7, "increment")]


def test_hash_comments_in_shell_skip_shebang_and_parameter_length():
    source = "#!/bin/sh\n# build it\necho ${#arr} \"#fff\"\n"

    assert find_comments("a.sh", source) == [Comment(2, "build it")]


def test_slash_comments_cover_line_and_block_and_ignore_urls():
    source = (
        "const u = 'http://x.io'; // base url\n"
        "/* header\n"
        "   still comment // inside */\n"
        "// eslint-disable-next-line\n"
        "run();\n"
    )

    assert find_comments("a.ts", source) == [Comment(1, "base url"), Comment(2, "header")]


def test_unknown_extension_has_no_comments():
    assert find_comments("a.md", "# heading\n") == []


def transcript(tmp_path, model):
    path = tmp_path / "t.jsonl"
    path.write_text(json.dumps({"message": {"model": "<synthetic>"}}) + "\n"
                    + json.dumps({"message": {"model": model}}) + "\n"
                    + json.dumps({"type": "user"}) + "\n")
    return str(path)


def test_worker_model_is_the_last_real_assistant_model(tmp_path):
    assert worker_model(transcript(tmp_path, "claude-opus-5-5")) == "claude-opus-5-5"


def test_reviewer_differs_from_worker(tmp_path, monkeypatch):
    monkeypatch.delenv("TRIM_COMMENTS_MODEL", raising=False)

    assert reviewer_model(transcript(tmp_path, "claude-opus-5-5")) == "haiku"
    assert reviewer_model(transcript(tmp_path, "claude-haiku-5-5")) == "sonnet"
    assert reviewer_model("") == "haiku"


def test_model_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIM_COMMENTS_MODEL", "opus")

    assert reviewer_model("") == "opus"


def test_python_docstrings_are_flagged_by_first_line_except_when_they_are_the_whole_body():
    source = (
        '"""Module summary."""\n'
        "import os\n"
        "\n"
        "def f(x):\n"
        '    """Return x.\n'
        "\n"
        '    More detail."""\n'
        "    return x\n"
        "\n"
        "class Empty:\n"
        '    """Only a docstring."""\n'
    )

    assert find_comments("a.py", source) == [Comment(1, "Module summary."), Comment(5, "Return x.")]


def scope_in(tmp_path, config=None):
    (tmp_path / ".commentrc").write_text(json.dumps({} if config is None else config))
    return load_scope(str(tmp_path))


def test_no_commentrc_means_no_scope(tmp_path):
    assert load_scope(str(tmp_path)) is None


def test_empty_commentrc_enables_the_defaults(tmp_path):
    (tmp_path / ".commentrc").write_text("")

    assert load_scope(str(tmp_path)).allows("a.py")


def test_default_scope_takes_known_extensions_and_skips_vendored_and_generated_paths(tmp_path):
    scope = scope_in(tmp_path)

    assert scope.allows("src/a.py")
    assert scope.allows("a.ts")
    assert not scope.allows("README.md")
    assert not scope.allows("node_modules/x/index.js")
    assert not scope.allows("web/dist/app.js")
    assert not scope.allows("web/app.min.js")
    assert not scope.allows("api/service_pb2.py")


def test_include_limits_to_matching_paths(tmp_path):
    scope = scope_in(tmp_path, {"include": ["src/**"]})

    assert scope.allows("src/deep/a.py")
    assert not scope.allows("scripts/a.py")


def test_exclude_extends_the_defaults(tmp_path):
    scope = scope_in(tmp_path, {"exclude": ["**/migrations/**", "tests/**"]})

    assert not scope.allows("app/migrations/0001.py")
    assert not scope.allows("tests/test_a.py")
    assert not scope.allows("vendor/a.py")
    assert scope.allows("app/models.py")


def test_extensions_map_new_suffixes_to_a_style(tmp_path):
    scope = scope_in(tmp_path, {"extensions": {".vue": "slash"}})

    assert scope.allows("a.vue")
    assert find_comments("a.vue", "x // note\n", scope.styles) == [Comment(1, "note")]


def test_unknown_style_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        scope_in(tmp_path, {"extensions": {".lua": "dash"}})


def test_files_with_a_generated_header_have_no_reviewable_comments():
    header = "// Generated from schema by gen.py. Do not edit.\npackage x // note\n"

    assert is_generated(header)
    assert find_comments("protocol.go", header) == []
    assert not is_generated("x = 1\n" * 10 + "# do not edit\n")


def edit_event(name, **args):
    return json.dumps({"message": {"content": [{"type": "tool_use", "name": name, "input": args}]}})


def test_edited_paths_collects_edit_tools_only(tmp_path):
    log = tmp_path / "t.jsonl"
    log.write_text("\n".join([
        edit_event("Edit", file_path="/a/x.py"),
        edit_event("Write", file_path="/b/y.py"),
        edit_event("NotebookEdit", notebook_path="/c/z.ipynb"),
        edit_event("Read", file_path="/d/no.py"),
        "not json",
        json.dumps({"message": "plain"}),
    ]))

    assert edited_paths(str(log)) == {"/a/x.py", "/b/y.py", "/c/z.ipynb"}
    assert edited_paths(str(tmp_path / "missing.jsonl")) == set()


def test_targets_group_session_dirty_files_and_edited_files_by_repo(tmp_path):
    base = tmp_path.resolve()
    for name in ("home", "sdk", "plain"):
        (base / name).mkdir()
    for name in ("home", "sdk"):
        subprocess.run(["git", "init", "-q", str(base / name)], check=True)
    (base / "home" / "dirty.py").write_text("x = 1\n")
    (base / "sdk" / "src").mkdir()
    (base / "sdk" / "src" / "edited.py").write_text("x = 1\n")
    (base / "plain" / "loose.py").write_text("x = 1\n")
    log = base / "t.jsonl"
    log.write_text("\n".join(
        edit_event("Edit", file_path=str(base / name))
        for name in ("sdk/src/edited.py", "plain/loose.py", "sdk/src/gone.py")
    ))

    assert targets(str(base / "home"), str(log)) == {
        str(base / "home"): {"dirty.py"},
        str(base / "sdk"): {"src/edited.py"},
    }


def test_jsdoc_block_with_an_empty_opening_line_is_collected_at_the_opener():
    source = "/**\n * Increment x.\n * More.\n */\nrun();\n/*\n * eslint-disable\n */\n"

    assert find_comments("a.ts", source) == [Comment(1, "Increment x.")]


@pytest.mark.parametrize("config", [
    [], {"extensions": []}, {"extensions": {".x": ["slash"]}}, {"include": "src/**"}, {"exclude": [1]},
])
def test_wrong_config_shapes_raise_value_error(tmp_path, config):
    with pytest.raises(ValueError):
        scope_in(tmp_path, config)


def test_touched_files_include_staged_files_before_the_first_commit_and_unquoted_names(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "staged.py").write_text("x = 1\n")
    (tmp_path / "café.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "staged.py"], check=True)

    assert touched_files(str(tmp_path)) == ["café.py", "staged.py"]
