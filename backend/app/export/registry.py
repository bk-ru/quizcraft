"""Registry for quiz export formats."""

from __future__ import annotations

from collections.abc import Mapping

from backend.app.domain.errors import DomainValidationError
from backend.app.domain.errors import UnsupportedExportFormatError
from backend.app.domain.models import Quiz
from backend.app.export.base import ExportedQuizFile
from backend.app.export.base import QuizExporter
from backend.app.export.docx_exporter import QuizDocxExporter
from backend.app.export.json_exporter import QuizJsonExporter


class QuizExportRegistry:
    """Resolve quiz exporters by stable format keys."""

    def __init__(self, exporters: Mapping[str, QuizExporter]) -> None:
        registered_exporters: dict[str, QuizExporter] = {}
        for export_format, exporter in exporters.items():
            normalized_format = self._normalize_registered_format(export_format)
            if normalized_format in registered_exporters:
                raise DomainValidationError(
                    f"duplicate quiz export format registered: {normalized_format}"
                )
            registered_exporters[normalized_format] = exporter
        if not registered_exporters:
            raise DomainValidationError("at least one quiz export format must be registered")
        self._exporters = registered_exporters

    def supported_formats(self) -> tuple[str, ...]:
        """Return registered quiz export formats in deterministic order."""

        return tuple(sorted(self._exporters))

    def get(self, export_format: str) -> QuizExporter:
        """Resolve one quiz exporter by requested format."""

        normalized_format = self._normalize_requested_format(export_format)
        exporter = self._exporters.get(normalized_format)
        if exporter is None:
            raise UnsupportedExportFormatError(normalized_format, self.supported_formats())
        return exporter

    def export(self, quiz: Quiz, export_format: str) -> ExportedQuizFile:
        """Export one quiz using the exporter registered for the requested format."""

        return self.get(export_format).export(quiz)

    @staticmethod
    def _normalize_registered_format(export_format: str) -> str:
        if not isinstance(export_format, str) or not export_format.strip():
            raise DomainValidationError("quiz export format keys must be non-empty strings")
        return export_format.strip().casefold()

    @staticmethod
    def _normalize_requested_format(export_format: str) -> str:
        if not isinstance(export_format, str):
            return str(export_format).casefold()
        return export_format.strip().casefold()


DEFAULT_QUIZ_EXPORT_REGISTRY = QuizExportRegistry(
    {
        "docx": QuizDocxExporter(),
        "json": QuizJsonExporter(),
    }
)
