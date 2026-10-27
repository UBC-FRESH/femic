from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))


project = "femic"
master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
if find_spec("nbsphinx"):
    extensions.append("nbsphinx")

autosummary_generate = True
autodoc_typehints = "description"
exclude_patterns = ["_build", "**.ipynb_checkpoints"]

if find_spec("sphinx_rtd_theme"):
    html_theme = "sphinx_rtd_theme"
    html_theme_options = {
        "collapse_navigation": False,
        "navigation_depth": 3,
    }
else:
    html_theme = "alabaster"
    html_theme_options = {}

_static_dir = Path(__file__).with_name("_static")
html_static_path = ["_static"] if _static_dir.exists() else []
html_extra_path = ["llms.txt"]
templates_path = ["_templates"]
