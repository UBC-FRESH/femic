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

[feature] Tweak the THLB processing logic to simplify it. Currently the logic compiels mean (median?) THLB raster data value for pixels inside each stand in the VRI and then snaps the stand-level THLB attribute to one of `{0, 1}` based on a threshold value, and then iteratively calibrates the THLB cutoff threshold value until total landscape THLB area is approximately equal to a target value (we typically use the total THLB area reported in the latest TSR documentation published on the BC MoF web site). We can retain this logic as an optional mode that can be user-activated, but the new default could simply be to compile mean THLB value from THLB raster layer pixels that land inside every stand, and then just set (1 - THLB) proportion of each stand to "unmanaged area" in Patchworks. For the ws3 model output type target logic, we will need to come up with a similar mechanism that has similar effect. For THLB raster pixels with no data, we can just assume 0 value (i.e., no THLB, which is fine as a starting assumption until we observe actual instances where this obviously does not work---we can cross that bridge when we get to it).

[feature] Add FEMIC CLI surface to help users connect a local FEMIC package installation with their own FEMIC-compatible GitHub+DataLad "instance repository", and optionally populate their new instance repo with "forks" of built-in FEMIC model instance variants (or grab a whole instance family with all of its variants). Basically the first (and possibly only---we we'll see how she goes) client for this functionality would be me (as PI of the UBC FRESH lab) and my UBC FRESH lab team members---basically I want to create both private (for WIP projects, accessible only to FRESH team and authorized collaborators) and public (for ready-to-share projects) FEMIC model instance repositories that are storage-volume-backed by either my DRAC Arbutus cloud S3 bucket object store account or my UBC ARC Chinook cloud S3 bucket object store account (the latter has much more space and better Globus-user-based self-serve cloud-based user-access management surface). Also make sure that users who cannot or prefer not to sync their datalad data to a cloud "special remote" repo can just use the default "local" dataset data stash (a local git-annex repo or something?... I am fuzzy on recalling the implementation details)

[feature] Implement parallel Patchworks scenario runner feature on top of existing variant scenario runner functionality.

[feature] Widen Patchworks model instance variant registry idea and implementation scope (i.e., GitHub issue #60) to include *any* FEMIC-supported forest estate model. I am specifically thinking of ws3, which would be so *easy* to implement compared to Patchworks (becauase ws3 is fully open source, can be deployed easily in basically any environment, does not have licensing restrictions, is easy to run in headless-paralel mode on as many cores as available, running could even be dispatched to cluster-ws3-worker-nodes using some sort of distributed runner service architecture, etc.). Also we could try to implement some sort of Makefile-like "dirty upstream dependency tracking", such that users get a warning if trying to run a variant that has dirty (i.e., modified since variant registry executable dataset compile timestamp) state. That would help avoid running stale models, but partial or full upstream femic model component rebuild could trigger automatic registered variant dirty flag setting, etc. We could also extend the registry to track saved scenario output (timestamped) *versions* and automatic scenario-version-output-diffing so users can quickly assess if a recent upstream variant input data change or rebuild induced a regression (or produced the desired change).

[feature] Leverage new BTC and FANSIER features to compile new cost and revenue product atributes/accounts/targets (linked to application of CC treatment) in the K3Z instance. The idea is to estimate the value creation potential (VCP) of each CC harvested unit of area (i.e., sum of $/ha gross revenue from sale of logs stacked at roadside, net of planning+harvest+regeneration cost). We can assume that CT treatments are break-even, and assume $500 per ha PCT and fertilization cost (per fert application). Use the `intensive_light` variant as the deployment target. The idea in the end is to be be able to pull up on unit VCP and see what shakes out as the most profitable intensive silviculture treatment prescription sequences, and if that result is homogenous or variable across AUs. The first generation implementation of this woudl just use net revenue from sale of logs at roadside, but subsequent implementations could push the decoupling point further down the supply chain (e.g., just downstream from primary forest product production, i.e., net revenue from production and sale of pulp+paper, lumber, panels, veneer, pellets, bioenergy, etc.)

[feature] After the TSA29 standalone-instance DataLad publication bundle (`#91`, `#93`, `#94`, `#92`) lands, revisit the broader idea of an optional FEMIC-wide "DataLad wrapper mode" that enables tracking of all FEMIC filesystem changes within a templated and guardrailed DataLad workflow, wherein the full lifecycle of data artifacts is traceable and version-controlled---from download and local archiving of raw VRI and other inputs through ready-to-run forest estate modelling input datasets, through to forest estate model run-scenario scripts and forest estate model scenario output datasets, through to post-hoc forest estate scenario output analysis and reporting. Every data transformation along the way could ALSO be datalad-tracked (using the `datalad run` data-transformation-process-tracking functions built into datalad), such that the ENTIRE LIFECYCLE of a forest estate modelling workflow, from raw source data through to final analysis reporting is FULLY REPRODUCIBLE (and version controlled). Datalad works great, but is finnicky AF... however if we can find safe, proven-valid datalad interaction patterns that we burn into FEMIC in a way that can be reliably invoked by human or coding-agent users, then we can basically define a NEW FRONTIER IN FOREST RESOURCE ANALYSIS. Seriously. We HAVE to at least try to get there.

[feature] Extend FEMIC to be able to "send FEM run-ws3-scenario jobs" to remote worker nodes in a distributed linux cluster. I suppose that would involve involve defining and implementing the notion of "client mode" versus "server mode" in FEMIC, and possibly allowing FEMIC to be installed and run as a linux system service (as opposed to an on-demand bash CLI command or via ad hoc calls to the public Python API).

[feature] Similarly to the Patchworks-running idea: add ws3-runner module to FEMIC and make sure this is LLM-coding-agent friendly, so a coding agent can build and run and analyses full-lifecycle forest estate modelling workflows using a fully open-source ws3-based modelling pipeline (that can run in any OS environment, thereby breaking through the Windows-only barrier of our current prototypes that rely on having a valid Patchworks software installation and matching active SPS license availabing in the local environment). This would allow deploying massively parallelized analyses in multi-core high-RAM Ubuntu linux server containerized dev environments, which would be a "FEM workflow game-changer".

[feature] Re-visit the QMD curves in the K3Z instance. The values still seem low for most of these BEC zones. Are we doing the math right when deriving these from volume per ha yield, stems per ha, SI-derived height, and stem form-factor assumptions? Also, if either VDYP or TIPSY (or both) already have literal stem diameter as a function of age curve outputs, then just grab those (obviously those will be higher quality).

[feature] Extend BTC/TIPSY functionality to include linkage to TIPSY-CBM.exe so we can pull custom carbon modelling outputs.

[feature] Extend BTC/TIPSY functionality to include explicit simulation of various combinations of optional mid-rotation treatments (pre-commercial thinning, multiple fertilization treatment applications, commercial thinning, variable retention harvesting, final felling at different ages [and impact on logs/products/economic outputs produced at end of rotation], etc)

[feature] Modify TISPY rpt input template to request 200 years of output instead of 120.

[documentation] Keep `reference/29ts_dpkg_2024.pdf` under version control as a TSA29 refinement reference for later production-grade release work. Use it as a likely source when we revisit final-package polish, parameter provenance, and any remaining TSR-alignment questions for the TSA29 standalone instance.
