import pytest
from render_report import Bead, InvalidFindings, bead_plan, render

FINDINGS = {
    "repo": "acme",
    "scope": "recent churn in ordering",
    "top": 1,
    "top_reason": "every order change touches it",
    "candidates": [
        {
            "id": 1,
            "title": "Deepen <Order> intake",
            "strength": "strong",
            "files": ["src/ordering"],
            "problem": "p",
            "solution": "s",
            "benefits": "b",
            "before": "graph LR; A-->B",
            "after": "graph LR; A",
            "bead": {"title": "Deepen Order intake", "type": "task", "priority": 2},
        }
    ],
    "glossary": [
        {"term": "Order", "definition": "A request to buy.", "avoid": ["Purchase"]}
    ],
}


def test_render_escapes_candidate_text():
    html = render(FINDINGS, date="2026-11-08")

    assert "Deepen &lt;Order&gt; intake" in html
    assert "<Order>" not in html


def test_render_rejects_an_unknown_strength():
    bad = {
        **FINDINGS,
        "candidates": [{**FINDINGS["candidates"][0], "strength": "maybe"}],
    }

    with pytest.raises(InvalidFindings):
        render(bad, date="2026-11-08")


def test_bead_plan_is_one_epic_with_a_child_per_candidate():
    epic, *children = bead_plan(FINDINGS, date="2026-11-08")

    assert epic.type == "epic"
    assert children == [Bead("Deepen Order intake", "task", 2, "s", parent="epic")]


def candidate(**changes):
    return {**FINDINGS["candidates"][0], **changes}


@pytest.mark.parametrize(
    "findings",
    [
        {"repo": "acme"},
        {**FINDINGS, "candidates": [candidate(), candidate()]},
        {**FINDINGS, "candidates": [candidate(), candidate(id='2"><script>')]},
        {
            **FINDINGS,
            "candidates": [
                candidate(bead={"title": "t", "type": "task; touch x", "priority": 2})
            ],
        },
        {
            **FINDINGS,
            "candidates": [
                candidate(bead={"title": "t", "type": "task", "priority": None})
            ],
        },
        {
            **FINDINGS,
            "candidates": [
                candidate(bead={"title": "t", "type": "task", "priority": 7})
            ],
        },
        {**FINDINGS, "top": True},
        {**FINDINGS, "candidates": [candidate(files="src/ordering")]},
        {**FINDINGS, "glossary": [{"term": "Order"}]},
    ],
    ids=[
        "missing-top-level-key",
        "duplicate-id",
        "non-int-id",
        "unknown-bead-type",
        "null-priority",
        "priority-out-of-range",
        "bool-top",
        "files-not-a-list",
        "glossary-without-definition",
    ],
)
def test_render_rejects_malformed_findings(findings):
    with pytest.raises(InvalidFindings):
        render(findings, date="2026-11-08")


def test_render_accepts_null_optional_fields():
    findings = {**FINDINGS, "candidates": [candidate(rules=None, adr_conflict=None)]}

    render(findings, date="2026-11-08")


def test_bead_plan_collapses_multiline_text_to_one_line():
    findings = {**FINDINGS, "candidates": [candidate(solution="merge\nthem")]}

    _, child = bead_plan(findings, date="2026-11-08")

    assert child.description == "merge them"
