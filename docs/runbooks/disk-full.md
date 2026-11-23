# Runbook: Low Disk Space (`disk-full`)

## Symptom
- `GET /ready` reports `components.disk.status = "degraded"` (< 500 MB free) or `"down"` (< 50 MB free).
- Blob uploads, backups, or SQLite WAL writes fail with `ENOSPC`.

## Diagnosis
1. Inspect free disk space and largest subdirectories under `master/data/`:
   ```powershell
   Get-PSDrive C
   Get-ChildItem master\data -Recurse | Sort-Object Length -Descending | Select-Object -First 15 FullName, Length
   ```
2. Check unreferenced blobs, old backups, and Docker build cache (`docker system df`).

## Resolution
1. Run blob garbage collection and retention cleanup (`master/blobstore.py` / `master/retention.py`).
2. Prune old backup archives keeping the latest verified daily/weekly snapshots.
3. Run `docker system prune -f` if Docker image layers consume space.
4. Re-verify `GET http://127.0.0.1:8000/ready`.
