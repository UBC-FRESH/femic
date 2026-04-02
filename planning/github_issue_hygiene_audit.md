# GitHub Issue Hygiene Audit Notes

Purpose
-------

This note records the concrete issue-hygiene rules and failure modes discovered
during the FEMIC `#76` tracker cleanup sweep.

Audit Categories
----------------

Every issue reviewed in the sweep fit one or more of these buckets:

- `No action needed`
- `Text cleanup`
- `Metadata cleanup`
- `Status reconciliation`
- `Follow-on design candidate`

Use these categories for future tracker audits so the sweep stays reproducible
instead of ad hoc.

Most Important Failure Mode Found
---------------------------------

The most common maintainer-authored formatting defect was not "bad writing."
It was **shell-induced text corruption**:

- PowerShell + `gh` issue/comment updates can accidentally inject control
  characters when Markdown bodies are assembled with the wrong escaping style.
- In practice this produced broken issue text such as:
  - `\femic`
  - `\ruff`
  - `\tracks`
  - `\flow`
- These were not GitHub rendering bugs. They were command-construction bugs.

Preferred Command Patterns
--------------------------

For future FEMIC issue work:

1. Audit first with non-mutating commands:

   - `gh issue list --state open`
   - `gh issue list --state closed`
   - `gh issue view <n> --json ...`

2. Prefer `gh issue edit` for:

   - title edits
   - body rewrites
   - label changes

3. Prefer `gh api graphql` for:

   - maintainer-authored comment edits
   - GitHub metadata surfaces that the higher-level CLI does not expose well

4. When sending Markdown from PowerShell:

   - prefer body files or quoted here-strings
   - avoid inline escaped strings that can introduce control characters

Issue Metadata Policy
---------------------

FEMIC uses GitHub's built-in issue `Type` as the canonical work-kind field:

- `Bug`
- `Feature`
- `Task`

Labels should stay orthogonal to Type, for example:

- `documentation`
- `windows`
- `patchworks`
- `k3z`
- `data`
- `tsa29`

Do not duplicate Type with labels like `bug`, `feature`, or `task`.

What This Sweep Did
-------------------

The `#76` sweep cleaned up:

- issue bodies with broken formatting or weak structure
- maintainer-authored comments with control-character corruption
- missing or weak orthogonal labels on recent issues
- stale issue state, including closing `#49` after confirming the cited work
  had truly landed on current `main`

Follow-On Decision
------------------

The proposed `fresh-gh` / helper-wrapper idea stays **design-only** for now.

Current recommendation:

- repo-side guidance plus documented `gh`/GraphQL command patterns are enough
  for current FEMIC needs
- if the same command-construction failures recur after the docs/process update,
  open a follow-on issue for either:
  - a repo-local helper wrapper, or
  - an external `fresh-gh` prototype package
