from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DESIGN_DIR = ROOT / "docs" / "design" / "concepts" / "v2"
STAGED_FLOW_PROTOTYPE = ROOT / "staged-flow-prototype" / "index.html"
EXPECTED_DESIGN_FILES = {
    "01-homepage.html",
    "02-quiz-editor.html",
    "03-status-page.html",
    "04-mobile.html",
    "05-export-page.html",
}


def test_repository_layout_uses_canonical_locations() -> None:
    assert (ROOT / ".agent" / "PLANS.md").is_file()
    assert (ROOT / "docs" / "planning" / "backlog.md").is_file()
    assert STAGED_FLOW_PROTOTYPE.is_file()
    assert DESIGN_DIR.is_dir()
    assert {path.name for path in DESIGN_DIR.glob("*.html")} == EXPECTED_DESIGN_FILES
    assert not (ROOT / "PLANS.md").exists()
    assert not (ROOT / "backlog.md").exists()
    assert not (ROOT / "design-concepts-v2").exists()


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


def test_staged_flow_prototype_exposes_russian_step_flow() -> None:
    content = STAGED_FLOW_PROTOTYPE.read_text(encoding="utf-8", errors="strict")

    assert '<html lang="ru">' in content
    assert "Поэтапная генерация квиза" in content
    for russian_fragment in (
        "1. Загрузите документ",
        "2. Настройте квиз",
        "3. Отслеживайте обработку",
        "4. Проверьте результат",
        "5. Отредактируйте и экспортируйте",
        "Ёжик_Москва_2026_кириллица",
    ):
        assert russian_fragment in content
