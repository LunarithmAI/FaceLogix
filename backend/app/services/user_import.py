from __future__ import annotations

import csv
import hashlib
import io
import stat
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import BinaryIO

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.images import MAX_IMAGE_BYTES, image_media_type

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_CSV_BYTES = 1024 * 1024
MAX_ARCHIVE_ENTRIES = 512
MAX_IMPORT_ROWS = 100
CSV_NAME = "people.csv"
IMAGE_COLUMNS = tuple(f"image_{index}" for index in range(1, 6))
REQUIRED_COLUMNS = {"external_id", "name", "image_1"}
ALLOWED_COLUMNS = REQUIRED_COLUMNS | {"email", "unit", *IMAGE_COLUMNS[1:]}
_EMAIL_ADAPTER = TypeAdapter(EmailStr)


@dataclass(frozen=True, slots=True)
class ImportRowError:
    row: int | None
    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedImportRow:
    row: int
    external_id: str
    name: str
    email: str | None
    unit: str | None
    image_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParsedUserImport:
    package_sha256: str
    total_rows: int
    rows: tuple[ParsedImportRow, ...]
    images: dict[str, bytes]
    errors: tuple[ImportRowError, ...]


@dataclass(slots=True)
class UserImportPackageError(Exception):
    code: str
    message: str
    status_code: int = 422


def _archive_size(file: BinaryIO) -> int:
    file.seek(0, io.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size


def _archive_sha256(file: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := file.read(1024 * 1024):
        digest.update(chunk)
    file.seek(0)
    return digest.hexdigest()


def _safe_member_path(name: str) -> str:
    if "\\" in name:
        raise UserImportPackageError("UNSAFE_ARCHIVE", "Archive paths must use forward slashes")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise UserImportPackageError("UNSAFE_ARCHIVE", "Archive contains an unsafe path")
    return path.as_posix()


def _is_ignored_member(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return "__MACOSX" in parts or parts[-1] == ".DS_Store"


def _read_csv(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> tuple[list[str], list[dict[str, str]]]:
    if info.file_size > MAX_CSV_BYTES:
        raise UserImportPackageError("CSV_TOO_LARGE", "people.csv exceeds the 1 MiB limit", 413)
    try:
        text = archive.read(info).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UserImportPackageError("INVALID_CSV", "people.csv must be UTF-8 encoded") from exc
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise UserImportPackageError("INVALID_CSV", "people.csv has no header row")
        normalized_headers = [field.strip() for field in fieldnames]
        if len(normalized_headers) != len(set(normalized_headers)):
            raise UserImportPackageError("INVALID_CSV", "people.csv contains duplicate headers")
        missing = sorted(REQUIRED_COLUMNS - set(normalized_headers))
        unknown = sorted(set(normalized_headers) - ALLOWED_COLUMNS)
        if missing:
            raise UserImportPackageError(
                "INVALID_CSV", f"people.csv is missing required columns: {', '.join(missing)}"
            )
        if unknown:
            raise UserImportPackageError(
                "INVALID_CSV", f"people.csv contains unknown columns: {', '.join(unknown)}"
            )
        reader.fieldnames = normalized_headers
        rows: list[dict[str, str]] = []
        for row in reader:
            if None in row:
                raise UserImportPackageError(
                    "INVALID_CSV", "A CSV row contains more values than the header"
                )
            normalized_row = {key: value or "" for key, value in row.items()}
            if any(value.strip() for value in normalized_row.values()):
                rows.append(normalized_row)
    except csv.Error as exc:
        raise UserImportPackageError("INVALID_CSV", "people.csv could not be parsed") from exc
    if not rows:
        raise UserImportPackageError("INVALID_CSV", "people.csv contains no people")
    if len(rows) > MAX_IMPORT_ROWS:
        raise UserImportPackageError(
            "TOO_MANY_PEOPLE", f"A package may contain at most {MAX_IMPORT_ROWS} people", 413
        )
    return normalized_headers, rows


def _validate_row(
    row_number: int, raw: dict[str, str]
) -> tuple[ParsedImportRow, list[ImportRowError]]:
    errors: list[ImportRowError] = []
    values = {key: (value or "").strip() for key, value in raw.items()}
    external_id = values["external_id"]
    name = values["name"]
    email_value = values.get("email", "")
    unit = values.get("unit", "") or None

    if not external_id:
        errors.append(
            ImportRowError(row_number, "REQUIRED_FIELD", "External ID is required", "external_id")
        )
    elif len(external_id) > 255:
        errors.append(
            ImportRowError(
                row_number, "FIELD_TOO_LONG", "External ID exceeds 255 characters", "external_id"
            )
        )
    if not name:
        errors.append(ImportRowError(row_number, "REQUIRED_FIELD", "Name is required", "name"))
    elif len(name) > 255:
        errors.append(
            ImportRowError(row_number, "FIELD_TOO_LONG", "Name exceeds 255 characters", "name")
        )
    if unit is not None and len(unit) > 255:
        errors.append(
            ImportRowError(row_number, "FIELD_TOO_LONG", "Unit exceeds 255 characters", "unit")
        )

    email: str | None = None
    if email_value:
        if len(email_value) > 255:
            errors.append(
                ImportRowError(
                    row_number, "FIELD_TOO_LONG", "Email exceeds 255 characters", "email"
                )
            )
        else:
            try:
                email = str(_EMAIL_ADAPTER.validate_python(email_value))
            except ValidationError:
                errors.append(
                    ImportRowError(row_number, "INVALID_EMAIL", "Email address is invalid", "email")
                )

    image_paths: list[str] = []
    found_gap = False
    for column in IMAGE_COLUMNS:
        value = values.get(column, "")
        if not value:
            found_gap = True
            continue
        if found_gap:
            errors.append(
                ImportRowError(
                    row_number,
                    "IMAGE_SEQUENCE_GAP",
                    "Image columns must be filled in order without gaps",
                    column,
                )
            )
        try:
            image_paths.append(_safe_member_path(value))
        except UserImportPackageError:
            errors.append(
                ImportRowError(row_number, "UNSAFE_IMAGE_PATH", "Image path is not safe", column)
            )
    if not image_paths:
        errors.append(
            ImportRowError(
                row_number, "REQUIRED_FIELD", "At least one face image is required", "image_1"
            )
        )

    return (
        ParsedImportRow(
            row=row_number,
            external_id=external_id,
            name=name,
            email=email,
            unit=unit,
            image_paths=tuple(image_paths),
        ),
        errors,
    )


def parse_user_import_archive(file: BinaryIO) -> ParsedUserImport:
    size = _archive_size(file)
    if size == 0:
        raise UserImportPackageError("EMPTY_PACKAGE", "Import package is empty")
    if size > MAX_ARCHIVE_BYTES:
        raise UserImportPackageError("PACKAGE_TOO_LARGE", "Import package exceeds 128 MiB", 413)
    package_sha256 = _archive_sha256(file)
    if not zipfile.is_zipfile(file):
        file.seek(0)
        raise UserImportPackageError(
            "INVALID_PACKAGE", "Import package must be a valid ZIP archive"
        )
    file.seek(0)

    try:
        with zipfile.ZipFile(file) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise UserImportPackageError(
                    "TOO_MANY_FILES",
                    f"A package may contain at most {MAX_ARCHIVE_ENTRIES} entries",
                    413,
                )

            members: dict[str, zipfile.ZipInfo] = {}
            total_uncompressed = 0
            for info in infos:
                path = _safe_member_path(info.filename)
                if info.is_dir():
                    continue
                if info.flag_bits & 0x1:
                    raise UserImportPackageError(
                        "ENCRYPTED_ARCHIVE", "Encrypted ZIP files are not supported"
                    )
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise UserImportPackageError(
                        "UNSAFE_ARCHIVE", "Archive symbolic links are not supported"
                    )
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                    raise UserImportPackageError(
                        "PACKAGE_TOO_LARGE", "Uncompressed package content exceeds 128 MiB", 413
                    )
                if _is_ignored_member(path):
                    continue
                if path in members:
                    raise UserImportPackageError(
                        "INVALID_PACKAGE", f"Archive contains duplicate path: {path}"
                    )
                members[path] = info

            csv_info = members.get(CSV_NAME)
            if csv_info is None:
                raise UserImportPackageError(
                    "MISSING_CSV", "Import package must contain people.csv at its root"
                )
            _, raw_rows = _read_csv(archive, csv_info)

            rows: list[ParsedImportRow] = []
            errors: list[ImportRowError] = []
            seen_external_ids: dict[str, int] = {}
            seen_emails: dict[str, int] = {}
            referenced_images: dict[str, int] = {}
            for row_number, raw in enumerate(raw_rows, start=2):
                row, row_errors = _validate_row(row_number, raw)
                errors.extend(row_errors)
                if row.external_id:
                    previous_external_row = seen_external_ids.get(row.external_id)
                    if previous_external_row is not None:
                        errors.append(
                            ImportRowError(
                                row.row,
                                "DUPLICATE_EXTERNAL_ID",
                                f"External ID also appears on row {previous_external_row}",
                                "external_id",
                            )
                        )
                    else:
                        seen_external_ids[row.external_id] = row.row
                if row.email is not None:
                    previous_email_row = seen_emails.get(row.email)
                    if previous_email_row is not None:
                        errors.append(
                            ImportRowError(
                                row.row,
                                "DUPLICATE_EMAIL",
                                f"Email also appears on row {previous_email_row}",
                                "email",
                            )
                        )
                    else:
                        seen_emails[row.email] = row.row
                for image_path in row.image_paths:
                    previous_image_row = referenced_images.get(image_path)
                    if previous_image_row is not None:
                        errors.append(
                            ImportRowError(
                                row.row,
                                "DUPLICATE_IMAGE",
                                f"Image is already assigned to row {previous_image_row}",
                                "image_1",
                            )
                        )
                    else:
                        referenced_images[image_path] = row.row
                rows.append(row)

            images: dict[str, bytes] = {}
            total_image_bytes = 0
            for image_path, row_number in referenced_images.items():
                image_info = members.get(image_path)
                if image_info is None:
                    errors.append(
                        ImportRowError(
                            row_number,
                            "IMAGE_NOT_FOUND",
                            f"Referenced image was not found: {image_path}",
                            "image_1",
                        )
                    )
                    continue
                if image_info.file_size == 0:
                    errors.append(
                        ImportRowError(
                            row_number, "INVALID_IMAGE", f"Image is empty: {image_path}", "image_1"
                        )
                    )
                    continue
                if image_info.file_size > MAX_IMAGE_BYTES:
                    errors.append(
                        ImportRowError(
                            row_number,
                            "IMAGE_TOO_LARGE",
                            f"Image exceeds the 10 MiB limit: {image_path}",
                            "image_1",
                        )
                    )
                    continue
                total_image_bytes += image_info.file_size
                if total_image_bytes > MAX_UNCOMPRESSED_BYTES:
                    raise UserImportPackageError(
                        "PACKAGE_TOO_LARGE", "Referenced images exceed 128 MiB", 413
                    )
                data = archive.read(image_info)
                if image_media_type(data) is None:
                    errors.append(
                        ImportRowError(
                            row_number,
                            "UNSUPPORTED_MEDIA_TYPE",
                            f"Only JPEG and PNG images are supported: {image_path}",
                            "image_1",
                        )
                    )
                    continue
                images[image_path] = data
    except zipfile.BadZipFile as exc:
        raise UserImportPackageError(
            "INVALID_PACKAGE", "Import package is not a valid ZIP archive"
        ) from exc
    finally:
        file.seek(0)

    return ParsedUserImport(
        package_sha256=package_sha256,
        total_rows=len(raw_rows),
        rows=tuple(rows),
        images=images,
        errors=tuple(errors),
    )
