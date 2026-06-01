from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DESIGN_DIR = ROOT / "docs" / "design" / "concepts" / "v2"
EXPECTED_DESIGN_FILES = {
    "01-homepage.html",
    "02-quiz-editor.html",
    "03-status-page.html",
    "04-mobile.html",
    "05-export-page.html",
}


def test_repository_layout_uses_canonical_locations() -> None:
    assert (ROOT / "docs" / "planning" / "backlog.md").is_file()
    assert DESIGN_DIR.is_dir()
    assert {path.name for path in DESIGN_DIR.glob("*.html")} == EXPECTED_DESIGN_FILES
    assert not (ROOT / "PLANS.md").exists()
    assert not (ROOT / "backlog.md").exists()
    assert not (ROOT / "design-concepts-v2").exists()


def test_frontend_workspace_modules_use_canonical_locations() -> None:
    assert (ROOT / "frontend" / "sidebar.js").is_file()
    assert (ROOT / "frontend" / "workspace.js").is_file()
    assert (ROOT / "frontend" / "question-shape.js").is_file()
    assert (ROOT / "frontend" / "undo-stack.js").is_file()
    assert (ROOT / "frontend" / "preview-mode.js").is_file()
    assert (ROOT / "frontend" / "text-export.js").is_file()
    assert (ROOT / "frontend" / "export-modal.js").is_file()


def test_backend_run_script_does_not_enable_reload_by_default() -> None:
    script = (ROOT / "run-backend.ps1").read_text(encoding="utf-8")

    assert "[switch]$Reload" in script
    assert 'if ($Reload)' in script
    assert "[switch]$NoReload" not in script


def test_design_concepts_keep_internal_html_links_resolvable() -> None:
    pattern = re.compile(r"""(?:href|window\.location\.href)\s*=\s*['"]([^'"]+\.html)['"]""")
    all_referenced_files: set[str] = set()

    for html_file in DESIGN_DIR.glob("*.html"):
        content = html_file.read_text(encoding="utf-8", errors="strict")
        referenced_files = pattern.findall(content)
        all_referenced_files.update(referenced_files)
        for referenced_file in referenced_files:
            target = DESIGN_DIR / referenced_file
            assert target.is_file(), f"{html_file.name} references missing file {referenced_file}"

    assert all_referenced_files
