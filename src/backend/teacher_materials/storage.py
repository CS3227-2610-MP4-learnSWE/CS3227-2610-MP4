"""Stream uploads into private storage and validate their actual content."""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pypdf import PdfReader

from errors import ApiError

MAX_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    original_filename: str
    media_type: str
    size_bytes: int


def storage_root() -> Path:
    value = os.getenv("FILE_STORAGE_DIR")
    if not value or not Path(value).is_absolute():
        raise ApiError(503, "service_unavailable", "Private file storage is unavailable.")
    root = Path(value)
    try:
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise OSError("not a directory")
    except OSError as exc:
        raise ApiError(503, "service_unavailable", "Private file storage is unavailable.") from exc
    return root


def resolve_file(storage_root: Path, storage_key: str) -> Path:
    root = storage_root.resolve()
    candidate = (root / storage_key).resolve()
    if not storage_key or candidate.parent != root or candidate == root:
        raise ApiError(503, "service_unavailable", "Private file storage is unavailable.")
    return candidate


def remove_file(storage_root: Path, storage_key: str) -> None:
    resolve_file(storage_root, storage_key).unlink(missing_ok=True)


def save_upload(upload: UploadFile, storage_root: Path) -> StoredFile:
    raw_name = (upload.filename or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", raw_name)[:255]
    extension = Path(name).suffix.lower()
    if extension not in (".pdf", ".txt"):
        raise ApiError(415, "unsupported_media_type", "Choose a PDF or UTF-8 text file (maximum 10 MiB).")
    key = f"{uuid4().hex}{extension}"
    stage_key = f".{uuid4().hex}.stage"
    stage = resolve_file(storage_root, stage_key)
    final = resolve_file(storage_root, key)
    size = 0
    try:
        with stage.open("xb") as out:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ApiError(413, "file_too_large", "File must be no larger than 10 MiB.")
                out.write(chunk)
        if size == 0:
            raise ApiError(422, "validation_error", "File must not be empty.")
        try:
            if extension == ".pdf":
                reader = PdfReader(stage)
                if reader.is_encrypted or len(reader.pages) < 1:
                    raise ValueError("invalid PDF")
                media_type = "application/pdf"
            else:
                stage.read_bytes().decode("utf-8")
                media_type = "text/plain; charset=utf-8"
        except Exception as exc:
            raise ApiError(422, "validation_error", "File must be a readable PDF or valid UTF-8 text.") from exc
        stage.replace(final)
        return StoredFile(key, name, media_type, size)
    except ApiError:
        stage.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        raise
    except OSError as exc:
        stage.unlink(missing_ok=True)
        final.unlink(missing_ok=True)
        raise ApiError(503, "service_unavailable", "Private file storage is unavailable.") from exc
