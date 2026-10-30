"""Bound request ingestion before Starlette can spool an unbounded upload."""
from contextlib import asynccontextmanager

from fastapi import Request
from starlette.formparsers import MultiPartException, MultiPartParser

from errors import ApiError
from teacher_materials.storage import MAX_BYTES


class UploadTooLarge(MultiPartException):
    pass


class MaterialMultipartParser(MultiPartParser):
    # Starlette's max_part_size applies to text fields, not file parts.
    # Count file bytes in the parser callback, before they are queued for spooling.
    def on_part_begin(self) -> None:
        super().on_part_begin()
        self._file_bytes = 0

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        if self._current_part.file is not None:
            self._file_bytes += end - start
            if self._file_bytes > MAX_BYTES:
                raise UploadTooLarge("File must be no larger than 10 MiB.")
        super().on_part_data(data, start, end)


@asynccontextmanager
async def material_form(request: Request):
    async def limited_stream():
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            # Bound multipart headers and fields as well as the file itself.
            if total > MAX_BYTES + 64 * 1024:
                raise UploadTooLarge("File must be no larger than 10 MiB.")
            yield chunk

    parser = MaterialMultipartParser(
        request.headers, limited_stream(), max_files=1, max_fields=2,
        max_part_size=1024,
    )
    try:
        form = await parser.parse()
    except UploadTooLarge as exc:
        raise ApiError(413, "file_too_large", "File must be no larger than 10 MiB.") from exc
    except OSError as exc:
        raise ApiError(503, "service_unavailable", "Private file storage is unavailable.") from exc
    except Exception as exc:
        raise ApiError(422, "validation_error", "Valid multipart upload fields are required.") from exc
    try:
        yield form
    finally:
        await form.close()
