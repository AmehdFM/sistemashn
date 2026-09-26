from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BackupReceipt:
    backup: Path
    manifest: Path
    sha256: str
    revision: str | None


@dataclass(frozen=True)
class VerificationResult:
    path: Path
    valid: bool
    integrity_ok: bool
    hash_ok: bool
    revision_ok: bool
    revision: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class RestoreResult:
    backup: Path
    trial_db: Path
    verification: VerificationResult


@dataclass(frozen=True)
class UpdateResult:
    installation: Path
    data_dir: Path
    previous_version: str
    installed_version: str


class BackupError(RuntimeError):
    pass


class RestoreError(RuntimeError):
    pass


class UpdateError(RuntimeError):
    pass
