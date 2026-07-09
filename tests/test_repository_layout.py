from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DESIGN_DIR = ROOT / "docs" / "design" / "concepts" / "v2"
LOCAL_ONLY_PATHS = (
    "docs/design/concepts/v2",
    "docs/execplans",
    "docs/planning",
)
LOCAL_ONLY_FILE_PATHS = (
    "docs/design/concepts/v2/01-homepage.html",
    "docs/execplans/2026-05-16-grounded-matching.md",
    "docs/planning/backlog.md",
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_repository_layout_uses_canonical_locations() -> None:
    assert not (ROOT / "PLANS.md").exists()
    assert not (ROOT / "backlog.md").exists()
    assert not (ROOT / "design-concepts-v2").exists()


def test_local_only_docs_are_not_tracked() -> None:
    tracked_paths = _git("ls-files", *LOCAL_ONLY_PATHS)

    assert tracked_paths.returncode == 0
    assert tracked_paths.stdout == ""


def test_local_only_docs_are_ignored() -> None:
    ignored_paths = _git("check-ignore", *LOCAL_ONLY_FILE_PATHS)

    assert ignored_paths.returncode == 0
    assert ignored_paths.stdout.splitlines() == list(LOCAL_ONLY_FILE_PATHS)


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
    if not DESIGN_DIR.exists():
        return

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
