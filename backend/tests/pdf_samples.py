from __future__ import annotations


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_stream(page_text: str | None) -> bytes:
    if page_text is None:
        return b""

    escaped_text = _escape_pdf_text(page_text)
    return (
        "BT\n"
        "/F1 12 Tf\n"
        "72 720 Td\n"
        f"({escaped_text}) Tj\n"
        "ET\n"
    ).encode("ascii")


def build_pdf_bytes(pages: list[str | None]) -> bytes:
    page_object_numbers = []
    content_object_numbers = []
    next_object_number = 4
    for _ in pages:
        page_object_numbers.append(next_object_number)
        content_object_numbers.append(next_object_number + 1)
        next_object_number += 2

    kids = " ".join(f"{object_number} 0 R" for object_number in page_object_numbers)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    for page_object_number, content_object_number, page_text in zip(page_object_numbers, content_object_numbers, pages):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_number} 0 R >>"
            ).encode("ascii")
        )
        stream = _build_stream(page_text)
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    payload = bytearray(header)
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{object_number} 0 obj\n".encode("ascii"))
        payload.extend(body)
        payload.extend(b"\nendobj\n")

    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(payload)
