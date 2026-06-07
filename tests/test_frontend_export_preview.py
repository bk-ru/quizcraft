from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def test_export_modal_previews_local_formats_and_identifies_server_files() -> None:
    content = (FRONTEND_DIR / "export-modal.js").read_text(encoding="utf-8")
    styles = (FRONTEND_DIR / "forms.css").read_text(encoding="utf-8")

    assert "function serializeLocalExport" in content
    assert "function updateExportPreview" in content
    assert 'preview.className = "export-preview"' in content
    assert "config.transport === \"server\"" in content
    assert "new Blob([content]).size" in content
    assert ".export-preview-body" in styles
