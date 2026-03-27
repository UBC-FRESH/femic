# Incoming Issue Ideas

Purpose

This file is a lightweight staging area for new work ideas that have been
mentioned by the developer but have not yet been fully processed into the
normal planning and GitHub workflow.

Think of this file as an intake queue, not as the canonical project plan.
Active execution still belongs in:
- `ROADMAP.md`
- `CHANGE_LOG.md`
- GitHub issues / PRs
- the appropriate working branch

How the coding agent should use this file

- When the developer asks "what next" or otherwise invites the agent to suggest
  follow-on work, the agent should check this file for unprocessed ideas.
- If an idea here is selected as the next likely piece of work, the agent
  should propose or perform the normal project-hygiene steps as appropriate:
  - turn the idea into a new phase, task, or subtask in `ROADMAP.md`
  - create or amend a GitHub issue
  - create a feature or bug branch
  - add any needed notes to `CHANGE_LOG.md`
- The agent should not treat an item in this file as automatically approved for
  implementation. It is an intake hint, not standing authorization.

When to remove or edit an idea

- Once the developer explicitly green-lights running with an idea, the coding
  agent should edit this file so the queue stays current.
- If the whole idea is being adopted, delete it from the list.
- If only part of the idea is being adopted, rewrite the entry so it reflects
  the still-unclaimed remainder.
- If an idea is superseded, merged into another tracked task, or no longer
  relevant, remove it.

How developers should add ideas

- Add new ideas to the end of the list below.
- Prefix each idea with an issue type such as `[feature]`, `[bug]`,
  `[documentation]`, or `[other]`.
- Write each entry so it can stand on its own when the agent reads it later,
  without requiring hidden chat context.
- If an idea depends on a specific file, dataset, branch, issue, or runtime
  assumption, say so directly in the entry.

Good queue hygiene

- Keep this file focused on incoming work ideas only.
- Do not use it as a scratchpad for active implementation notes once a task has
  moved into `ROADMAP.md` or GitHub.
- Prefer fewer, clearer entries over long duplicated lists of similar ideas.

---

[feature] Re-visit the QMD curves in the K3Z instance. The values still seem low for most of these BEC zones. Are we doing the math right when deriving these from volume per ha yield, stems per ha, SI-derived height, and stem form-factor assumptions? Also, if either VDYP or TIPSY (or both) already have literal stem diameter as a function of age curve outputs, then just grab those (obviously those will be higher quality).

[feature] Automate running batchTIPSY so my GPT coding agent running on a codex extension in my vscode dev env does not have to stop processing in the middle of the pipeline every time it does a full instance rebuild and wait for me to do the thing.
