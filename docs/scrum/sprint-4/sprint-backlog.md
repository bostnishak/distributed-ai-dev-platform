# Sprint 4 — Sprint Backlog

| | |
|---|---|
| Dates | 19 Kasım – 2 Aralık 2026 |
| Sprint Review + Retrospective | 2 Aralık 2026 |
| Status | Done |

## Sprint Goal

> Üretilen kodu gerçekten doğrulayın: sandbox'ta çalıştırın, test üretin, bağımsız ajan incelemesi yapın, dosya çakışmalarını çözün — ve hataları otomatik kurtarın.

## Items

| ID | Item | Responsible | Est. (h) | Target | Status |
|---|---|---|---|---|---|
| PB-40 | API sözleşme kontrolü: frontend fetch() ↔ backend rotalar | İshak Bostan | 10 h | 22 Nov | Done |
| PB-41 | Sandbox test koşucusu: Docker ağsız, zaman ve bellek limiti | Furkan Kaan Özbeyli | 18 h | 25 Nov | Done |
| PB-42 | Test üretme görevi + hata döngüsü (en fazla 2 tur) | Semih Sarıca | 16 h | 26 Nov | Done |
| PB-43 | Kod inceleme ajanı (asla yazar değil) + fix görevleri | Semih Sarıca | 14 h | 27 Nov | Done |
| PB-44 | Hata tespiti, kurtarma, yeniden atama (maks 3 deneme) | İshak Bostan | 12 h | 22 Nov | Done |
| PB-45 | Çakışma çözümü: aynı dosyaya dokunan sonuçlar | Işıl Karademir | 12 h | 24 Nov | Done |
| PB-46 | Scheduler + seçim testleri sahte ajanlarla | Zeynep Duru Küçük | 10 h | 23 Nov | Done |
| PB-47 | Proje sayfası: test sonuçları, kod inceleme bulguları, yeniden atama geçmişi | Berfin Yiğit | 14 h | 29 Nov | Done |
| — | Sprint 4 testleri + scrum belgeleri | Zeynep Duru Küçük (SM) | 8 h | 2 Ara | Done |

**Toplam:** 114 h

## Acceptance Criteria

| ID | Criteria |
|---|---|
| PB-40 | `GET /api/admin/contract-check` returns frontend/backend route lists and flags missing endpoints |
| PB-41 | Generated code runs in a network-isolated Docker container; exceeding time/memory limits returns a clear error |
| PB-42 | After a task is done, a "testing" task is automatically created; failed tests generate a fix task (max 2 cycles) |
| PB-43 | "review" tasks are never assigned to the agent that produced the code; `exclude_agent_id` wired in selection |
| PB-44 | `attempt >= MAX_ATTEMPTS (3)` → task status becomes "failed" permanently; requeue returns "failed" |
| PB-45 | Two tasks writing the same file path → conflict recorded; `GET /api/projects/{id}/conflicts` returns them; resolve endpoint marks resolved |
| PB-46 | 16 new tests covering max-attempt, conflict detection, review exclusion, DAG with fake agents |
| PB-47 | Project detail shows attempt count, validation badge, conflict warnings per task |
