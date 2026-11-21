import json
import os
import subprocess
import sys
import time

import pytest

from no_comment import (
    Comment, edit_is_safe, edited_paths, find_comments, is_generated, load_scope, review_repo, reviewer_model,
    python_docstrings, python_shape, read_hook_input, run_reviewer, survey, targets, touched_files,
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
    monkeypatch.delenv("NO_COMMENT_MODEL", raising=False)

    assert reviewer_model(transcript(tmp_path, "claude-opus-5-5")) == "haiku"
    assert reviewer_model(transcript(tmp_path, "claude-haiku-5-5")) == "sonnet"
    assert reviewer_model("") == "haiku"


def test_model_env_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("NO_COMMENT_MODEL", "opus")

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


def fake_claude(tmp_path, monkeypatch, mode):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "claude"
    script.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        "mode = os.environ['FAKE_CLAUDE']\n"
        "if os.environ.get('FAKE_LOG'):\n"
        "    open(os.environ['FAKE_LOG'], 'a').write('x')\n"
        "if mode == 'fail':\n"
        "    sys.stderr.write('quota'); sys.exit(1)\n"
        "lines = open('a.py').read().splitlines(True)\n"
        "if mode == 'trim':\n"
        "    lines = [l for l in lines if '# note' not in l]\n"
        "if mode == 'mangle':\n"
        "    lines = [l.replace('return x', 'return 0') for l in lines if '# note' not in l]\n"
        "if mode == 'mangle_fail':\n"
        "    open('a.py', 'w').write('def f(x):\\n    return 0\\n')\n"
        "    open('other.py', 'a').write('x = 2\\n')\n"
        "    sys.stderr.write('quota'); sys.exit(1)\n"
        "if mode == 'badbytes':\n"
        "    open('a.py', 'wb').write(b'\\xff\\xfe not utf8\\n')\n"
        "    sys.exit(0)\n"
        "if mode == 'truncate':\n"
        "    open('other.py', 'w').write('y\\n')\n"
        "if mode == 'stray':\n"
        "    open('other.py', 'a').write('x = 2\\n')\n"
        "if mode == 'create':\n"
        "    open('made.py', 'w').write('z = 1\\n')\n"
        "open('a.py', 'w').write(''.join(lines))\n"
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE", mode)


def repo_with_comment(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".commentrc").write_text("{}")
    (tmp_path / "a.py").write_text("def f(x):\n    # note\n    return x\n")
    (tmp_path / "other.py").write_text("y = 1\n")


def review(tmp_path, rels=("a.py",)):
    return review_repo(str(tmp_path), set(rels), "haiku", False, time.monotonic() + 60)


def test_review_trims_a_comment(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    fake_claude(tmp_path, monkeypatch, "trim")

    assert "removed 1 of 1 comments in 1 files" in review(tmp_path)
    assert (tmp_path / "a.py").read_text() == "def f(x):\n    return x\n"


def test_review_skips_a_file_whose_content_was_already_reviewed(tmp_path, tmp_path_factory, monkeypatch):
    repo_with_comment(tmp_path)
    log = tmp_path_factory.mktemp("log") / "calls.log"
    monkeypatch.setenv("FAKE_LOG", str(log))
    fake_claude(tmp_path, monkeypatch, "keep")

    assert "removed 0 of 1 comments" in review(tmp_path)
    assert review(tmp_path) is None
    assert log.read_text() == "x"


def test_review_restores_a_file_whose_code_changed(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    original = (tmp_path / "a.py").read_text()
    fake_claude(tmp_path, monkeypatch, "mangle")

    message = review(tmp_path)

    assert "reverted unsafe edit to a.py" in message
    assert (tmp_path / "a.py").read_text() == original
    (rejected,) = (tmp_path / ".git" / "no-comment-rejected").glob("a.py.*")
    assert "return 0" in rejected.read_text()


def test_review_reports_files_changed_outside_the_flagged_set(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    fake_claude(tmp_path, monkeypatch, "stray")

    assert "reverted reviewer edits to other.py" in review(tmp_path)
    assert (tmp_path / "other.py").read_text() == "y = 1\n"


def test_review_reports_a_failing_reviewer_and_leaves_files_alone(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    original = (tmp_path / "a.py").read_text()
    fake_claude(tmp_path, monkeypatch, "fail")

    assert "reviewer (haiku) failed: quota" in review(tmp_path)
    assert (tmp_path / "a.py").read_text() == original


def test_review_without_commentrc_does_nothing(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    (tmp_path / ".commentrc").unlink()
    fake_claude(tmp_path, monkeypatch, "trim")

    assert review(tmp_path) is None
    assert "# note" in (tmp_path / "a.py").read_text()


def test_edit_is_safe_ignores_docstrings_but_not_code():
    styles = {".py": "python", ".sh": "hash"}
    old = 'def f(x):\n    """Return x."""\n    return x\n'

    assert edit_is_safe("a.py", old, "def f(x):\n    return x\n", styles)
    assert not edit_is_safe("a.py", old, 'def f(x):\n    """Return x."""\n    return 0\n', styles)
    assert not edit_is_safe("a.py", old, "def f(x:\n", styles)
    assert edit_is_safe("a.sh", "echo a  # b\n# c\n\nls\n", "echo a\n\nls\n", styles)
    assert not edit_is_safe("a.sh", "echo a  # b\nls\n", "echo b\nls\n", styles)


def test_more_directives_and_ruby_interpolation_are_not_comments():
    ts = '/// <reference types="node" />\nconst a = 1; // biome-ignore lint: x\n'
    rb = '# frozen_string_literal: true\nputs "Hello #{name}"\nx = 1 # nosec\n'

    assert find_comments("a.ts", ts) == []
    assert find_comments("a.rb", rb) == []


def test_a_stray_script_marker_does_not_swallow_later_comments():
    source = "# /// note\nx = 1  # real\n"

    assert find_comments("a.py", source) == [Comment(1, "/// note"), Comment(2, "real")]


def test_review_restores_a_clean_tracked_file_the_reviewer_changed(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    subprocess.run(["git", "-C", str(tmp_path), "add", "other.py"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "i"], check=True
    )
    fake_claude(tmp_path, monkeypatch, "stray")

    assert "reverted reviewer edits to other.py" in review(tmp_path)
    assert (tmp_path / "other.py").read_text() == "y = 1\n"


def test_revert_keeps_crlf_line_endings(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    original = b"def f(x):\r\n    # note\r\n    return x\r\n"
    (tmp_path / "a.py").write_bytes(original)
    fake_claude(tmp_path, monkeypatch, "mangle")

    review(tmp_path)

    assert (tmp_path / "a.py").read_bytes() == original


@pytest.mark.parametrize("new", [
    "set -e\n# clean\ndeploy --prod\n",
    "",
    "set -e\nrm -rf build\ndeploy --prod\nextra\n",
])
def test_edit_is_safe_rejects_deleted_code_emptied_files_and_additions(new):
    old = "set -e\nrm -rf build\n# clean\ndeploy --prod\n"

    assert not edit_is_safe("a.sh", old, new, {".sh": "hash"})


def test_edit_is_safe_rejects_a_truncated_code_line_and_accepts_block_comment_removal():
    styles = {".ts": "slash"}

    assert not edit_is_safe("a.ts", "foo(a, b); // x\n", "foo(a,\n", styles)
    assert edit_is_safe("a.ts", "/**\n * Inc.\n */\nrun(); // go\n", "run();\n", styles)
    assert not edit_is_safe("a.c", "int a;\n*p = 1;\n", "int a;\n", {".c": "slash"})


def test_review_deletes_a_file_the_reviewer_created(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    fake_claude(tmp_path, monkeypatch, "create")

    assert "reverted reviewer edits to made.py" in review(tmp_path)
    assert not (tmp_path / "made.py").exists()


def test_survey_reports_styles_directories_generated_files_and_config_errors(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for rel, text in {
        "src/a.py": "x = 1\n",
        "src/b.py": "x = 1\n",
        "tests/t.py": "x = 1\n",
        "web/c.vue": "<template/>\n",
        "web/d.ts": "const a = 1;\n",
        "api/pb.go": "// Code generated by x. DO NOT EDIT.\npackage a\n",
        "node_modules/m/i.js": "a();\n",
    }.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)

    report = survey(str(tmp_path))

    assert "  .py 3 python" in report
    assert "  .vue 1 unsupported" in report
    assert "  src 2" in report and "  tests 1" in report and "  web 1" in report
    assert "node_modules" not in report.split("per top-level directory:")[1].split("generated")[0]
    assert "generated files skipped: 1" in report
    assert "  tests 1" in report.split("conventional directories present")[1]

    (tmp_path / ".commentrc").write_text(json.dumps({"extensions": {".vue": "slash"}, "exclude": ["tests/**"]}))
    configured = survey(str(tmp_path))

    assert "  .vue 1 slash" in configured
    assert "  tests" not in configured.split("conventional")[0].split("per top-level directory:")[1]
    (tmp_path / ".commentrc").write_text(json.dumps({"include": "src"}))
    with pytest.raises(ValueError):
        survey(str(tmp_path))


def test_failing_reviewer_that_already_edited_files_is_rolled_back(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    original = (tmp_path / "a.py").read_text()
    fake_claude(tmp_path, monkeypatch, "mangle_fail")

    message = review(tmp_path)

    assert "reviewer (haiku) failed: quota" in message
    assert "reverted unsafe edit to a.py" in message and "reverted reviewer edits to other.py" in message
    assert (tmp_path / "a.py").read_text() == original
    assert (tmp_path / "other.py").read_text() == "y = 1\n"
    assert review(tmp_path) is not None


def test_reviewer_may_edit_only_the_flagged_files(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: calls.append(args))
    (tmp_path / "sub").mkdir()

    run_reviewer(str(tmp_path), "haiku", "p", 5, ["a.py", "sub/with space.py"])

    args = calls[0]
    root = os.path.realpath(tmp_path)
    allowed = args[args.index("--allowedTools") + 1:args.index("--strict-mcp-config")]
    assert allowed == ["Read", f"Edit(/{root}/a.py)", f"Edit(/{root}/sub/with space.py)"]
    assert args[args.index("--permission-mode") + 1] == "dontAsk"
    assert args[args.index("--setting-sources") + 1] == ""


def test_files_with_pattern_characters_in_the_path_are_not_reviewed(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    (tmp_path / "b[1].py").write_text("x = 1  # one\n")
    fake_claude(tmp_path, monkeypatch, "trim")

    assert "in 1 files" in review(tmp_path, ("a.py", "b[1].py"))
    assert "# one" in (tmp_path / "b[1].py").read_text()


@pytest.mark.parametrize("old,new", [
    ('echo "build #1"\n', 'echo "build\n'),
    ("echo 'a #b'\n", "echo 'a\n"),
    ("echo ${#arr}\n", "echo ${\n"),
    ("#!/bin/bash\nls\n", "ls\n"),
])
def test_hash_edits_that_cut_strings_or_drop_the_shebang_are_unsafe(old, new):
    assert not edit_is_safe("a.sh", old, new, {".sh": "hash"})


@pytest.mark.parametrize("old,new", [
    ("#include <a.h>\nint a;\n", "int a;\n"),
    ('const u = "x //y";\n', 'const u = "x\n'),
])
def test_slash_edits_that_drop_a_directive_line_or_cut_a_string_are_unsafe(old, new):
    assert not edit_is_safe("a.c", old, new, {".c": "slash"})


def test_trailing_comment_removal_is_safe_in_each_style():
    assert edit_is_safe("a.sh", "echo a  # why\n", "echo a\n", {".sh": "hash"})
    assert edit_is_safe("a.c", "int a; // why\n#include <b.h>\n", "int a;\n#include <b.h>\n", {".c": "slash"})


def test_a_deeply_nested_python_file_does_not_crash_the_parsers():
    source = "x = " + "+".join(["1"] * 20000) + "\n"

    assert python_docstrings(source) == []
    assert python_shape(source) is None
    assert edit_is_safe("a.py", source, source, {".py": "python"})


def test_bare_directory_names_in_include_and_exclude_cover_the_subtree(tmp_path):
    scope = scope_in(tmp_path, {"include": ["src", "lib/"], "exclude": ["src/tests"]})

    assert scope.allows("src/a.py") and scope.allows("lib/x/b.py")
    assert not scope.allows("src/tests/t.py")
    assert not scope.allows("docs/c.py")


def test_hook_input_tolerates_blank_and_invalid_stdin(monkeypatch):
    import io

    for text, expected in [("\n", {}), ("nope", {}), ("[1]", {}), ('{"cwd": "/x"}', {"cwd": "/x"})]:
        monkeypatch.setattr("sys.stdin", io.StringIO(text))
        assert read_hook_input() == expected


def test_reviewer_model_falls_back_when_the_worker_name_contains_every_candidate(tmp_path, monkeypatch):
    monkeypatch.delenv("NO_COMMENT_MODEL", raising=False)

    assert reviewer_model(transcript(tmp_path, "haiku-sonnet-blend")) == "haiku"


def test_targets_accept_files_whose_names_start_with_two_dots(tmp_path, tmp_path_factory):
    base = tmp_path.resolve()
    subprocess.run(["git", "init", "-q", str(base)], check=True)
    (base / "..odd.py").write_text("x = 1\n")
    log = tmp_path_factory.mktemp("transcript") / "t.jsonl"
    log.write_text(edit_event("Edit", file_path=str(base / "..odd.py")))

    assert targets(str(base), str(log)) == {str(base): {"..odd.py"}}


def test_a_second_rejection_of_the_same_file_keeps_both_copies(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    fake_claude(tmp_path, monkeypatch, "mangle")

    review(tmp_path)
    (tmp_path / "a.py").write_text("def f(x):\n    # note two\n    return x\n")
    review(tmp_path)

    assert len(list((tmp_path / ".git" / "no-comment-rejected").glob("a.py.*"))) == 2


def test_bare_names_match_at_any_depth_and_slashed_paths_stay_anchored(tmp_path):
    scope = scope_in(tmp_path, {"exclude": ["tests", "src/gen", "*.snap.py"]})

    assert not scope.allows("pkg/a/tests/t.py") and not scope.allows("tests/t.py")
    assert not scope.allows("src/gen/a.py") and scope.allows("pkg/src/gen/a.py")
    assert not scope.allows("deep/x.snap.py")


def test_include_names_are_anchored_at_the_repo_root_unless_written_as_globs(tmp_path):
    scope = scope_in(tmp_path, {"include": ["src", "**/lib"]})

    assert scope.allows("src/a.py") and not scope.allows("docs/src/a.py")
    assert scope.allows("pkg/lib/b.py")


@pytest.mark.parametrize("old,new", [
    ("/* c */ foo();\n", "\n"),
    ("const x = a\n  * b;\n", "const x = a\n"),
    ("/* open\n*/ foo();\n", "\n"),
])
def test_slash_edits_that_delete_code_beside_or_after_a_block_marker_are_unsafe(old, new):
    assert not edit_is_safe("a.c", old, new, {".c": "slash"})


def test_a_trailing_comment_after_an_in_string_marker_is_a_safe_removal():
    assert edit_is_safe("a.sh", 'echo "Issue #5"  # report\n', 'echo "Issue #5"\n', {".sh": "hash"})
    assert edit_is_safe("a.ts", 'const u = "a // b"; // c\n', 'const u = "a // b";\n', {".ts": "slash"})
    assert not edit_is_safe("a.sh", 'echo "Issue #5"\n', 'echo "Issue\n', {".sh": "hash"})


def test_survey_counts_files_the_hook_would_skip_for_path_characters(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "app" / "[id]").mkdir(parents=True)
    (tmp_path / "app" / "[id]" / "page.ts").write_text("a();\n")
    (tmp_path / "app" / "ok.ts").write_text("a();\n")

    report = survey(str(tmp_path))

    assert "files skipped for special characters in the path: 1" in report
    assert "  app 1" in report


def test_a_trailing_block_comment_is_a_safe_removal_but_code_after_it_is_not():
    assert edit_is_safe("a.c", "int a; /* why */\n", "int a;\n", {".c": "slash"})
    assert edit_is_safe("a.c", "int a; /* open\n more */\n", "int a;\n", {".c": "slash"})
    assert not edit_is_safe("a.c", "int a; /* c */ b();\n", "int a;\n", {".c": "slash"})


def test_a_block_opener_inside_a_string_does_not_make_later_lines_comment_only():
    old = 'const g = glob("src/*.ts");\nimportant();\nmore();\n'

    assert not edit_is_safe("a.js", old, 'const g = glob("src/*.ts");\n', {".js": "slash"})
    assert edit_is_safe("a.js", "/*\n note\n*/\nrun();\n", "run();\n", {".js": "slash"})


def test_a_cut_inside_a_single_quoted_js_string_is_unsafe_but_rust_lifetimes_are_not_quotes():
    assert not edit_is_safe("a.js", "const s = 'a //b';\n", "const s = 'a\n", {".js": "slash"})
    assert edit_is_safe("a.js", "const s = 'a'; // why\n", "const s = 'a';\n", {".js": "slash"})
    assert edit_is_safe("a.rs", "fn f<'a>(x: &'a str) {} // why\n", "fn f<'a>(x: &'a str) {}\n", {".rs": "slash"})


def test_an_oversized_file_the_reviewer_truncates_is_neither_deleted_nor_overwritten(tmp_path, monkeypatch):
    import no_comment

    repo_with_comment(tmp_path)
    (tmp_path / "other.py").write_text("y = 1\n" * 10)
    monkeypatch.setattr(no_comment, "SNAPSHOT_LIMIT", 20)
    fake_claude(tmp_path, monkeypatch, "truncate")

    message = review(tmp_path)

    assert "other.py" not in message
    assert (tmp_path / "other.py").read_text() == "y\n"


def test_rejected_bytes_survive_when_the_reviewer_writes_invalid_utf8(tmp_path, monkeypatch):
    repo_with_comment(tmp_path)
    original = (tmp_path / "a.py").read_bytes()
    fake_claude(tmp_path, monkeypatch, "badbytes")

    message = review(tmp_path)

    assert "reverted unsafe edit to a.py" in message
    assert (tmp_path / "a.py").read_bytes() == original
    (rejected,) = (tmp_path / ".git" / "no-comment-rejected").glob("a.py.*")
    assert rejected.read_bytes() == b"\xff\xfe not utf8\n"


def test_a_marker_inside_a_string_is_not_a_comment():
    assert find_comments("a.sh", 'echo "a # b"\n') == []
    assert find_comments("a.ts", "const s = 'a // b';\n") == []


def test_rust_lifetimes_do_not_hide_a_trailing_comment():
    source = "fn f<'a>(x: &'a str) -> &'a str { x } // keep\n"

    assert find_comments("a.rs", source) == [Comment(1, "keep")]


def test_a_block_opener_inside_a_single_quoted_string_does_not_make_later_lines_comment_only():
    old = "const s = 'a /* x';\nrun();\n"

    assert not edit_is_safe("a.ts", old, "const s = 'a /* x';\n", {".ts": "slash"})


YAML_BLOCK = "run: |\n  echo hi\n  # a script line, not a yaml comment\n  echo bye\n"


@pytest.mark.parametrize("opener, body", [
    ("run: |", "  "), ("run: >-", "  "), ("run: |2", "  "), ("- |", "  "), ("- run: |+", "    "), ("a:\n  - |", "    "),
])
def test_a_hash_line_inside_a_yaml_block_scalar_is_not_a_comment(opener, body):
    source = f"{opener}\n{body}echo hi\n{body}# script line\n{body}echo bye\n"

    assert find_comments("a.yml", source) == []
    assert not edit_is_safe("a.yml", source, source.replace(f"{body}# script line\n", ""), {".yml": "hash"})


@pytest.mark.parametrize("source", [
    "cat <<EOF\n# literal text\nEOF\n",
    "cat <<-EOF\n# literal text\n\tEOF\n",
    "cat <<~EOF\n  # literal text\n  EOF\n",
    'cat <<"EOF"\n# literal text\nEOF\n',
    "cat <<'EOF'\n# literal text\nEOF\n",
])
def test_a_hash_line_inside_a_heredoc_is_not_a_comment(source):
    deleted = "".join(line for line in source.splitlines(True) if "# literal text" not in line)

    assert find_comments("a.sh", source) == []
    assert not edit_is_safe("a.sh", source, deleted, {".sh": "hash"})


def test_real_comments_around_a_literal_block_are_still_found_and_deletable():
    styles = {".yml": "hash", ".sh": "hash"}
    yaml = "# before\nrun: |\n  # literal\nnext: 1\n# after\n"
    shell = "# before\ncat <<EOF\n# literal\nEOF\n# after\n"

    for path, source in (("a.yml", yaml), ("a.sh", shell)):
        assert find_comments(path, source) == [Comment(1, "before"), Comment(5, "after")]
        stripped = "".join(line for line in source.splitlines(True) if line not in ("# before\n", "# after\n"))
        assert edit_is_safe(path, source, stripped, styles)


def test_a_comment_after_the_block_indicator_is_still_a_comment():
    assert find_comments("a.yml", "run: |  # note\n  echo hi\n") == [Comment(1, "note")]


def test_an_indented_hash_line_after_a_block_scalar_ends_is_a_comment_again():
    source = "run: |\n  echo hi\nnext: 1\n  # indented comment\n"

    assert find_comments("a.yml", source) == [Comment(4, "indented comment")]


def test_a_heredoc_opener_without_a_terminator_protects_nothing():
    source = "echo $((1 << x))\n# real comment\n"

    assert find_comments("a.sh", source) == [Comment(2, "real comment")]


def test_blank_lines_after_a_block_scalar_are_not_protected():
    old = "run: |\n  echo hi\n\n# c\nnext: 1\n"

    assert edit_is_safe("a.yml", old, "run: |\n  echo hi\nnext: 1\n", {".yml": "hash"})


def test_a_blank_line_inside_a_block_scalar_is_protected():
    old = "run: |\n  echo hi\n\n  echo bye\n"

    assert not edit_is_safe("a.yml", old, "run: |\n  echo hi\n  echo bye\n", {".yml": "hash"})


def test_an_apostrophe_in_jsx_text_does_not_hide_a_trailing_comment():
    source = "const a = <p>don't</p>; // note\n"

    assert find_comments("a.tsx", source) == [Comment(1, "note")]
    assert edit_is_safe("a.tsx", source, "const a = <p>don't</p>;\n", {".tsx": "slash"})


def test_code_after_an_unterminated_apostrophe_is_still_protected():
    old = "const a = <p>don't</p>; // note\nrun();\n"
    styles = {".tsx": "slash"}

    assert not edit_is_safe("a.tsx", old, "const a = <p>don't</p>; // note\n", styles)
    assert not edit_is_safe("a.tsx", old, "const a = <p>don\nrun();\n", styles)
    assert not edit_is_safe("a.tsx", "isn't ready();\n", "", styles)


def test_a_comment_marker_inside_a_closed_single_quoted_string_is_not_a_comment():
    assert find_comments("a.ts", "const s = 'a // b'; // real\n") == [Comment(1, "real")]
    assert find_comments("a.ts", "const s = 'a // b';\n") == []
