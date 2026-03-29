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

[feature] Do a full scan of FEMIC code and docs, to replace all hard-coded references to "TSA" as a forest management unit prefix with the more generic "FMU". TSA references "Timber Supply Area" in British Columbia public forest management tenure jargon. But even just in BC there are other management unit designations (tree farm licences, community forests, first-nations woodlot licenses, etc.), and the intent is for FEMIC to be eventually usable (and ASAP deployed) for Canadian national-scale modelling projects, and eventually (if there is demand and interest) to be deployed in other-than-BC Canadian provincial- and regional-scale analyses (in both research, teaching, and professional contexts), and eventually to non-Canada contexts (again, if there is interest and demand---I am not planning on doing the "hard sell" on anyone).

[feature] Implement an optional "DataLad wrapper mode" that enables tracking of all FEMIC filesystem changes within a templated and guardrailed DataLad workflow, wherein the full lifecycle of data artifacts is traceable and version-controlled---from download and local archiving of raw VRI and other inputs through ready-to-run forest estate modelling input datasets, through to forest estate model run-scenario scripts and forest estate model scenario output datasets, through to post-hoc forest estate scenario output analysis and reporting. Every data transformation along the way could ALSO be datalad-tracked (using the `datalad run` data-transformation-process-tracking functions built into datalad), such that the ENTIRE LIFECYCLE of a forest estate modelling workflow, from raw source data through to final analysis reporting is FULLY REPRODUCIBLE (and version controlled). Datalad works great, but is finnicky AF... however if we can find safe, proven-valid datalad interaction patterns that we burn into FEMIC in a way that can be reliably invoked by human or coding-agent users, then we can basically define a NEW FRONTIER IN FOREST RESOURCE ANALYSIS. Seriously. We HAVE to at least try to get there.

[feature] Extend FEMIC to be able to "send FEM run-ws3-scenario jobs" to remote worker nodes in a distributed linux cluster. I suppose that would involve involve defining and implementing the notion of "client mode" versus "server mode" in FEMIC, and possibly allowing FEMIC to be installed and run as a linux system service (as opposed to an on-demand bash CLI command or via ad hoc calls to the public Python API).

[feature] Similarly to the Patchworks-running idea: add ws3-runner module to FEMIC and make sure this is LLM-coding-agent friendly, so a coding agent can build and run and analyses full-lifecycle forest estate modelling workflows using a fully open-source ws3-based modelling pipeline (that can run in any OS environment, thereby breaking through the Windows-only barrier of our current prototypes that rely on having a valid Patchworks software installation and matching active SPS license availabing in the local environment). This would allow deploying massively parallelized analyses in multi-core high-RAM Ubuntu linux server containerized dev environments, which would be a "FEM workflow game-changer".

[feature] Add a new femic API (and CLI hook) for easily launching a given patchcworks model instance variant from a named pin (or even maybe for an unnamed default variant pin if you only name the instance).

[feature] Add missing `<succcession>` elements to ForestModel XML files compiled by FEMIC (always: default can be a null "pass through" succession event at age 1000, but every fragment in Patchworks should have a valid succession path defined so we can get down to 0 warnings 0 errors as the "gold standard" green-light post-MatrixBuilder signal, and then wire in warning-tolerance default and user override settings into FEMIC so that no warning goes ignored without getting a pass from an explicit ignore-these-specific-warnings default or user-defined policy).

[feature] Re-visit the QMD curves in the K3Z instance. The values still seem low for most of these BEC zones. Are we doing the math right when deriving these from volume per ha yield, stems per ha, SI-derived height, and stem form-factor assumptions? Also, if either VDYP or TIPSY (or both) already have literal stem diameter as a function of age curve outputs, then just grab those (obviously those will be higher quality).

[feature] Automate running batchTIPSY so my GPT coding agent running on a codex extension in my vscode dev env does not have to stop processing in the middle of the pipeline every time it does a full instance rebuild and wait for me to do the thing.

[feature] Extend BTC/TIPSY functionality to include linkage to TIPSY-CBM.exe so we can pull custom carbon modelling outputs.

[feature] Extend BTC/TIPSY functionality to include explicit simulation of various combinations of optional mid-rotation treatments (pre-commercial thinning, multiple fertilization treatment applications, commercial thinning, variable retention harvesting, final felling at different ages [and impact on logs/products/economic outputs produced at end of rotation], etc)

[feature] Modify TISPY rpt input template to request 200 years of output instead of 120.
