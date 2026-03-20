from __future__ import annotations

import csv
import json
from pathlib import Path

from typer.testing import CliRunner
import yaml

from femic.cli.main import app

DOCS_ROOT = Path("docs")
GUIDES_ROOT = DOCS_ROOT / "guides"
SAMPLE_MODELS_ROOT = DOCS_ROOT / "sample-models"
API_ROOT = DOCS_ROOT / "reference" / "api"
COVERAGE_CSV = GUIDES_ROOT / "legacy_notebook_coverage.csv"
K3Z_INSTANCE_ROOT = Path("external/femic-k3z-instance")
TSA29_INSTANCE_ROOT = Path("external/femic-tsa29-instance")

GUIDE_PAGES = [
    "pipeline-overview",
    "deployment-instances",
    "rebuild-repro-contract",
    "author-instance-rebuild-spec",
    "interpret-rebuild-reports",
    "data-access-inventory",
    "public-data-mirror-runbook",
    "case-onboarding",
    "stage-00-data-prep",
    "stage-01a-vdyp-tipsy-input",
    "stage-01b-post-tipsy",
    "model-input-bundle-and-export",
    "diagnostics-playbook",
    "troubleshooting",
    "limitations-and-boundaries",
    "patchworks-wine-runtime",
    "ubc-vpn-license-connectivity",
    "geospatial-runtime-bootstrap",
    "pypi-release-runbook",
    "legacy-traceability",
    "sphinx-template-baseline",
]
SAMPLE_MODEL_PAGES = [
    "k3z",
    "tsa29",
    "k3z-metadata-lineage",
]

NOTEBOOKS = [
    Path("reference/legacy_notebooks/00_data-prep.ipynb"),
    Path("reference/legacy_notebooks/01a_run-tsa.ipynb"),
    Path("reference/legacy_notebooks/01b_run-tsa.ipynb"),
]
LEGACY_SLUG = "wbi_ria_yield"

runner = CliRunner()


def _non_trivial_markdown_cells(path: Path) -> set[tuple[str, int]]:
    payload = json.loads(path.read_text())
    keys: set[tuple[str, int]] = set()
    for idx, cell in enumerate(payload.get("cells", [])):
        if cell.get("cell_type") != "markdown":
            continue
        text = " ".join("".join(cell.get("source", [])).split())
        if len(text) >= 10:
            keys.add((path.name, idx))
    return keys


def test_guides_pages_are_in_docs_tree() -> None:
    assert (DOCS_ROOT / "index.rst").exists()
    index_text = (DOCS_ROOT / "index.rst").read_text()
    assert "guides/index" in index_text

    guides_index = (GUIDES_ROOT / "index.rst").read_text()
    for slug in GUIDE_PAGES:
        page_path = GUIDES_ROOT / f"{slug}.rst"
        assert page_path.exists(), f"missing guide page: {page_path}"
        assert slug in guides_index, f"missing toctree entry for {slug}"


def test_release_runbook_and_workflows_exist() -> None:
    runbook = GUIDES_ROOT / "pypi-release-runbook.rst"
    assert runbook.exists()
    runbook_text = runbook.read_text(encoding="utf-8")
    assert "TestPyPI" in runbook_text
    assert "Production PyPI publication" in runbook_text
    assert "scripts/release_package_checks.sh" in runbook_text

    assert Path(".github/workflows/publish-testpypi.yml").exists()
    assert Path(".github/workflows/publish-pypi.yml").exists()


def test_legacy_notebook_coverage_matrix_is_complete() -> None:
    assert COVERAGE_CSV.exists(), "missing notebook coverage artifact"

    with COVERAGE_CSV.open(newline="") as fh:
        rows = list(csv.DictReader(fh))

    assert rows, "coverage CSV is empty"

    expected_keys: set[tuple[str, int]] = set()
    for notebook in NOTEBOOKS:
        expected_keys |= _non_trivial_markdown_cells(notebook)

    observed_keys: set[tuple[str, int]] = set()
    for row in rows:
        key = (row["notebook"], int(row["cell_index"]))
        observed_keys.add(key)
        assert row["classification"] in {
            "assumptions",
            "step intent",
            "interpretation guidance",
            "failure mode",
            "operator action",
        }
        assert row["status"] in {"mapped", "retired"}
        assert row["target_doc"].startswith("guides/")
        target_path = DOCS_ROOT / f"{row['target_doc']}.rst"
        assert target_path.exists(), f"target doc missing for row {key}: {target_path}"

    assert observed_keys == expected_keys


def test_cli_reference_mentions_current_high_value_options() -> None:
    cli_doc = (DOCS_ROOT / "reference" / "cli.rst").read_text()

    checks: list[tuple[list[str], list[str]]] = [
        (
            ["run", "--help"],
            [
                "--run-config",
                "--run-id",
                "--log-dir",
                "--debug-rows",
                "--instance-root",
            ],
        ),
        (
            ["prep", "validate-case", "--help"],
            ["--run-config", "--tipsy-config-dir", "--strict-warnings"],
        ),
        (
            ["prep", "geospatial-preflight", "--help"],
            ["--strict-warnings", "--skip-shapefile-smoke"],
        ),
        (
            ["vdyp", "report", "--help"],
            [
                "--max-curve-warnings",
                "--max-first-point-mismatches",
                "--max-curve-parse-errors",
                "--min-curve-events",
            ],
        ),
        (
            ["tsa", "post-tipsy", "--help"],
            ["--tsa", "--run-id", "--log-dir", "--run-config"],
        ),
        (
            ["export", "patchworks", "--help"],
            [
                "--bundle-dir",
                "--checkpoint",
                "--cc-transition-ifm",
                "--ifm-source-col",
                "--ifm-threshold",
                "--ifm-target-managed-share",
            ],
        ),
        (
            ["export", "release", "--help"],
            [
                "--case-id",
                "--patchworks-dir",
                "--woodstock-dir",
                "--strict",
                "--no-strict",
            ],
        ),
        (
            ["export", "dual", "--help"],
            [
                "--with-ws3-smoke",
                "--ws3-command",
                "--ws3-workdir",
                "--ws3-report",
                "--ws3-repo-path",
                "--ws3-builtin-smoke",
                "--ws3-bridge-dir",
            ],
        ),
        (
            ["patchworks", "preflight", "--help"],
            ["--config"],
        ),
        (
            ["patchworks", "matrix-build", "--help"],
            ["--config", "--log-dir", "--run-id", "--interactive"],
        ),
        (
            ["patchworks", "build-blocks", "--help"],
            [
                "--config",
                "--model-dir",
                "--fragments-shp",
                "--topology-radius",
                "--with-topology",
                "--no-topology",
                "--instance-root",
            ],
        ),
        (
            ["instance", "init", "--help"],
            [
                "--instance-root",
                "--overwrite",
                "--download-bc-vri",
                "--no-download-bc-vri",
                "--yes",
            ],
        ),
        (
            ["instance", "rebuild", "--help"],
            [
                "--spec",
                "--run-config",
                "--tipsy-config-dir",
                "--log-dir",
                "--run-id",
                "--with-patchworks",
                "--no-patchworks",
                "--dry-run",
                "--patchworks-config",
                "--baseline",
                "--write-baseline",
                "--allowlist",
                "--instance-root",
            ],
        ),
        (
            ["instance", "validate-spec", "--help"],
            ["--spec", "--instance-root"],
        ),
        (
            ["instance", "promote-evidence", "--help"],
            [
                "--report",
                "--output",
                "--log-dir",
                "--max-warn-increase",
                "--max-baseline-diff-increase",
                "--instance-root",
            ],
        ),
        (
            ["instance", "refresh-reference-evidence", "--help"],
            [
                "--report",
                "--reference-root",
                "--max-warn-increase",
                "--max-baseline-diff-increase",
            ],
        ),
        (
            ["instance", "ws3-smoke", "--help"],
            [
                "--woodstock-dir",
                "--output",
                "--ws3-command",
                "--ws3-workdir",
                "--require-command",
                "--timeout-seconds",
                "--ws3-repo-path",
                "--ws3-bridge-dir",
            ],
        ),
    ]

    for argv, options in checks:
        result = runner.invoke(app, argv)
        assert result.exit_code == 0, result.output
        for option in options:
            assert option in result.output, (
                f"CLI no longer exposes expected option {option}"
            )
            assert option in cli_doc, f"CLI docs missing option {option}"


def test_case_onboarding_templates_exist() -> None:
    assert Path("instances/reference/config/run_profile.case_template.yaml").exists()
    assert Path("instances/reference/config/rebuild.spec.yaml").exists()
    assert Path("instances/reference/config/rebuild.allowlist.yaml").exists()
    assert Path("instances/reference/runbooks/REBUILD_RUNBOOK.md").exists()
    assert Path("instances/reference/config/tipsy/template.case.yaml").exists()
    runbook_text = Path("instances/reference/runbooks/REBUILD_RUNBOOK.md").read_text()
    assert "femic instance refresh-reference-evidence" in runbook_text
    assert "evidence/reference_rebuild_report.latest.json" in runbook_text
    assert "femic instance account-surface" in runbook_text
    assert "diagnosis.total_ok_species_empty_signature" in runbook_text


def test_case_onboarding_guide_keeps_template_and_preflight_links() -> None:
    guide_text = (GUIDES_ROOT / "case-onboarding.rst").read_text()
    assert "config/run_profile.case_template.yaml" in guide_text
    assert "config/rebuild.spec.yaml" in guide_text
    assert "config/rebuild.allowlist.yaml" in guide_text
    assert "runbooks/REBUILD_RUNBOOK.md" in guide_text
    assert "config/tipsy/template.case.yaml" in guide_text
    assert "python -m femic prep validate-case" in guide_text
    assert "cd instances/reference" in guide_text


def test_reference_instance_location_is_defined_and_documented() -> None:
    reference_root = Path("instances/reference")
    assert reference_root.is_dir()
    assert (reference_root / "config/run_profile.case_template.yaml").is_file()
    assert (reference_root / "config/tipsy/template.case.yaml").is_file()
    assert (reference_root / "QUICKSTART.md").is_file()
    assert (reference_root / "evidence/reference_rebuild_report.latest.json").is_file()

    guide_text = (GUIDES_ROOT / "deployment-instances.rst").read_text()
    assert "instances/reference/" in guide_text
    pipeline_text = (GUIDES_ROOT / "pipeline-overview.rst").read_text()
    assert "instances/reference/" in pipeline_text


def test_active_docs_and_config_avoid_repo_root_path_wording() -> None:
    contract_files = [
        Path("README.md"),
        DOCS_ROOT / "guides" / "pipeline-overview.rst",
        DOCS_ROOT / "guides" / "case-onboarding.rst",
        DOCS_ROOT / "sample-models" / "k3z.rst",
        Path("config/patchworks.runtime.yaml"),
        Path("config/patchworks.runtime.windows.yaml"),
    ]
    forbidden_snippets = [
        "repository root",
        "repo root",
        "relative to the repo root",
        "/home/gep/projects/",
    ]

    for path in contract_files:
        text = path.read_text().lower()
        for snippet in forbidden_snippets:
            assert snippet not in text, (
                f"{path} includes forbidden repo-coupled deployment wording: {snippet}"
            )


def test_package_release_checks_workflow_exists() -> None:
    workflow_path = Path(".github/workflows/package-release-checks.yml")
    workflow_text = workflow_path.read_text()

    assert "python -m build" in workflow_text
    assert "twine check dist/*" in workflow_text
    assert "pip install dist/*.whl" in workflow_text
    assert "femic instance init" in workflow_text
    assert "femic prep validate-case" in workflow_text
    assert "FEMIC_EXTERNAL_DATA_ROOT=" in workflow_text
    assert "Reference instance rebuild evidence gate" in workflow_text
    assert "instances/reference/evidence/reference_rebuild_report.latest.json" in (
        workflow_text
    )


def test_docs_include_installed_package_instance_run_workflow() -> None:
    readme_text = Path("README.md").read_text()
    deploy_text = (GUIDES_ROOT / "deployment-instances.rst").read_text()
    pipeline_text = (GUIDES_ROOT / "pipeline-overview.rst").read_text()

    assert "python -m pip install femic" in readme_text
    assert "femic instance init" in readme_text
    assert "femic run --run-config" in readme_text
    assert "python -m pip install femic" in deploy_text
    assert "femic prep validate-case" in deploy_text
    assert "femic run --run-config" in pipeline_text


def test_k3z_instance_repo_submodule_docs_contract() -> None:
    deploy_text = (GUIDES_ROOT / "deployment-instances.rst").read_text()
    onboarding_text = (GUIDES_ROOT / "case-onboarding.rst").read_text()
    k3z_text = (SAMPLE_MODELS_ROOT / "k3z.rst").read_text()

    for text in (deploy_text, onboarding_text, k3z_text):
        assert "UBC-FRESH/femic-k3z-instance" in text
        assert "external/femic-k3z-instance" in text

    assert "git submodule update --init --recursive" in deploy_text
    assert "git submodule update --remote external/femic-k3z-instance" in deploy_text
    assert "git submodule update --init --recursive" in onboarding_text
    assert (
        "git submodule update --remote external/femic-k3z-instance" in onboarding_text
    )


def test_tsa29_instance_repo_submodule_docs_contract() -> None:
    deploy_text = (GUIDES_ROOT / "deployment-instances.rst").read_text()
    onboarding_text = (GUIDES_ROOT / "case-onboarding.rst").read_text()
    tsa29_text = (SAMPLE_MODELS_ROOT / "tsa29.rst").read_text()

    for text in (deploy_text, onboarding_text, tsa29_text):
        assert "UBC-FRESH/femic-tsa29-instance" in text
        assert "external/femic-tsa29-instance" in text

    assert "git submodule update --init --recursive" in tsa29_text
    assert "git submodule update --remote external/femic-tsa29-instance" in deploy_text
    assert (
        "git submodule update --remote external/femic-tsa29-instance" in onboarding_text
    )


def test_tsa29_instance_standalone_docs_scaffold_exists() -> None:
    docs_root = TSA29_INSTANCE_ROOT / "docs"
    assert docs_root.is_dir()
    assert (docs_root / "conf.py").is_file()
    assert (docs_root / "index.rst").is_file()
    assert (docs_root / "requirements.txt").is_file()
    assert (TSA29_INSTANCE_ROOT / ".readthedocs.yaml").is_file()
    assert (TSA29_INSTANCE_ROOT / ".github/workflows/docs-pages.yml").is_file()
    assert (
        TSA29_INSTANCE_ROOT / "evidence/reference_rebuild_report.latest.json"
    ).is_file()
    assert (TSA29_INSTANCE_ROOT / "metadata/lineage_registry.yaml").is_file()


def test_k3z_instance_standalone_docs_scaffold_exists() -> None:
    docs_root = K3Z_INSTANCE_ROOT / "docs"
    assert docs_root.is_dir()
    assert (docs_root / "conf.py").is_file()
    assert (docs_root / "index.rst").is_file()
    assert (docs_root / "requirements.txt").is_file()
    assert (K3Z_INSTANCE_ROOT / ".readthedocs.yaml").is_file()
    assert (K3Z_INSTANCE_ROOT / ".github/workflows/docs-pages.yml").is_file()

    index_text = (docs_root / "index.rst").read_text()
    for slug in (
        "getting-started",
        "model-anatomy",
        "data-package-crosswalk",
        "land-base-and-netdown",
        "assumptions-registry",
        "base-case-analysis",
        "figure-appendix",
        "metadata-and-lineage",
        "operator-runbook",
        "edit-policy-and-scenarios",
        "docs-ownership-and-release",
        "rebuild-and-qa",
        "troubleshooting",
    ):
        assert slug in index_text


def test_k3z_instance_standalone_docs_required_sections_and_navigation() -> None:
    docs_root = K3Z_INSTANCE_ROOT / "docs"
    index_text = (docs_root / "index.rst").read_text()
    assert "K3Z Instance User Guide" in index_text
    assert ":caption: Guide" in index_text

    getting_started_text = (docs_root / "getting-started.rst").read_text()
    for heading in (
        "Purpose",
        "Prerequisites",
        "Quickstart",
        "Authoritative Paths",
    ):
        assert heading in getting_started_text
    for snippet in (
        "femic prep validate-case",
        "femic run --run-config",
        "femic patchworks matrix-build",
    ):
        assert snippet in getting_started_text

    model_anatomy_text = (docs_root / "model-anatomy.rst").read_text()
    for heading in ("Directory Map", "Generated vs Editable"):
        assert heading in model_anatomy_text
    for snippet in (
        "models/k3z_patchworks_model/",
        "config/seral.k3z.yaml",
        "tracks/*.csv",
    ):
        assert snippet in model_anatomy_text

    rebuild_qa_text = (docs_root / "rebuild-and-qa.rst").read_text()
    for heading in (
        "Deterministic Rebuild Script",
        "Outputs",
        "Key Invariants",
        "Baseline Workflow",
    ):
        assert heading in rebuild_qa_text
    assert "femic instance rebuild" in rebuild_qa_text
    assert "config/rebuild.spec.yaml" in rebuild_qa_text

    troubleshooting_text = (docs_root / "troubleshooting.rst").read_text()
    for heading in (
        "Patchworks Launches But Reports Block Join Errors",
        "Species Accounts Missing or Zero",
        "Patchworks Runtime Preflight Fails",
    ):
        assert heading in troubleshooting_text
    for snippet in (
        "femic instance account-surface",
        "total OK, species-wise empty",
        "required_nonzero",
    ):
        assert snippet in troubleshooting_text


def test_k3z_instance_tsr_data_package_pages_exist_with_required_sections() -> None:
    docs_root = K3Z_INSTANCE_ROOT / "docs"

    crosswalk_text = (docs_root / "data-package-crosswalk.rst").read_text()
    for heading in ("Section Crosswalk", "Reference Exemplars"):
        assert heading in crosswalk_text
    for exemplar in (
        "TFL26 Timber Supply Analysis Information Package",
        "CFA Timber Supply Analysis Data Package and Base Case Results",
        "FNWL Timber Supply Analysis Data Package and Base Case Results",
    ):
        assert exemplar in crosswalk_text

    landbase_text = (docs_root / "land-base-and-netdown.rst").read_text()
    for heading in (
        "Introduction",
        "Land Base Definition",
        "Exclusions from Contributing Forest",
        "Reductions from THLB (Netdown Logic)",
        "Analysis Area Map",
        "Total Area and THLB Summary",
        "Area by AU",
        "Provenance Table",
        "THLB Netdown Placeholder Table",
        "What to Edit vs Regenerate",
        "How to Validate Reruns",
    ):
        assert heading in landbase_text
    for column in (
        "Update Date",
        "Source Path/URL",
        "Transform Stage",
        "QA Status",
    ):
        assert column in landbase_text

    assumptions_text = (docs_root / "assumptions-registry.rst").read_text()
    for heading in (
        "Non-Timber Assumptions",
        "Harvesting Assumptions",
        "Growth and Yield Assumptions",
        "Natural Disturbance Assumptions",
        "Modeling Assumptions",
        "Provenance Table",
        "What to Edit vs Regenerate",
        "How to Validate Reruns",
        "References",
    ):
        assert heading in assumptions_text

    analysis_text = (docs_root / "base-case-analysis.rst").read_text()
    for heading in (
        "Analysis Report",
        "Base Case Output and Interpretation",
        "Expected-Empty Account Matrix",
        "Discussion",
        "Known Limitations and Uncertainty",
        "Provenance Table",
        "What to Edit vs Regenerate",
        "How to Validate Reruns",
        "References",
    ):
        assert heading in analysis_text
    assert "Figure Appendix Linkage" in analysis_text
    assert ":ref:`k3z-figure-appendix`" in analysis_text

    appendix_text = (docs_root / "figure-appendix.rst").read_text()
    for heading in (
        "Analysis Area Map",
        "Strata Distribution Figure",
        "VDYP Low/Medium/High Envelopes",
        "VDYP Fit Diagnostics",
        "Treated \\(Scaled-VDYP\\) Curve Overlays",
        "Full Plot Inventory",
    ):
        assert heading in appendix_text
    for snippet in (
        ".. _k3z-figure-appendix:",
        ".. figure:: _static/k3z_analysis_area_map.png",
        ".. figure:: ../plots/strata-tsak3z.png",
        "k3z_analysis_area_map.png",
        "plots/strata-tsak3z.png",
        "plots/vdyp_lmh_tsak3z-",
        "plots/vdyp_fitdiag_tsak3z-",
        "plots/tipsy_vdyp_tsak3z-",
    ):
        assert snippet in appendix_text

    metadata_text = (docs_root / "metadata-and-lineage.rst").read_text()
    for heading in (
        "Artifact Family Inventory",
        "Build-Lineage Chain",
        "Validation Evidence",
        "Provenance Versioning Policy",
    ):
        assert heading in metadata_text

    runbook_text = (docs_root / "operator-runbook.rst").read_text()
    for heading in (
        "Fresh Setup",
        "Rebuild Workflow",
        "Diagnostics Workflow",
        "Troubleshooting Workflow",
        "Release Checklist",
        "Publication Checklist",
    ):
        assert heading in runbook_text

    policy_text = (docs_root / "edit-policy-and-scenarios.rst").read_text()
    for heading in (
        "Edit Policy Matrix",
        "Scenario Comparison Guidance",
        "Interpretation Workflow",
        "Classroom Use Guidance",
        "How to Validate Reruns",
    ):
        assert heading in policy_text

    governance_text = (docs_root / "docs-ownership-and-release.rst").read_text()
    for heading in (
        "Ownership Matrix",
        "Update Cadence",
        "Release Tagging and Versioning Policy",
        "Contributor Onboarding and Review Workflow",
    ):
        assert heading in governance_text


def test_k3z_standalone_docs_do_not_reference_parent_repo_paths() -> None:
    docs_root = K3Z_INSTANCE_ROOT / "docs"
    forbidden_snippets = (
        "scripts/k3z/rebuild_k3z_instance.py",
        "reference/",
        "external/femic-k3z-instance",
    )
    for path in docs_root.glob("*.rst"):
        text = path.read_text()
        for snippet in forbidden_snippets:
            assert snippet not in text, f"{path} references parent-repo path: {snippet}"


def test_fhops_aligned_sphinx_template_contract() -> None:
    parent_conf = Path("docs/conf.py").read_text()
    standalone_conf = (K3Z_INSTANCE_ROOT / "docs/conf.py").read_text()
    parent_workflow = Path(".github/workflows/docs-pages.yml").read_text()
    standalone_workflow = (
        K3Z_INSTANCE_ROOT / ".github/workflows/docs-pages.yml"
    ).read_text()
    baseline_guide = (GUIDES_ROOT / "sphinx-template-baseline.rst").read_text()

    for conf_text in (parent_conf, standalone_conf):
        for required in (
            '"sphinx.ext.autodoc"',
            '"sphinx.ext.autosummary"',
            '"sphinx.ext.napoleon"',
            '"sphinx.ext.viewcode"',
            'autodoc_typehints = "description"',
            '"collapse_navigation": False',
            '"navigation_depth": 3',
        ):
            assert required in conf_text
        assert "sphinx_rtd_theme" in conf_text

    for workflow_text in (parent_workflow, standalone_workflow):
        for required in (
            "pages: write",
            "id-token: write",
            "actions/upload-pages-artifact@v4",
            "actions/deploy-pages@v4",
            "sphinx-build",
            "-W",
        ):
            assert required in workflow_text

    assert "https://github.com/UBC-FRESH/fhops" in baseline_guide


def test_sample_model_pages_are_in_docs_tree() -> None:
    assert (DOCS_ROOT / "index.rst").exists()
    index_text = (DOCS_ROOT / "index.rst").read_text()
    assert "sample-models/index" in index_text

    sample_models_index = (SAMPLE_MODELS_ROOT / "index.rst").read_text()
    for slug in SAMPLE_MODEL_PAGES:
        page_path = SAMPLE_MODELS_ROOT / f"{slug}.rst"
        assert page_path.exists(), f"missing sample-model page: {page_path}"
        assert slug in sample_models_index, f"missing toctree entry for {slug}"


def test_api_reference_pages_are_in_docs_tree_and_list_public_modules() -> None:
    index_text = (DOCS_ROOT / "index.rst").read_text()
    assert "reference/api/index" in index_text

    api_index = (API_ROOT / "index.rst").read_text()
    assert "API contract" in api_index
    assert "femic.resources" in api_index
    assert "private members" in api_index
    assert "modules" in api_index

    modules_page = (API_ROOT / "modules.rst").read_text()
    for module_name in (
        "femic.cli.main",
        "femic.patchworks_runtime",
        "femic.pipeline.stages",
        "femic.rebuild_runner",
    ):
        assert module_name in modules_page
    assert "femic.resources" not in modules_page


def test_k3z_sample_model_docs_keep_required_sections() -> None:
    k3z_text = (SAMPLE_MODELS_ROOT / "k3z.rst").read_text()
    required_k3z_sections = [
        "Purpose",
        "Canonical Student Docs",
        "Submodule Sync Commands",
        "FEMIC-Local Integration Notes",
    ]
    for heading in required_k3z_sections:
        assert heading in k3z_text, f"k3z.rst missing required section: {heading}"
    assert "https://github.com/UBC-FRESH/femic-k3z-instance" in k3z_text
    assert "https://ubc-fresh.github.io/femic-k3z-instance/" in k3z_text
    assert "external/femic-k3z-instance" in k3z_text
    assert "git submodule update --init --recursive" in k3z_text
    assert "git submodule update --remote external/femic-k3z-instance" in k3z_text
    assert "config/rebuild.spec.yaml" in k3z_text
    assert "config/rebuild.allowlist.yaml" in k3z_text
    assert "runbooks/REBUILD_RUNBOOK.md" in k3z_text
    assert "k3z-metadata-lineage.rst" in k3z_text

    lineage_text = (SAMPLE_MODELS_ROOT / "k3z-metadata-lineage.rst").read_text()
    required_lineage_sections = [
        "Inventory: Upstream Sources -> Model Artifacts",
        "Build-Lineage Chain",
        "Provenance Versioning Policy",
        "Acceptance Checklist for Lineage Updates",
    ]
    for heading in required_lineage_sections:
        assert heading in lineage_text, (
            f"k3z-metadata-lineage.rst missing required section: {heading}"
        )


def test_legacy_traceability_docs_include_notebook_cleanup_policy() -> None:
    traceability_text = (GUIDES_ROOT / "legacy-traceability.rst").read_text()
    assert "Notebook Output Cleanup Policy" in traceability_text
    assert "jupyter nbconvert --clear-output --inplace" in traceability_text


def test_geospatial_runtime_bootstrap_guide_keeps_required_sections() -> None:
    guide_text = (GUIDES_ROOT / "geospatial-runtime-bootstrap.rst").read_text()
    for heading in (
        "Why This Matters",
        "Windows Bootstrap Ritual",
        "Linux Bootstrap Ritual",
        "Verify Runtime Readiness",
        "Troubleshooting",
    ):
        assert heading in guide_text
    assert "femic prep geospatial-preflight" in guide_text


def test_instance_rebuild_contract_artifacts_are_present_and_complete() -> None:
    contract_doc = Path("planning/femic_instance_rebuild_contract.md")
    contract_yaml = Path("planning/femic_instance_rebuild_contract.v1.yaml")

    assert contract_doc.is_file()
    assert contract_yaml.is_file()

    contract_text = contract_doc.read_text()
    for heading in (
        "Required Inputs and Prerequisites (`P13.1a`)",
        "Authoritative Rebuild Sequence (`P13.1b`)",
        "Required Post-Rebuild Invariants (`P13.1c`)",
        "Failure Classes and Remediation Messaging (`P13.1d`)",
    ):
        assert heading in contract_text

    payload = yaml.safe_load(contract_yaml.read_text())
    assert payload["contract_id"] == "femic_instance_rebuild_contract_v1"
    assert payload["version"] == "1.0"
    for key in (
        "required_inputs",
        "authoritative_sequence",
        "post_rebuild_invariants",
        "failure_classes",
    ):
        assert key in payload
    assert payload["authoritative_sequence"], "authoritative sequence must not be empty"
    assert payload["post_rebuild_invariants"], "invariants list must not be empty"


def test_instance_rebuild_spec_schema_artifact_is_present_and_structured() -> None:
    schema_path = Path("planning/femic_instance_rebuild_spec_schema.v1.yaml")
    assert schema_path.is_file()
    payload = yaml.safe_load(schema_path.read_text())

    assert payload["schema_id"] == "femic_instance_rebuild_spec_schema_v1"
    assert payload["version"] == "1.0"
    root = payload["root"]
    assert root["type"] == "map"
    assert set(root["required"]) == {
        "schema_version",
        "instance",
        "runtime",
        "steps",
        "invariants",
    }
    fields = root["fields"]
    assert fields["steps"]["type"] == "list"
    assert fields["invariants"]["type"] == "list"
    step_fields = fields["steps"]["item"]["fields"]
    for required in ("step_id", "kind", "required", "depends_on", "expected_outputs"):
        assert required in step_fields
    invariant_fields = fields["invariants"]["item"]["fields"]
    for required in ("invariant_id", "severity", "metric", "comparator", "target"):
        assert required in invariant_fields


def test_rebuild_repro_contract_guide_covers_core_sections() -> None:
    guide_text = (GUIDES_ROOT / "rebuild-repro-contract.rst").read_text()
    required_sections = [
        "Purpose",
        "Contract Sources",
        "Expected Operator Workflow",
        "Required Evidence Artifacts",
        "Failure Classes",
        "Contributor Policy (Mandatory for New Instance Repos)",
    ]
    for section in required_sections:
        assert section in guide_text


def test_contributor_policy_requires_rebuild_spec_and_checks() -> None:
    contract_text = (GUIDES_ROOT / "rebuild-repro-contract.rst").read_text()
    required_markers = [
        "config/rebuild.spec.yaml",
        "config/rebuild.allowlist.yaml",
        "femic instance validate-spec",
        "femic instance rebuild",
    ]
    for marker in required_markers:
        assert marker in contract_text


def test_reference_rebuild_evidence_payload_is_present_and_passing() -> None:
    path = Path("instances/reference/evidence/reference_rebuild_report.latest.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    gate = payload["regression_gate"]
    assert gate["step_failure"] is False
    assert gate["fatal_invariant_failure"] is False
    assert gate["unexpected_diff_regression"] is False


def test_phase_13_closure_policy_requires_rebuild_evidence_note() -> None:
    roadmap_text = Path("ROADMAP.md").read_text(encoding="utf-8")
    changelog_text = Path("CHANGE_LOG.md").read_text(encoding="utf-8")
    required_phrase = (
        "no new instance phase closes without reproducible rebuild evidence"
    )
    assert required_phrase in roadmap_text.lower()
    assert required_phrase in changelog_text.lower()


def test_author_instance_rebuild_spec_guide_covers_core_sections() -> None:
    guide_text = (GUIDES_ROOT / "author-instance-rebuild-spec.rst").read_text()
    required_sections = [
        "Purpose",
        "Start from Template",
        "Core Sections",
        "Minimal Copy-Ready Example",
        "Step Authoring Rules",
        "Invariant Authoring Rules",
        "K3Z Reference Pattern",
        "Dry-Run and Execute",
    ]
    for section in required_sections:
        assert section in guide_text
    assert "species_account_policy" in guide_text


def test_interpret_rebuild_reports_guide_covers_core_sections() -> None:
    guide_text = (GUIDES_ROOT / "interpret-rebuild-reports.rst").read_text()
    required_sections = [
        "Report Location",
        "Step Outcomes",
        "Invariant Results",
        "Baseline and Allowlist Diffs",
        "Regression Gate",
        "Evidence Trend Drift Across Releases",
        "Triage Workflow",
    ]
    for section in required_sections:
        assert section in guide_text
    for marker in (
        "trend_drift.previous_summary",
        "trend_drift.warn_increase",
        "trend_drift.baseline_diff_increase",
        "--max-warn-increase",
        "--max-baseline-diff-increase",
    ):
        assert marker in guide_text


def test_k3z_reference_rebuild_spec_exists_and_matches_schema_basics() -> None:
    spec_path = K3Z_INSTANCE_ROOT / "config/rebuild.spec.yaml"
    assert spec_path.is_file()
    payload = yaml.safe_load(spec_path.read_text())

    assert payload["schema_version"] == "1.0"
    assert payload["instance"]["case_id"] == "k3z"
    assert payload["runtime"]["run_config"] == "config/run_profile.k3z.yaml"
    step_ids = [step["step_id"] for step in payload["steps"]]
    assert "validate_case" in step_ids
    assert "compile_upstream" in step_ids
    assert "patchworks_matrix_build" in step_ids


def test_legacy_slug_references_are_limited_to_audit_trail_files() -> None:
    allowed_paths = {
        Path("ROADMAP.md"),
        Path("CHANGE_LOG.md"),
    }
    candidate_files = [
        Path("README.md"),
        Path("CITATION.cff"),
        Path("pyproject.toml"),
        Path(".github/workflows/docs-pages.yml"),
    ]
    allowed_suffixes = {
        ".py",
        ".rst",
        ".md",
        ".yaml",
        ".yml",
        ".toml",
        ".cff",
        ".json",
        ".txt",
    }
    for root in (Path("src"), Path("docs"), Path("config")):
        candidate_files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in allowed_suffixes
        )

    offenders: list[str] = []
    for path in candidate_files:
        if path in allowed_paths:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if LEGACY_SLUG in text:
            offenders.append(str(path))

    assert not offenders, "legacy slug appears outside audit-trail files: " + ", ".join(
        offenders
    )
