VS Code and Coding-Agent Onboarding
===================================

Purpose
-------

This guide helps a new FEMIC contributor set up a practical local VS Code
workflow and collaborate effectively with a local coding agent working in the
same checkout.

It is written for real project work, not as a generic AI-tools overview.
The goal is to help a newcomer become productive without losing track of the
repo/runtime rules that matter in FEMIC.

Use This Guide For
------------------

Use this guide when you want to:

- open FEMIC in VS Code and do day-to-day development from a local checkout;
- work with a local coding agent that can read and edit files in the repo;
- understand what work can be delegated safely and what still needs active
  human review;
- onboard a new student or collaborator who is comfortable with code but has
  not yet learned the FEMIC workflow.

This guide assumes you are working from a local FEMIC checkout, not from a
read-only browser view of the repo.

Minimum Local Setup
-------------------

Before thinking about prompts or agent workflow, get the local environment into
 a known-good state.

1. Install the normal local tools:

   - Git
   - Python
   - VS Code
   - the OS-level runtime pieces FEMIC expects for your platform
     (for example `git-annex`, Java, and any geospatial/runtime dependencies
     needed for your specific workflow)

2. Open the FEMIC repo root in VS Code.

3. In the integrated terminal, follow the canonical bootstrap in
   ``docs/guides/developer-environment-bootstrap.rst``.

4. Confirm the repo can pass the minimum shell checks from the active
   ``.venv`` before starting model work:

   - ``python -m femic --help``
   - ``ruff --version``
   - ``mypy --version``
   - ``pytest --version``
   - ``pre-commit --version``
   - ``sphinx-build --version``
   - ``gh --version``
   - ``gh auth status``

5. Initialize submodules and materialize any required annex-backed data before
   assuming a path under ``external/`` is usable.

Windows VS Code/Codex Recovery: Broken Local File Links
-------------------------------------------------------

One recurring Windows 11-specific productivity failure in the local
VS Code/Codex workflow is that assistant-rendered local file links can regress
and start opening in the browser instead of the editor.

When that happens, the coding agent can still edit files, but ordinary
file-navigation from the chat surface becomes unreliable and wastes time
immediately.

If you hit that seam in a Windows VS Code or Cursor environment, use the
lab-maintained patch repo before doing deeper FEMIC work:

- ``https://github.com/UBC-FRESH/codex-local-file-link-patch``

That repo includes:

- a PowerShell patcher that auto-detects the newest local
  ``openai.chatgpt-*`` extension install under VS Code or Cursor;
- backup/restore behavior for the modified bundle files; and
- root-level ``AGENTS.md`` notes intended for a Codex agent that is trying to
  bootstrap-fix its own broken IDE environment safely.

Recommended recovery sequence:

1. Clone or open ``codex-local-file-link-patch``.
2. Dry-run the patcher first:

   .. code-block:: powershell

      powershell -ExecutionPolicy Bypass -File .\apply_codex_local_file_link_patch.ps1 -WhatIf

3. Run the real patch:

   .. code-block:: powershell

      powershell -ExecutionPolicy Bypass -File .\apply_codex_local_file_link_patch.ps1

4. In VS Code, run:

   .. code-block:: text

      Developer: Reload Window

Treat this as a Windows VS Code/Codex recovery step, not a normal FEMIC
runtime dependency. Linux contributors working in other IDE surfaces should not
need it.

VS Code Workspace Basics
------------------------

For FEMIC work, a good baseline VS Code layout usually includes:

- one repo window rooted at the active FEMIC checkout;
- an integrated terminal already activated into ``.venv``;
- the Source Control pane visible so you can notice unintended file churn;
- the Problems pane visible so linter/type-check output is easy to review;
- the Output / terminal area available for long-running FEMIC commands;
- the open editors focused on:
  - the active implementation file,
  - `ROADMAP.md`,
  - `CHANGE_LOG.md`,
  - and any relevant instance config/docs files.

If the Windows local-file-link regression is active, keep the patch repo open
in a second window or clone so the agent can rediscover its own bootstrap
instructions quickly:

- ``https://github.com/UBC-FRESH/codex-local-file-link-patch``

Treat this repo-root VS Code window as the canonical place to launch commands.
Do not let stale editor tasks or copied absolute paths pull you into a
different checkout by accident.

What the Coding Agent Is Good At
--------------------------------

A local coding agent is especially useful for:

- repo-wide search and trace work;
- drafting or extending a plan in `ROADMAP.md`;
- editing multiple related files consistently;
- rebuilding docs/tests and summarizing failures;
- repetitive config/path migrations;
- producing first-pass docs, tests, and validation notes;
- doing issue / PR / changelog hygiene once the scope is clear.

In FEMIC, this can save a lot of time on wide but structured edits.

What Still Needs Human Supervision
----------------------------------

Even with a strong coding agent, the human developer still needs to supervise
things that are easy to get subtly wrong in this repo:

- whether the chosen governing GitHub issue is really the right tracker;
- whether the roadmap phase/task structure matches the actual work;
- whether generated artifacts were rebuilt from the right canonical inputs;
- whether Matrix Builder, Patchworks, BatchTIPSY, annex-backed data, or other
  external tools were actually operating on current inputs;
- whether a model behavior explanation is plausible in domain terms, not just
  syntactically tidy;
- whether a doc change is actually helpful for a student or operator;
- whether the agent accidentally treated historical/audit-trail text as a live
  source of truth.

The agent can do a lot of the mechanical work. It should not be trusted to
replace domain judgment or release judgment.

Prompting Style That Works Well
-------------------------------

In this repo, prompts work best when they are:

- concrete about the target outcome;
- explicit about which repo or submodule is in scope;
- clear about whether you want planning first or direct implementation;
- specific about validation expectations;
- honest about uncertainty or suspected bugs.

Good prompt patterns:

- "Plan the implementation before editing anything."
- "Use Issue `#NN` and update the roadmap first."
- "Do the change, rebuild the relevant XML/tracks, and tell me exactly what was
  validated."
- "Assume the current output is wrong; prove or disprove that before changing
  code."
- "Do not merge or close until I have spot-checked the behavior."

Less effective prompt patterns:

- "Fix everything."
- "Make it better."
- "Do whatever seems right."

Those vague prompts make it easier for the agent to drift, overreach, or close
something prematurely.

Scoping Rules for Large Tasks
-----------------------------

For larger FEMIC tasks, ask for work in slices.

A good slice usually has:

- one governing issue;
- one roadmap phase;
- one branch;
- one clear validation story.

Examples of good slicing:

- implement the `ctfert_*` pilot first, then port to the rest of K3Z;
- fix the runtime path contract first, then land docs cleanup and closeout;
- add a new account family first, then add the student-facing docs after the
  model behavior is verified.

This reduces the chance that the agent mixes planning, implementation, and
release hygiene across too many moving parts at once.

Recommended Human Review Loop
-----------------------------

A practical review loop for FEMIC work looks like this:

1. Ask the agent to identify the governing issue and update the roadmap.
2. Let it implement one coherent slice.
3. Review:

   - the actual files changed;
   - the claimed validation commands and outputs;
   - any generated XML/tracks/accounts/docs artifacts that matter.

4. Spot-check the live behavior yourself when the task is model-facing.
5. Only after that, ask the agent to:

   - update the GitHub issue,
   - open PRs,
   - merge,
   - close the issue,
   - and return the repo to `main`.

This review loop is especially important for:

- Patchworks-facing changes;
- generated artifact refreshes;
- teaching-model assumptions;
- GitHub issue/comment cleanup, where shell quoting mistakes can corrupt text
  just as badly as a code bug can corrupt a config file.

GitHub Issue Workflow Hygiene
-----------------------------

When the task includes GitHub issue work, use a disciplined shell workflow.

Recommended baseline:

1. Audit before mutating anything:

   - ``gh issue list --state open``
   - ``gh issue list --state closed``
   - ``gh issue view <n> --json ...``

2. Use ``gh issue edit`` for issue titles, bodies, and labels.

3. Use ``gh api graphql`` when you need to edit maintainer-authored comments or
   another metadata surface that the higher-level CLI does not expose cleanly.

4. When sending Markdown bodies from PowerShell, prefer body files or quoted
   here-strings instead of inline escaped strings. FEMIC has already seen issue
   comments mangled by accidental control-character injection from bad shell
   escaping.

5. Before closing an issue, add one final closeout comment that states:

   - what landed;
   - which repo paths/docs matter most;
   - what validation passed; and
   - why any remaining caveats do not block closure.

One Windows-specific improvement now helps with local agent-driven rebuilds:

- when the shipped Windows Patchworks runtime configs have
  ``matrix_builder.auto_close_window_on_success: true``, FEMIC will supervise
  the noninteractive Matrix Builder launch, wait for fresh output activity to
  stabilize, and then close the spawned Matrix Builder window automatically;
- on this host, that supervised cleanup also tears down the matching
  Patchworks launcher ``cmd.exe`` shell tree, so the coding agent does not
  have to wait for a leftover console window after the Java process is done;
- this is meant to remove the routine "human must notice and close the window"
  interruption from the local coding-agent workflow;
- it does **not** replace normal validation: you should still review the
  manifest and logs if the runtime behavior seems suspicious.
- docs intended for students or external users.

FEMIC-Specific Things to Watch For
----------------------------------

This repo has a few recurring failure modes that a human should actively watch
for when steering a coding agent:

- stale generated artifacts: code/config changed, but XML/tracks/accounts/docs
  were not rebuilt;
- stale canonical-vs-historical confusion: an old path in `ROADMAP.md` or
  `CHANGE_LOG.md` gets mistaken for the live runtime contract;
- submodule drift: the parent repo and the instance submodule no longer point
  at the same intended milestone state;
- external runtime seams: Matrix Builder, Patchworks, BatchTIPSY, `git-annex`,
  or DataLad are the actual blocker, not Python code;
- track overlay confusion: a user-edited Patchworks ``tracks/*/groups.csv``
  surface gets mistaken for a compiled artifact and the agent starts
  rebuilding or adding BeanShell logic even though the real task is to respect
  the post-build overlay contract;
- issue hygiene drift: the branch is real, but the GitHub
  issue/roadmap/changelog still describe an older scope.

If you suspect one of these, say so directly in the prompt. That kind of
domain hint is often more valuable than a long generic instruction.

Current Proprietary-Tool Seams
------------------------------

The current proprietary-tool boundaries are now specific enough that agents
should be pointed at the right doc surface instead of rediscovering them:

- BTC unattended `/TSR`:
  the only known-valid unattended FEMIC seam is the live user-overlay
  ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt`` path, and copied-install
  or stock-report-only probes are not equivalent validation.
- BTC `/No_GUI`:
  documented dead end; not a supported FEMIC runtime seam.
- FAN$IER:
  unattended extraction is real, but it is a Windows GUI-automation seam, not
  a native CLI contract. Start with
  ``docs/guides/btc-fansier-runtime-and-extraction.rst`` and
  ``docs/reference/api/femic-fansier-runtime.rst``.
- Patchworks:
  prefer the shipped registry/operator surfaces over raw `.pin` spelunking
  when using bundled K3Z examples. Start with
  ``docs/guides/patchworks-variant-and-scenario-management.rst`` and
  ``docs/reference/api/femic-patchworks-variants.rst``.

Patchworks Overlay Reminder
---------------------------

One recurring FEMIC/K3Z gotcha is that not every file under a Patchworks
``tracks/`` directory is a "rebuild me" artifact.

- The compiled tables such as ``curves.csv`` and ``products.csv`` come from
  export + Matrix Builder.
- ``groups.csv`` may instead be a user-defined post-build overlay.

If a human asks for a new grouping assignment on an already-built track
surface, the safe first assumption is:

- do **not** rebuild yet;
- do **not** invent new BeanShell ``calculateGroups("...")`` expressions;
- first verify the documented runtime contract for how that instance consumes
  ``groups.csv``.

Suggested First Session for a New Contributor
---------------------------------------------

If you are onboarding a new student or developer, a good first session is:

1. Open the FEMIC repo in VS Code.
2. Follow ``docs/guides/developer-environment-bootstrap.rst``.
3. Read:

   - ``AGENTS.md``
   - ``docs/reference/contracts/index.rst``
   - ``docs/reference/contracts/patchworks-model-semantics.rst``
   - ``docs/guides/deployment-instances.rst``
   - ``docs/guides/case-onboarding.rst``

4. Ask the coding agent for a short summary of:

   - repo structure,
   - bundled instance submodules,
   - and the current top roadmap phase.

5. Do one small supervised task first:

   - docs-only cleanup,
   - a targeted test fix,
   - or a narrow config-path update.

6. Only after that, move on to model-facing rebuild work.

This sequence helps a newcomer learn the repo contracts before they have to
debug generated artifacts or external runtime tools.

Patchworks model rule of thumb
------------------------------

When a new coding agent or student touches a Patchworks instance, require them
to state these rules back in repo terms before they start rewriting model
logic:

- ``managed`` / ``unmanaged`` means treatment eligibility;
- ``natural`` / ``treated`` means curve provenance;
- retention can move area between managed and unmanaged without changing
  origin; and
- successful Matrix Builder output is not enough if rebuilt runtime signal
  disagrees with published source-share inputs.

If the agent cannot restate those rules cleanly, stop and point them at
``docs/reference/contracts/patchworks-model-semantics.rst`` before they touch
instance runtime semantics.

Looking Ahead
-------------

This guide is intentionally FEMIC-specific.

Later, parts of it could be generalized into a more reusable onboarding
template for similar FRESH lab projects, especially:

- local scientific-computing repo bootstrap;
- coding-agent supervision patterns;
- planning / validation / issue-hygiene workflow;
- handling generated artifacts and external modeling tools safely.

For now, keep the guidance anchored to this repo and its actual runtime
contracts.

Related Guides
--------------

- ``docs/guides/developer-environment-bootstrap.rst``
- ``docs/guides/deployment-instances.rst``
- ``docs/guides/case-onboarding.rst``
- ``docs/reference/contracts/index.rst``
- ``https://github.com/UBC-FRESH/codex-local-file-link-patch``
