from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agentic_qa.domain.models import EvidenceReference, ScenarioResult, is_safe_identifier

_CHUNK_SIZE = 1024 * 1024


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


class FilesystemEvidenceStore:
    """Confines evidence to one root and ties every reference to a content digest."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        return self._root

    def run_directory(self, run_id: str) -> Path:
        return self._directory(run_id)

    def scenario_directory(self, run_id: str, scenario_id: str) -> Path:
        return self._directory(run_id, scenario_id)

    def write_json(self, directory: Path, name: str, payload: object) -> Path:
        path = self._inside_root(directory / name)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def reference(self, kind: str, path: Path) -> EvidenceReference:
        resolved = self._inside_root(path)
        if not resolved.is_file():
            raise FileNotFoundError(f"evidence file does not exist: {path.name}")
        location = resolved.relative_to(self._root).as_posix()
        return EvidenceReference(kind, location, sha256_of(resolved))

    def problems(self, result: ScenarioResult) -> tuple[str, ...]:
        found: list[str] = []
        for reference in result.evidence:
            label = f"{reference.kind} ({reference.location})"
            try:
                path = self._inside_root(self._root / reference.location)
            except ValueError:
                found.append(f"{label} is outside the evidence root")
                continue
            if not path.is_file():
                found.append(f"{label} is missing")
            elif reference.sha256 is None:
                found.append(f"{label} has no digest")
            elif sha256_of(path) != reference.sha256.lower():
                found.append(f"{label} does not match its digest")
        return tuple(found)

    def _directory(self, *parts: str) -> Path:
        for part in parts:
            if not is_safe_identifier(part):
                raise ValueError(f"unsafe evidence path component: {part!r}")
        directory = self._inside_root(self._root.joinpath(*parts))
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _inside_root(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(self._root):
            raise ValueError("path escapes the evidence root")
        return resolved
