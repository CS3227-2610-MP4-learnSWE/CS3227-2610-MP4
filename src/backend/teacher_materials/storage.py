"""Bound and validate original upload bytes before database storage."""
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath

from fastapi import UploadFile
from pypdf import PdfReader

from errors import ApiError

MAX_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    media_type: str
    size_bytes: int
    content: bytes


def validate_upload(upload: UploadFile) -> ValidatedUpload:
    raw_name = (upload.filename or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", raw_name)[:255]
    extension = PurePath(name).suffix.lower()
    if extension not in (".pdf", ".txt"):
        raise ApiError(415, "unsupported_media_type", "Choose a PDF or UTF-8 text file (maximum 10 MiB).")
    try:
        content = upload.file.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ApiError(503, "service_unavailable", "Upload processing is unavailable.") from exc
    if len(content) > MAX_BYTES:
        raise ApiError(413, "file_too_large", "File must be no larger than 10 MiB.")
    if not content:
        raise ApiError(422, "validation_error", "File must not be empty.")
    try:
        if extension == ".pdf":
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted or len(reader.pages) < 1:
                raise ValueError("invalid PDF")
            media_type = "application/pdf"
        else:
            content.decode("utf-8", errors="strict")
            media_type = "text/plain; charset=utf-8"
    except Exception as exc:
        raise ApiError(422, "validation_error", "File must be a readable PDF or valid UTF-8 text.") from exc
    return ValidatedUpload(name, media_type, len(content), content)
