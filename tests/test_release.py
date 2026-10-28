import pytest

from release import bump_version, publish_steps, sync_steps


@pytest.mark.parametrize(
    ("current", "level", "expected"),
    [
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("1.9.9", "minor", "1.10.0"),
    ],
)
def test_bump_version_increments_the_requested_part(current, level, expected):
    assert bump_version(current, level) == expected


def test_bump_version_rejects_unknown_level():
    with pytest.raises(ValueError):
        bump_version("1.2.3", "huge")


def test_bump_version_rejects_malformed_version():
    with pytest.raises(ValueError):
        bump_version("1.2", "patch")


def test_sync_steps_end_by_rebasing_main():
    assert sync_steps()[-1] == ["git", "pull", "--rebase", "origin", "main"]


def test_publish_steps_tag_after_the_release_commit():
    verbs = [step[1] for step in publish_steps("1.3.0")]

    assert verbs.index("commit") < verbs.index("tag")


def test_publish_steps_push_branch_and_tag_atomically_last():
    last = publish_steps("1.3.0")[-1]

    assert last == ["git", "push", "--atomic", "origin", "main", "v1.3.0"]
