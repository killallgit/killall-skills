#!/usr/bin/env python3
"""Render an architectural-review findings JSON file as a self-contained HTML report.

Usage: render_report.py FINDINGS.json [--out PATH]
Prints the report path, then the bd commands for the suggested beads.
The findings shape is in references/report.md.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

STRENGTHS = {"strong": "Strong", "worth-exploring": "Worth exploring", "speculative": "Speculative"}
CANDIDATE_KEYS = ("id", "title", "strength", "files", "problem", "solution", "benefits", "before", "after", "bead")


class InvalidFindings(ValueError):
    pass


@dataclass(frozen=True)
class Bead:
    title: str
    type: str
    priority: int
    description: str
    parent: str | None = None


def validate(findings: dict) -> None:
    ids = set()
    for candidate in findings["candidates"]:
        missing = [key for key in CANDIDATE_KEYS if key not in candidate]
        if missing:
            raise InvalidFindings(f"candidate {candidate.get('id')} is missing {missing}")
        if candidate["strength"] not in STRENGTHS:
            raise InvalidFindings(f"candidate {candidate['id']} strength must be one of {list(STRENGTHS)}")
        ids.add(candidate["id"])
    if findings["top"] not in ids:
        raise InvalidFindings(f"top {findings['top']} is not a candidate id")


def bead_plan(findings: dict, date: str) -> tuple[Bead, ...]:
    epic = Bead(f"Architecture review {date}: {findings['scope']}", "epic", 2, findings["top_reason"])
    children = (
        Bead(c["bead"]["title"], c["bead"]["type"], c["bead"]["priority"], c["solution"], parent="epic")
        for c in findings["candidates"]
    )
    return (epic, *children)


def bead_command(bead: Bead) -> str:
    flags = f"-t {bead.type} -p {bead.priority} --title {shlex.quote(bead.title)} -d {shlex.quote(bead.description)}"
    if bead.parent is None:
        return f"EPIC=$(bd create --silent {flags})"
    return f'bd create --parent "$EPIC" {flags}'


def paragraph(label: str, text: str) -> str:
    return f"<h4>{label}</h4><p>{escape(text)}</p>"


def candidate_card(c: dict) -> str:
    files = "".join(f"<code>{escape(f)}</code> " for f in c["files"])
    rules = "".join(f"<li>{escape(r)}</li>" for r in c.get("rules", []))
    adr = f'<p class="warn">{escape(c["adr_conflict"])}</p>' if c.get("adr_conflict") else ""
    return f"""<article id="c{c['id']}">
<header><h3>{c['id']}. {escape(c['title'])}</h3><span class="badge {c['strength']}">{STRENGTHS[c['strength']]}</span></header>
<p>{files}</p>{adr}
{paragraph("Problem", c["problem"])}{paragraph("Solution", c["solution"])}{paragraph("Benefits", c["benefits"])}
{f"<h4>Rules in play</h4><ul>{rules}</ul>" if rules else ""}
<div class="diagrams"><figure><figcaption>Before</figcaption><pre class="mermaid">{escape(c['before'])}</pre></figure>
<figure><figcaption>After</figcaption><pre class="mermaid">{escape(c['after'])}</pre></figure></div>
</article>"""


def glossary_rows(terms: list[dict]) -> str:
    return "".join(
        f"<tr><td><b>{escape(t['term'])}</b></td><td>{escape(t['definition'])}</td>"
        f"<td>{escape(', '.join(t.get('avoid', [])))}</td></tr>"
        for t in terms
    )


def render(findings: dict, date: str) -> str:
    validate(findings)
    cards = "\n".join(candidate_card(c) for c in findings["candidates"])
    commands = escape("\n".join(bead_command(b) for b in bead_plan(findings, date)))
    glossary = findings.get("glossary", [])
    glossary_section = (
        f"<section><h2>Proposed glossary terms</h2><table><tr><th>Term</th><th>Definition</th><th>Avoid</th></tr>"
        f"{glossary_rows(glossary)}</table></section>"
        if glossary else ""
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Architecture review</title>
<style>{CSS}</style></head><body><main>
<h1>Architecture review: {escape(findings['repo'])}</h1>
<p class="muted">{escape(date)} · scope: {escape(findings['scope'])}</p>
<section class="top"><h2>Top recommendation</h2><p><a href="#c{findings['top']}">#{findings['top']}</a> {escape(findings['top_reason'])}</p></section>
<section><h2>Candidates</h2>{cards}</section>
{glossary_section}
<section><h2>Suggested beads</h2><p>One epic for this review, one child per candidate. Prune before running.</p><pre>{commands}</pre></section>
</main><script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";
mermaid.initialize({{startOnLoad: true, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default"}});
</script></body></html>"""


CSS = """
:root{--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--card:#fff;--line:#e7e5e4;--strong:#15803d;--explore:#b45309;--spec:#6b7280;--warn:#fef3c7}
@media (prefers-color-scheme:dark){:root{--bg:#0c0a09;--fg:#e7e5e4;--muted:#a8a29e;--card:#1c1917;--line:#292524;--warn:#451a03}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px}
article,.top{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
article header{display:flex;justify-content:space-between;align-items:center;gap:12px}
h3{margin:0}h4{margin:12px 0 4px}.muted{color:var(--muted)}
.badge{border-radius:99px;padding:2px 10px;color:#fff;font-size:12px;white-space:nowrap}
.strong{background:var(--strong)}.worth-exploring{background:var(--explore)}.speculative{background:var(--spec)}
.warn{background:var(--warn);padding:8px;border-radius:6px}
.diagrams{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
figure{margin:0;border:1px solid var(--line);border-radius:8px;padding:8px;overflow-x:auto}
pre{overflow-x:auto}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--line);padding:6px;text-align:left}
"""


def default_out() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(os.environ.get("TMPDIR") or tempfile.gettempdir()) / f"architectural-review-{stamp}.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("findings", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    findings = json.loads(args.findings.read_text())
    date = datetime.now().strftime("%Y-%m-%d")
    out = args.out or default_out()
    out.write_text(render(findings, date))
    print(out)
    print("\n".join(bead_command(bead) for bead in bead_plan(findings, date)))


if __name__ == "__main__":
    main()
