# Tools

Small things that sit beside the setup rather than inside a skill. Each script uses the standard
library only, has its paths in a configuration block at the top, and tests itself with
`--self-test`.

| Tool | What it is |
|---|---|
| [archive_notes.py](archive_notes.py) | Moves the agent's dated notes into `Archive/YYYY-MM/` once they have been quiet for thirty days, and logs each move (guide 08). `--dry-run` lists what would move; run it weekly from a scheduled task, as the outside twin of a startup script in the notes app. |
| [output_check.py](../hooks/output_check.py) | Checks a finished note for dashes inside sentences, abbreviations used before their long form, bare issue numbers and frontmatter that does not parse. It lives beside the guard; the skills that end in a note run it under their Checks. |
| [setup_refs.py](../hooks/setup_refs.py) | Lists every line of the setup that names a thing (`--who`), and the references that point at nothing: a path that does not exist, a step beyond a skill's last, a skill without its index row. It lives beside the guard; `learn` runs it under its Checks, and a git hook can run it on every commit. |
| [measure_context.md](measure_context.md) | How to read `/context`, and what to cut. |
| [literature-stack.md](literature-stack.md) | The literature tools of guide 07, in the order to install them, with a test for each. |

The weekly measurement of how the workflow runs (`workflow_health.py`) belongs to its skill and
lives in `kit/skills/workflow-health/scripts/`.
