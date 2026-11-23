# Runbook: SQLite Database Locked or Unwritable (`database-locked`)

## Symptom
- `GET /ready` returns HTTP 503 with `components.database.status = "down"`.
- Logs show `sqlite3.OperationalError: database is locked` or permission errors.

## Diagnosis
1. Check if multiple uvicorn instances or stray scripts hold open locks on `master/data/*.db`:
   ```powershell
   Get-Process python* | Select-Object Id, ProcessName, StartTime
   ```
2. Run the database integrity doctor:
   ```powershell
   .\master\venv\Scripts\python.exe master/db_doctor.py
   ```
3. Verify WAL journal mode and checkpoint size (`platform.db-wal`).

## Resolution
1. Stop duplicate Master processes so only one server writes to `master/data/`.
2. Run WAL checkpoint and integrity repair via `master/db_doctor.py --repair`.
3. Confirm `GET http://127.0.0.1:8000/ready` returns `components.database.status == "ok"`.
