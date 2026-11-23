# Erişilemeyen Modül Sınıflandırması — Wiring Triage (DEF-02)

Bu tablo `docs/plan-v2/wiring_allowlist.txt` içindeki tüm eski/erişilemeyen modüller için mimari kararı tanımlar (`BİRLEŞTİR` yeni paket mimarisine taşınanlar, `BAĞLA` ilgili plan maddesine bağlı olanlar, `DONDUR/SİL` kapsam dışı bırakılanlar).

| Modül | Karar | Hedef Paket / Plan Maddesi | Gerekçe |
|---|---|---|---|
| `academic_expert` | BİRLEŞTİR | `master/domains/` (`DOM-01`) | Yeni alan motorları paketinde sıkı giriş doğrulaması ile yer alır |
| `auth_rbac` | BİRLEŞTİR | `master/access_control.py` (`SEC-01`, `SEC-04`) | İnce sarmalayıcı; gerçek oturum/RBAC koruması `access_control.py` içinde |
| `automation_engine` | DONDUR/SİL | `ORC-10` | Onay kapısı olmadan yerel otomasyon çalıştırılmayacak (Parça 8 kapsam dışı) |
| `bandit_router` | BİRLEŞTİR | `master/distributed/core.py` (`DIST-03`) | Thompson/UCB ajan yönlendirmesi `master/distributed/` içinde canlı bağlı |
| `browser_agent` | DONDUR/SİL | `ORC-10` | Genel amaçlı otonom tarayıcı ajanları güvenlik incelemesi gerektirir (Parça 8 kapsam dışı) |
| `build_pipelines` | BİRLEŞTİR | `master/factory/` (`IDE-01`, `IDE-18`) | Paketleme ve derleme aşamaları birleşik `master/factory/` hattına taşındı |
| `cad_kernel` | BİRLEŞTİR | `master/cad_cam_physics.py` (`DOM-06`) | İnce sarmalayıcı; STEP/IGES analizi `cad_cam_physics.py` içinde |
| `cad_projection` | BİRLEŞTİR | `master/domains/` (`DOM-06`) | Teknik çizim doğrulama yardımcısı alan motorları paketine taşındı |
| `cam_postprocessor` | BİRLEŞTİR | `master/cad_cam_physics.py` (`DOM-07`) | G-Code doğrulama ve çoklu kontrolör üretimi canlı `cad_cam_physics.py` içinde |
| `citation_guard` | BİRLEŞTİR | `master/hallucination/` (`HAL-06`, `HAL-08`) | Atıf zorunluluğu ve çözümleme yeni `master/hallucination/` paketinde canlı |
| `cmm_closed_loop` | BİRLEŞTİR | `master/cnc_api.py` (`DOM-08`) | CMM Cp/Cpk kapalı döngü denetimi canlı CNC API hattıyla birleştirildi |
| `cnc_physics` | BİRLEŞTİR | `master/cad_cam_physics.py` (`DOM-07`) | İnce sarmalayıcı; Kienzle kesme fiziği `cad_cam_physics.py` içinde |
| `cognitive_arena` | BİRLEŞTİR | `master/media_lab_arena.py` (`DIST-19`) | İnce sarmalayıcı; ELO sıralaması `media_lab_arena.py` içinde |
| `cyber_expert` | BİRLEŞTİR | `master/domains/` (`DOM-01`) | İnce sarmalayıcı; yeni `master/domains/` motorunda birleşti |
| `desktop_automation` | DONDUR/SİL | `ORC-10` | Ana makinede GUI/masaüstü otomasyonu güvenlik politikası gereği kapalı (Parça 8 kapsam dışı) |
| `dfm_advisor` | BİRLEŞTİR | `master/domains/` (`DOM-06`) | Üretilebilirlik kontrolü `master/domains/` paketine taşındı |
| `enterprise_connectors` | BİRLEŞTİR | `master/mcp_connector.py` (`SEC-11`) | İnce sarmalayıcı; şifreli bağlayıcılar `mcp_connector.py` ve `secret_store.py` içinde |
| `fault_tolerance` | BİRLEŞTİR | `master/distributed/core.py` (`DIST-06`, `DIST-22`) | Kiralama, yeniden atama ve kurtarma `master/distributed/` içinde canlı |
| `fea_solver` | BİRLEŞTİR | `master/cad_cam_physics.py` (`DOM-07`) | Basit kiriş/halka mekanik modeli `cad_cam_physics.py` içinde |
| `feedback_collector` | BİRLEŞTİR | `master/ml_ops/` (`ML-04`, `ML-05`) | İnce sarmalayıcı; DPO tercih/geri bildirim kaydı `master/ml_ops/` içinde canlı |
| `finance_expert` | BİRLEŞTİR | `master/domains/` (`DOM-01`, `DOM-04`) | İnce sarmalayıcı; uydurma varsayılan veri kapalı şekilde `master/domains/` içinde |
| `image_studio` | BİRLEŞTİR | `master/studios/` (`MM-06`, `MM-14`) | Görsel üretim ve imzalı medya hattı `master/studios/` paketinde canlı |
| `job_shop_scheduler` | BİRLEŞTİR | `master/erp_mes_scheduler.py` (`DOM-09`) | İnce sarmalayıcı; tezgâh çizelgeleme `erp_mes_scheduler.py` içinde |
| `knowledge_graph` | BİRLEŞTİR | `master/rag/` (`RAG-15`) | İnce sarmalayıcı; bilgi grafiği ve hibrit arama `master/rag/` içinde canlı |
| `legal_expert` | BİRLEŞTİR | `master/domains/` (`DOM-01`, `DOM-04`) | İnce sarmalayıcı; belgesiz tarama kapalı şekilde `master/domains/` içinde |
| `machine_iot` | DONDUR/SİL | `DOM-08` | Gerçek tezgâh bağlantısı kapsam dışı (Parça 8 Bölüm 6) |
| `map_reduce_llm` | BİRLEŞTİR | `master/orchestrator/` (`ORC-06`, `GW-05`) | Uzun bağlam böl-birleştir akışı `master/gateway/` ve `master/orchestrator/` içinde |
| `mcp_registry` | BİRLEŞTİR | `master/mcp_connector.py` (`ORC-08`) | İnce sarmalayıcı; araç ve MCP kaydı `mcp_connector.py` ve `orchestrator/tools.py` içinde |
| `media_analyzer` | BİRLEŞTİR | `master/studios/` (`MM-01`, `MM-04`) | Çoklu medya çözümleme `master/studios/` paketine taşındı |
| `media_factory_v2` | BİRLEŞTİR | `master/studios/` (`MM-06`, `MM-14`) | İnce sarmalayıcı; medya stüdyosu `master/studios/` içinde canlı |
| `model_gate` | BİRLEŞTİR | `master/ml_ops/` (`ML-10`, `HAL-05`) | İnce sarmalayıcı; eval kapısı ve model terfisi `master/ml_ops/` içinde |
| `nesting_optimizer` | BİRLEŞTİR | `master/erp_mes_scheduler.py` (`DOM-09`) | İnce sarmalayıcı; 1D kesim optimizasyonu `erp_mes_scheduler.py` içinde |
| `project_archetypes` | BİRLEŞTİR | `master/factory/` (`IDE-01`, `IDE-17`) | Proje şablonları `master/factory/` paketinde birleştirildi |
| `secure_sandbox` | BİRLEŞTİR | `master/sandbox/runner.py` (`SEC-13`) | Gerçek Docker konteyner izolasyonu `master/sandbox/` paketinde canlı |
| `security_scanner` | BİRLEŞTİR | `master/factory/` (`IDE-11`, `SEC-19`) | Statik güvenlik denetimi yazılım fabrikası doğrulama adımında ve CI'da |
| `software_factory` | BİRLEŞTİR | `master/factory/` (`IDE-01..24`) | Birleşik yazılım fabrikası hattı `master/factory/` paketinde canlı |
| `swarm_coordinator` | BİRLEŞTİR | `master/distributed/core.py` (`DIST-09`, `ORC-07`) | Dağıtık görev eşgüdümü `master/distributed/` paketinde canlı |
| `tools_data_sql` | BİRLEŞTİR | `master/studios/` (`DS-01..10`) | İnce sarmalayıcı; veri bilimi araçları `master/studios/` içinde |
| `tools_math_science` | BİRLEŞTİR | `master/orchestrator/` (`DEF-22`, `HAL-09`) | İnce sarmalayıcı; deterministik hesap ve SymPy doğrulama canlı hatta |
| `vector_store` | BİRLEŞTİR | `master/rag/store.py` (`RAG-04`, `DAT-11`) | İnce sarmalayıcı; sürümlü vektör + FTS5 deposu `master/rag/` içinde canlı |
| `vision_qc` | BİRLEŞTİR | `master/domains/` (`DOM-08`) | Görsel kalite kontrolü alan motorlarına taşındı |
| `vision_rag` | BİRLEŞTİR | `master/rag/` (`RAG-03`) | İnce sarmalayıcı; çoklu ortam belge alma `master/rag/` içinde |
| `visual_verifier` | BİRLEŞTİR | `master/factory/` (`IDE-06`) | Tarayıcı/görsel doğrulama yazılım fabrikası doğrulama adımına taşındı |
| `voice_engine` | BİRLEŞTİR | `master/multimodal_studio.py` (`MM-01`, `MM-02`) | Yerel Whisper STT ve ses işleme `multimodal_studio.py` ve `studios/` içinde canlı |
| `vram_manager` | BİRLEŞTİR | `master/gateway/power_manager.py` (`GW-06`, `OPS-24`) | VRAM/güç yönetimi `master/gateway/` paketinde canlı |
