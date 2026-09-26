import sqlite3

import pytest

from sistemashn.core.operations.backup import create_backup, verify_backup
from sistemashn.core.operations.contracts import BackupError, RestoreError
from sistemashn.core.operations.restore import restore_to_trial


def test_snapshot_with_open_writer_and_trial_restore(tmp_path):
    source = tmp_path / "José 東京" / "datos.sqlite3"
    source.parent.mkdir()
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE items (name TEXT NOT NULL)")
        db.execute("INSERT INTO items VALUES ('confirmado')")
    writer = sqlite3.connect(source)
    try:
        writer.execute("INSERT INTO items VALUES ('sin confirmar')")
        destination = tmp_path / "copia con espacios.sqlite3"
        receipt = create_backup(source, destination)
        assert receipt.backup == destination
        assert verify_backup(destination).valid
        trial = tmp_path / "ensayo.sqlite3"
        restore_to_trial(destination, trial)
        with sqlite3.connect(trial) as db:
            assert db.execute("SELECT name FROM items").fetchall() == [("confirmado",)]
    finally:
        writer.rollback()
        writer.close()


def test_corruption_and_existing_destination_never_overwrite(tmp_path):
    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE items (name TEXT)")
    destination = tmp_path / "backup.sqlite3"
    create_backup(source, destination)
    with pytest.raises(BackupError):
        create_backup(source, destination)
    existing = tmp_path / "existing.sqlite3"
    existing.write_bytes(b"keep")
    with pytest.raises(RestoreError):
        restore_to_trial(destination, existing)
    assert existing.read_bytes() == b"keep"
    destination.write_bytes(b"corrupt")
    assert not verify_backup(destination).valid
    with pytest.raises(RestoreError):
        restore_to_trial(destination, tmp_path / "rejected.sqlite3")
