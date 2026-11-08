# Sprint 5 — Sprint Backlog

| | |
|---|---|
| Dates | 3 Aralık – 16 Aralık 2026 |
| Sprint Review + Retrospective | 16 Aralık 2026 |
| Status | Done |

## Sprint Goal

> Platformu uçtan uca sertleştirin ve demo hazır hale getirin: canlı pano, performans ölçümü, model karşılaştırma, güvenlik ve son belgeleme.

## Items

| ID | Item | Responsible | Est. (h) | Target | Status |
|---|---|---|---|---|---|
| PB-50 | Uçtan uca iş akışı sertleştirme — örnek doküman | İshak Bostan | 16 h | 7 Ara | Done |
| PB-51 | Pano: genel bakış ve canlı olay akışı | Berfin Yiğit | 16 h | 8 Ara | Done |
| PB-52 | Performans ölçümleri: süreler, başarı oranları, token/s | Zeynep Duru Küçük | 12 h | 7 Ara | Done |
| PB-53 | Ajan / model karşılaştırma görünümü | Berfin Yiğit | 12 h | 9 Ara | Done |
| PB-54 | Son belgeleme ve kullanıcı rehberi | Işıl Karademir | 10 h | 10 Ara | Done |
| PB-55 | Son testler ve demo provası — çalışan ajanı durdurma senaryosu | Semih Sarıca | 14 h | 14 Ara | Done |
| PB-56 | Güvenlik sertleştirme: UI erişimi, bağlama adresleri | Furkan Kaan Özbeyli | 10 h | 10 Ara | Done |
| — | Sprint 5 testleri + scrum belgeleri | Zeynep Duru Küçük (SM) | 8 h | 16 Ara | Done |

**Toplam:** 98 h

## Acceptance Criteria

| ID | Criteria |
|---|---|
| PB-50 | Kütüphane Yönetim Sistemi SRS → çalışan backend+frontend ZIP, tekrarlanabilir |
| PB-51 | `/api/dashboard` endpoint returns agent counts, project overview, perf stats, recent events; frontend tab auto-refreshes every 10 s |
| PB-52 | `perf_ms` stored per task; `GET /api/perf/stats` returns avg/min/max/by_type/by_agent |
| PB-53 | Agents tab shows side-by-side capability bars and model metadata for all registered agents |
| PB-54 | README, SRS, architecture docs up to date; user guide covers setup → first project → ZIP download |
| PB-55 | Demo script rehearsed: agent stops mid-task → lease expires → task reassigned → demo recovers |
| PB-56 | AGENT_TOKEN required on all /api/agents/* write endpoints; UI accessible only on 127.0.0.1 by default |
