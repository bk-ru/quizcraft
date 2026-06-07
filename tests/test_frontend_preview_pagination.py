from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def test_playable_preview_paginates_questions() -> None:
    content = (FRONTEND_DIR / "preview-mode.js").read_text(encoding="utf-8")
    styles = (FRONTEND_DIR / "layout.css").read_text(encoding="utf-8")

    assert 'footer.className = "quiz-preview-footer"' in content
    assert 'progress.className = "quiz-preview-progress"' in content
    assert "activeQuestionIndex" in content
    assert "updatePreviewPage()" in content
    assert "form.requestSubmit()" in content
    assert ".quiz-preview-footer" in styles
