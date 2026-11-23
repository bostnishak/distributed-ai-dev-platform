# Runbook: Encrypted Backup & Restore (`backup-restore`)

## Symptom
- Need to recover from database corruption, accidental deletion, or migrate the Master server to a new machine (`SEC-12`, `DAT-07`).

## Diagnosis
1. Locate the latest encrypted backup archive in `master/data/backups/` and its SHA-256 manifest.
2. Confirm the backup passphrase is available (never stored in git or inside the backup archive; secrets in `secrets` table are intentionally excluded per `SEC-11`).

## Resolution
1. Stop the running Master server before restoring data files.
2. Restore using `master/backup_manager.py` (or `POST /api/admin/backup/restore` with valid admin auth and passphrase).
3. Verify row counts, SHA-256 checksums, and run `master/db_doctor.py`.
4. Re-enter any external secrets via `master/secret_store.py` if needed, restart Master, and verify `GET /ready`.
