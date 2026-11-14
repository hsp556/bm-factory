# Vendored skills: provenance

| Skills | Source | Version | Licence |
|---|---|---|---|
| writing-plans, subagent-driven-development, executing-plans, test-driven-development, systematic-debugging, verification-before-completion, requesting-code-review, receiving-code-review, dispatching-parallel-agents, finishing-a-development-branch, using-git-worktrees | https://github.com/obra/superpowers | v7.0.2, commit 22f0b463e7a5e579904dd6211a520321035526f7 (2026-11-03) | MIT (`LICENSE-superpowers`) |

Local changes, made on 2026-11-14:
- Removed the `superpowers:` prefix from cross-skill references, because the skills are installed unprefixed at project level.
- Changed the plan location from `docs/superpowers/plans` to `docs/plans`.
- In executing-plans, replaced the pointer to the missing `using-superpowers/references/` folder with a one-line Claude Code note.

Deliberately not vendored:
- `using-superpowers`, along with its SessionStart hook ("invoke on a 1% chance"). It adds overhead to every session and conflicts with the bounded-autonomy rules in CLAUDE.md.
- `brainstorming`, which runs a local web server. The design is already settled in the SOP.
- `writing-skills` and `diagnosing-superpowers`.

Karpathy guidelines (github.com/multica-ai/andrej-karpathy-skills) are folded into the project `CLAUDE.md`, not added as a skill. CLAUDE.md is always loaded, whereas a skill loads only when triggered.

To update: re-clone superpowers, diff it against these folders, and re-apply the local changes above.
