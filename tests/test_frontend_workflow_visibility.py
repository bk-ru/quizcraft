from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def test_hero_is_visible_only_on_setup_stage() -> None:
    content = (FRONTEND_DIR / "feedback.css").read_text(encoding="utf-8")

    assert '.workspace[data-active-stage="setup"]' in content
    assert ".workspace-workbench:not(:has(" in content
    assert ".hero {" in content
    assert "display: none;" in content
