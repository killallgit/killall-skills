## Agents

{{framework_note}}

Once a spec or plan exists and the work has parts that can be built independently, run the `orchestrate` skill in the main session. It cuts the work into lanes and starts the `builder`, `reviewer`, and `hall-monitor` agents; those agents run only as its lanes. A single small change stays in the main session.

Every agent that writes or checks code follows the `follow-the-rules` skill.
