from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass
class FileEntry:
    """Metadata describing an entry in the download directory."""

    name: str
    relative_path: str
    is_dir: bool
    size: int | None


class DirectoryAccessError(FileNotFoundError):
    """Raised when the requested path is outside the download root."""


def _ensure_within_base(base: Path, target: Path) -> Path:
    base = base.resolve()
    target = target.resolve()
    if base == target:
        return target
    if base in target.parents:
        return target
    raise DirectoryAccessError(f"Path '{target}' escapes download root {base}")


def resolve_directory(base: Path, relative_path: str = "") -> Path:
    """Return the absolute directory path inside the allowed root."""

    target = (base / relative_path).resolve()
    _ensure_within_base(base, target)
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError(f"Directory '{relative_path}' not found")
    return target


def build_listing(base: Path, relative_path: str = "") -> list[FileEntry]:
    """Return a sorted listing (dirs first) for the requested directory."""

    directory = resolve_directory(base, relative_path)
    entries: Iterable[Path] = directory.iterdir()

    base_posix = PurePosixPath(relative_path) if relative_path else None

    file_entries = []
    for item in entries:
        if base_posix:
            rel_path = base_posix / item.name
        else:
            rel_path = PurePosixPath(item.name)
        file_entries.append(
            FileEntry(
                name=item.name,
                relative_path=str(rel_path),
                is_dir=item.is_dir(),
                size=item.stat().st_size if item.is_file() else None,
            )
        )

    file_entries.sort(key=lambda entry: (not entry.is_dir, entry.name.lower()))
    return file_entries


def resolve_download(base: Path, relative_path: str) -> Path:
    """Return the absolute file path for download, ensuring safety."""

    if not relative_path:
        raise FileNotFoundError("No file provided")
    target = (base / relative_path).resolve()
    _ensure_within_base(base, target)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File '{relative_path}' not found")
    return target


def resolve_upload_target(base: Path, relative_path: str) -> Path:
    """Return the absolute path for an uploaded file, ensuring target parent exists."""

    if not relative_path:
        raise FileNotFoundError("No file provided")

    target = (base / relative_path).resolve()
    _ensure_within_base(base, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target
