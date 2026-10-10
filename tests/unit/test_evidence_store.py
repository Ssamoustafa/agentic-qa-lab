from __future__ import annotations

from pathlib import Path

import pytest

from agentic_qa.domain.models import EvidenceReference, Outcome, ScenarioResult
from agentic_qa.infrastructure.evidence.store import FilesystemEvidenceStore


@pytest.fixture
def store(tmp_path: Path) -> FilesystemEvidenceStore:
    return FilesystemEvidenceStore(tmp_path / "artifacts")


def _result(*evidence: EvidenceReference) -> ScenarioResult:
    return ScenarioResult("s1", Outcome.FAILED, 1, evidence, failure_reason="failed")


def _artifact(store: FilesystemEvidenceStore, content: bytes = b"data") -> Path:
    directory = store.scenario_directory("run-1", "s1")
    path = directory / "artifact.bin"
    path.write_bytes(content)
    return path


@pytest.mark.parametrize("unsafe", ["..", "../x", "a/b", "", ".hidden", "a b", "x" * 65])
def test_directories_reject_unsafe_identifiers(store: FilesystemEvidenceStore, unsafe: str) -> None:
    with pytest.raises(ValueError, match="unsafe evidence path"):
        store.scenario_directory("run-1", unsafe)
    with pytest.raises(ValueError, match="unsafe evidence path"):
        store.run_directory(unsafe)


def test_reference_is_relative_and_carries_a_digest(store: FilesystemEvidenceStore) -> None:
    reference = store.reference("blob", _artifact(store))

    assert reference.location == "run-1/s1/artifact.bin"
    assert reference.sha256 is not None and len(reference.sha256) == 64


def test_reference_rejects_files_outside_the_root(
    store: FilesystemEvidenceStore, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("x")

    with pytest.raises(ValueError, match="escapes"):
        store.reference("blob", outside)


def test_reference_rejects_missing_files(store: FilesystemEvidenceStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.reference("blob", store.root / "run-1" / "missing.bin")


def test_write_json_is_confined_to_the_root(store: FilesystemEvidenceStore, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        store.write_json(tmp_path, "x.json", {})


def test_intact_evidence_has_no_problems(store: FilesystemEvidenceStore) -> None:
    reference = store.reference("blob", _artifact(store))

    assert store.problems(_result(reference)) == ()


def test_tampered_evidence_is_reported(store: FilesystemEvidenceStore) -> None:
    path = _artifact(store)
    reference = store.reference("blob", path)
    path.write_bytes(b"forged")

    assert "does not match its digest" in store.problems(_result(reference))[0]


def test_missing_evidence_is_reported(store: FilesystemEvidenceStore) -> None:
    path = _artifact(store)
    reference = store.reference("blob", path)
    path.unlink()

    assert "is missing" in store.problems(_result(reference))[0]


def test_reference_without_digest_is_reported(store: FilesystemEvidenceStore) -> None:
    path = _artifact(store)
    location = path.relative_to(store.root).as_posix()

    problems = store.problems(_result(EvidenceReference("blob", location)))

    assert "has no digest" in problems[0]


def test_reference_escaping_the_root_is_reported(store: FilesystemEvidenceStore) -> None:
    forged = EvidenceReference("blob", "../outside.txt", "a" * 64)

    assert "outside the evidence root" in store.problems(_result(forged))[0]
