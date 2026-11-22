"""Sphinx configuration for the Flemish Energy documentation."""

import json
from pathlib import Path

project = "Flemish Energy"
author = "Arkadiusz Ryś"
root = Path(__file__).resolve().parent.parent
manifest = root / "custom_components/flemish_energy/manifest.json"
release = json.loads(manifest.read_text(encoding="utf-8"))["version"]

extensions = ["myst_parser"]
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "sphinx_rtd_theme"
html_theme_options = {"collapse_navigation": False}
html_static_path = ["_static"]
html_logo = "_static/flemish-energy.svg"
html_favicon = html_logo
