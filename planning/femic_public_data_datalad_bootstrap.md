# FEMIC Public Data Mirror Bootstrap (P10.6b)

This note is maintainer-focused and captures the first publish flow for a
dedicated DataLad dataset repository (target: `UBC-FRESH/femic-public-data`).

Current local bootstrap state (2026-03-11):

- Local dataset repo exists at `/home/gep/projects/femic-public-data`.
- FEMIC links it as submodule at `external/femic-public-data`.
- Published dataset repo: `https://github.com/UBC-FRESH/femic-public-data`.
- Arbutus special-remote upload verified for mirrored seed artifacts (including `misc.thlb.tif` and `VEG_COMP_LYR_R1_POLY.gdb/a00000009.gdbtable`).

Known-good command sequence source:

- `tmp/datalad-kb-page.md` (FRESH lab DataLad KB copy).
- `tmp/lab-data-workflow-workshop` symlink target:
  `/home/gep/projects/lab-data-workflow-workshop`.
- Most relevant workshop references:
  - `arbutus_s3/datalad_s3_setup.md`
  - `scripts/create_github_sibling.sh`
  - `workflows/common_errors.md`

## Inputs

- `metadata/required_datasets.yaml` (authoritative source inventory)
- `metadata/datalad_mirror_seed.csv` (current include=true dataset list)
- Arbutus S3 credentials for special remote setup
- Local credential template:
  `config/credentials/arbutus_env.template.sh`

## Bootstrap Steps

1. Create the GitHub repository (`femic-public-data`) under `UBC-FRESH`.
2. Initialize local DataLad dataset:
   ```bash
   datalad create -c text2git femic-public-data
   cd femic-public-data
   ```
3. Create destination paths matching `canonical_instance_path`.
4. Place mirrored artifacts at those paths and run:
   ```bash
   datalad save -m "Add initial FEMIC mirrored public datasets"
   ```
5. Configure and test remotes:
   - Arbutus S3 special remote via `git annex initremote`
   - GitHub sibling with `--publish-depends arbutus-s3`
6. Push dataset metadata and annexed content to both remotes.
7. Validate cold-clone retrieval:
   ```bash
   datalad clone git@github.com:UBC-FRESH/femic-public-data.git smoke
   cd smoke
   datalad get data/misc.thlb.tif
   ```

## Required Completion Artifacts

- Published dataset repo URL.
- Arbutus S3 special remote config recorded in repo docs.
- Checksum values backfilled in `metadata/required_datasets.yaml`.
- Follow-on FEMIC task: add repo as submodule (`P10.6c`).

## Windows Lessons Learned (Issue #95)

If this workflow is repeated from a fresh Windows environment for a new FEMIC
instance dataset, do not start from `git annex testremote`. The lowest-noise
path is:

1. Load a user-local env file with plain `KEY=VALUE` lines and no quotes.
2. In PowerShell, use an execution-policy-bypassed session before dot-sourcing
   the loader.
3. Confirm required vars are non-empty.
4. Run direct `HeadBucket` probe(s).
5. Only then run `git annex initremote`.

Known-good Windows-specific details now proven in `#95`:

- `%USERPROFILE%\.config\femic\arbutus.env` should contain:
  - `AWS_ACCESS_KEY_ID=<key-id>`
  - `AWS_SECRET_ACCESS_KEY=<secret-key>`
  - `AWS_DEFAULT_REGION=ca-west-1`
  - `S3_ENDPOINT_URL=https://object-arbutus.cloud.computecanada.ca`
  - `S3_BUCKET_NAME=<unique-bucket-name>`
- quoted values in `arbutus.env` are a real failure mode; they cause Windows to
  export invalid literal credentials;
- if interactive PowerShell blocks the loader script, use:
  - `Set-ExecutionPolicy -Scope Process Bypass -Force`
- the known-good `git annex initremote` parity flags are:
  - `public=yes`
  - `publicurl=https://object-arbutus.cloud.computecanada.ca/<unique-bucket-name>`
  - `host=object-arbutus.cloud.computecanada.ca`
  - `protocol=https`
  - `port=80`
  - `requeststyle=path`
  - `autoenable=true`
  - `chunk=1GiB`
  - `storageclass=STANDARD`

If `initremote` fails because the bucket already has a different `annex-uuid`,
inspect the bucket contents before doing anything destructive:

- if the bucket has real payload, treat it as a legitimate ownership conflict;
- if it contains only a stale lone `annex-uuid` marker from an aborted init,
  clear that marker and retry.

Publish order matters:

1. `git annex copy --to arbutus-s3 --all`
2. `git config remote.origin.datalad-publish-depends arbutus-s3`
3. `git push origin main`
4. `git push origin git-annex`
5. fresh-clone validation
