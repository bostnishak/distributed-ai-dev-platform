# Parça 5 — Python statik analiz bulguları (2)

## PYD · Python: gömülü uzun metinler ve büyük modüller

#### PYD-01 · assistant.py:636 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] assistant.py:636: 13 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-02 · auth/service.py:45 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] auth/service.py:45: 21 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-03 · benchmarks.py:140 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] benchmarks.py:140: 18 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-04 · benchmarks.py:166 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] benchmarks.py:166: 17 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-05 · benchmarks.py:191 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] benchmarks.py:191: 16 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-06 · benchmarks.py:215 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] benchmarks.py:215: 14 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-07 · benchmarks.py:237 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] benchmarks.py:237: 15 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-08 · cmm_closed_loop.py:30 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] cmm_closed_loop.py:30: 26 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-09 · cnc_ballooning.py:825 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] cnc_ballooning.py:825: 12 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-10 · db.py:89 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] db.py:89: 113 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-11 · decompose.py:58 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] decompose.py:58: 23 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-12 · deep_research.py:333 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] deep_research.py:333: 23 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-13 · distributed/core.py:555 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] distributed/core.py:555: 12 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-14 · distributed/core.py:70 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] distributed/core.py:70: 46 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-15 · document_factory.py:96 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] document_factory.py:96: 17 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-16 · factory/templates.py:14 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] factory/templates.py:14: 12 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-17 · factory/templates.py:50 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] factory/templates.py:50: 15 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-18 · games/studio.py:15 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] games/studio.py:15: 39 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-19 · gateway/client.py:179 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] gateway/client.py:179: 30 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-20 · gateway/registry.py:173 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] gateway/registry.py:173: 20 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-21 · gateway/registry.py:78 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] gateway/registry.py:78: 19 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-22 · hallucination/verifier.py:593 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] hallucination/verifier.py:593: 33 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-23 · hybrid_graph_rag.py:247 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] hybrid_graph_rag.py:247: 38 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-24 · hybrid_graph_rag.py:323 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] hybrid_graph_rag.py:323: 11 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-25 · mcp_connector.py:43 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] mcp_connector.py:43: 17 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-26 · memory_engine.py:35 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] memory_engine.py:35: 50 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-27 · ml_ops/models.py:275 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] ml_ops/models.py:275: 26 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-28 · multimodal_studio.py:568 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] multimodal_studio.py:568: 13 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-29 · orchestrator/state.py:364 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] orchestrator/state.py:364: 13 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-30 · orchestrator/state.py:75 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] orchestrator/state.py:75: 73 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-31 · rag/store.py:146 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] rag/store.py:146: 74 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-32 · studios/multimedia.py:281 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] studios/multimedia.py:281: 11 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-33 · user_profile.py:89 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] user_profile.py:89: 34 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-34 · ux_api.py:122 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] ux_api.py:122: 11 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-35 · workspace_builder.py:218 gömülü uzun metin
- **Sorun:** [DOĞRULANDI: F208] workspace_builder.py:218: 19 satırlık gömülü metin/prompt; sürümsüz, ölçülmemiş ve kodla birlikte değişiyor.
- **Değişiklik:** Metni `master/prompts/*.md` şablonuna taşı, değişken doğrulamalı yükleyiciyle oku, şablon değişince eval çalıştır.
- **Kabul:** Kodda ≥ 10 satırlık gömülü metin kalmaz (lint); şablon sürümü yanıt kaydında.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### PYD-36 · assistant.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] assistant.py: 1874 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-37 · cad_cam_physics.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] cad_cam_physics.py: 785 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-38 · cnc_ballooning.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] cnc_ballooning.py: 2028 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-39 · code_graph.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] code_graph.py: 935 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-40 · db.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] db.py: 782 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-41 · distributed/core.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] distributed/core.py: 616 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-42 · domain_experts.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] domain_experts.py: 732 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-43 · gateway/client.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] gateway/client.py: 911 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-44 · hallucination/verifier.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] hallucination/verifier.py: 736 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-45 · hybrid_graph_rag.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] hybrid_graph_rag.py: 778 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-46 · multimodal_studio.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] multimodal_studio.py: 910 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-47 · rag/store.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] rag/store.py: 711 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-48 · user_profile.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] user_profile.py: 917 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

#### PYD-49 · workspace_builder.py çok büyük modül
- **Sorun:** [DOĞRULANDI: F208] workspace_builder.py: 766 satır; test ve inceleme maliyeti yüksek.
- **Değişiklik:** Sorumluluklara göre paketlere böl; dışa aktarılan API'yi koru.
- **Kabul:** Modül ≤ 600 satır; mevcut testler değişmeden geçer.
- **Meta:** P2 · L · Bağ: - · Durum: açık

## PRM · Python: çok parametreli fonksiyonlar

#### PRM-01 · blobstore.py:69 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] blobstore.py:69 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 blobstore.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-02 · cad_cam_physics.py:636 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cad_cam_physics.py:636 — Too many arguments in function definition (17 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 cad_cam_physics.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-03 · cad_cam_physics.py:732 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cad_cam_physics.py:732 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 cad_cam_physics.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-04 · cmm_closed_loop.py:60 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cmm_closed_loop.py:60 — Too many arguments in function definition (12 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 cmm_closed_loop.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-05 · cnc_api.py:93 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_api.py:93 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 cnc_api.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-06 · db.py:429 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] db.py:429 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 db.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-07 · db.py:584 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] db.py:584 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 db.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-08 · db.py:623 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] db.py:623 — Too many arguments in function definition (8 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 db.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-09 · decompose.py:351 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] decompose.py:351 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 decompose.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-10 · distributed/core.py:335 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] distributed/core.py:335 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 distributed/core.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-11 · distributed/core.py:524 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] distributed/core.py:524 — Too many arguments in function definition (9 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 distributed/core.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-12 · document_factory.py:205 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:205 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 document_factory.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-13 · document_factory.py:329 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:329 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 document_factory.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-14 · document_factory.py:387 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:387 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 document_factory.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-15 · domain_experts.py:264 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:264 — Too many arguments in function definition (19 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 domain_experts.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-16 · domain_experts.py:439 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:439 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 domain_experts.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-17 · events_log.py:17 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] events_log.py:17 — Too many arguments in function definition (8 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 events_log.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-18 · gateway/client.py:212 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:212 — Too many arguments in function definition (14 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/client.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-19 · gateway/client.py:375 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:375 — Too many arguments in function definition (19 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/client.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-20 · gateway/client.py:539 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:539 — Too many arguments in function definition (9 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/client.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-21 · gateway/client.py:637 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:637 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/client.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-22 · gateway/client.py:686 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:686 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/client.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-23 · gateway/client.py:735 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:735 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/client.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-24 · gateway/client.py:791 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:791 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/client.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-25 · gateway/prompts.py:57 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/prompts.py:57 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/prompts.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-26 · gateway/providers.py:44 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/providers.py:44 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/providers.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-27 · gateway/providers.py:76 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/providers.py:76 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/providers.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-28 · gateway/providers.py:206 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/providers.py:206 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/providers.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-29 · gateway/providers.py:270 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/providers.py:270 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/providers.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-30 · gateway/registry.py:151 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:151 — Too many arguments in function definition (13 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/registry.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-31 · gateway/registry.py:304 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:304 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 gateway/registry.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-32 · hallucination/verifier.py:392 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:392 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 hallucination/verifier.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-33 · hallucination/verifier.py:629 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:629 — Too many arguments in function definition (8 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 hallucination/verifier.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-34 · hallucination/verifier.py:674 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:674 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 hallucination/verifier.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-35 · mcp_connector.py:112 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] mcp_connector.py:112 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 mcp_connector.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-36 · mcp_connector.py:228 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] mcp_connector.py:228 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 mcp_connector.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-37 · memory_engine.py:90 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] memory_engine.py:90 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 memory_engine.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-38 · ml_ops/models.py:304 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] ml_ops/models.py:304 — Too many arguments in function definition (8 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 ml_ops/models.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-39 · ops.py:153 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] ops.py:153 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 ops.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-40 · orchestrator/pipeline.py:382 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/pipeline.py:382 — Too many arguments in function definition (13 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 orchestrator/pipeline.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-41 · orchestrator/state.py:213 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/state.py:213 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 orchestrator/state.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-42 · orchestrator/tools_registry.py:190 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/tools_registry.py:190 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 orchestrator/tools_registry.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-43 · ownership.py:72 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] ownership.py:72 — Too many arguments in function definition (9 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 ownership.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-44 · process_utils.py:27 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] process_utils.py:27 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 process_utils.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-45 · rag/store.py:224 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:224 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 rag/store.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-46 · rag/store.py:324 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:324 — Too many arguments in function definition (8 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 rag/store.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-47 · rag/store.py:448 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:448 — Too many arguments in function definition (9 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 rag/store.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-48 · rag/store.py:686 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:686 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 rag/store.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-49 · search_index.py:51 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] search_index.py:51 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 search_index.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-50 · search_index.py:71 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] search_index.py:71 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 search_index.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-51 · self_healing_runner.py:147 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] self_healing_runner.py:147 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 self_healing_runner.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-52 · studios/data_science.py:116 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] studios/data_science.py:116 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 studios/data_science.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-53 · studios/research.py:139 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] studios/research.py:139 — Too many arguments in function definition (7 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 studios/research.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-54 · user_profile.py:233 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:233 — Too many arguments in function definition (6 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 user_profile.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PRM-55 · user_profile.py:281 çok parametreli fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:281 — Too many arguments in function definition (8 > 5) (`PLR0913`).
- **Değişiklik:** Parametreleri veri sınıfına veya ayar nesnesine topla.
- **Kabul:** `ruff check --select PLR0913 user_profile.py` bu fonksiyonu raporlamaz; çağıranlar güncellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

## DAL · Python: çok dallı fonksiyonlar

#### DAL-01 · assistant.py:678 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:678 — Too many branches (33 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 assistant.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-02 · assistant.py:1151 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1151 — Too many branches (33 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 assistant.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-03 · automl_studio.py:38 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] automl_studio.py:38 — Too many branches (28 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 automl_studio.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-04 · automl_studio.py:205 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] automl_studio.py:205 — Too many branches (16 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 automl_studio.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-05 · cad_cam_physics.py:137 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cad_cam_physics.py:137 — Too many branches (29 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cad_cam_physics.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-06 · cnc_ballooning.py:135 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:135 — Too many branches (15 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-07 · cnc_ballooning.py:231 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:231 — Too many branches (13 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-08 · cnc_ballooning.py:552 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:552 — Too many branches (31 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-09 · cnc_ballooning.py:843 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:843 — Too many branches (13 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-10 · cnc_ballooning.py:941 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:941 — Too many branches (18 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-11 · cnc_ballooning.py:1145 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1145 — Too many branches (40 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-12 · cnc_ballooning.py:1446 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1446 — Too many branches (28 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-13 · cnc_ballooning.py:1674 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1674 — Too many branches (24 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 cnc_ballooning.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-14 · code_graph.py:281 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:281 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 code_graph.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-15 · code_graph.py:539 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:539 — Too many branches (15 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 code_graph.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-16 · code_graph.py:631 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:631 — Too many branches (34 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 code_graph.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-17 · code_graph.py:849 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:849 — Too many branches (18 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 code_graph.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-18 · code_graph.py:890 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:890 — Too many branches (15 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 code_graph.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-19 · db_doctor.py:47 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] db_doctor.py:47 — Too many branches (20 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 db_doctor.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-20 · decompose.py:214 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] decompose.py:214 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 decompose.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-21 · document_factory.py:205 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:205 — Too many branches (15 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 document_factory.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-22 · document_factory.py:329 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:329 — Too many branches (15 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 document_factory.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-23 · domain_experts.py:576 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:576 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 domain_experts.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-24 · erp_mes_scheduler.py:99 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] erp_mes_scheduler.py:99 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 erp_mes_scheduler.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-25 · erp_mes_scheduler.py:227 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] erp_mes_scheduler.py:227 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 erp_mes_scheduler.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-26 · extract.py:81 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] extract.py:81 — Too many branches (13 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 extract.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-27 · factory/deploy_verify.py:54 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] factory/deploy_verify.py:54 — Too many branches (16 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 factory/deploy_verify.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-28 · file_converter.py:145 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_converter.py:145 — Too many branches (26 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 file_converter.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-29 · file_converter.py:257 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_converter.py:257 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 file_converter.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-30 · file_inspector.py:94 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_inspector.py:94 — Too many branches (39 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 file_inspector.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-31 · gateway/client.py:375 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:375 — Too many branches (15 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 gateway/client.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-32 · hallucination/verifier.py:328 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:328 — Too many branches (22 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 hallucination/verifier.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-33 · hybrid_graph_rag.py:701 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:701 — Too many branches (20 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 hybrid_graph_rag.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-34 · multimodal_studio.py:95 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:95 — Too many branches (18 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 multimodal_studio.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-35 · orchestrator/contracts.py:163 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/contracts.py:163 — Too many branches (26 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 orchestrator/contracts.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-36 · rag/parsing.py:442 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/parsing.py:442 — Too many branches (15 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 rag/parsing.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-37 · rag/store.py:448 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:448 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 rag/store.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-38 · self_healing_runner.py:133 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] self_healing_runner.py:133 — Too many branches (21 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 self_healing_runner.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-39 · self_healing_runner.py:276 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] self_healing_runner.py:276 — Too many branches (13 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 self_healing_runner.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-40 · user_profile.py:431 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:431 — Too many branches (14 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 user_profile.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-41 · user_profile.py:584 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:584 — Too many branches (18 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 user_profile.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DAL-42 · user_profile.py:851 çok dallı fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:851 — Too many branches (13 > 12) (`PLR0912`).
- **Değişiklik:** Dalları tablo veya strateji nesnelerine indir.
- **Kabul:** `ruff check --select PLR0912 user_profile.py` bu fonksiyonu raporlamaz; her dal için test var.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## UZN · Python: çok uzun fonksiyonlar

#### UZN-01 · assistant.py:678 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:678 — Too many statements (133 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 assistant.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-02 · assistant.py:953 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:953 — Too many statements (69 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 assistant.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-03 · assistant.py:1151 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1151 — Too many statements (342 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 assistant.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-04 · automl_studio.py:38 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] automl_studio.py:38 — Too many statements (77 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 automl_studio.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-05 · automl_studio.py:205 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] automl_studio.py:205 — Too many statements (73 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 automl_studio.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-06 · cad_cam_physics.py:137 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cad_cam_physics.py:137 — Too many statements (107 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cad_cam_physics.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-07 · cnc_ballooning.py:135 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:135 — Too many statements (58 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cnc_ballooning.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-08 · cnc_ballooning.py:552 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:552 — Too many statements (108 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cnc_ballooning.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-09 · cnc_ballooning.py:941 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:941 — Too many statements (83 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cnc_ballooning.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-10 · cnc_ballooning.py:1145 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1145 — Too many statements (92 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cnc_ballooning.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-11 · cnc_ballooning.py:1446 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1446 — Too many statements (131 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cnc_ballooning.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-12 · cnc_ballooning.py:1674 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1674 — Too many statements (51 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cnc_ballooning.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-13 · cnc_ballooning.py:1780 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1780 — Too many statements (69 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 cnc_ballooning.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-14 · code_graph.py:631 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:631 — Too many statements (82 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 code_graph.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-15 · deep_research.py:136 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] deep_research.py:136 — Too many statements (142 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 deep_research.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-16 · document_factory.py:205 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:205 — Too many statements (86 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 document_factory.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-17 · document_factory.py:387 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:387 — Too many statements (54 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 document_factory.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-18 · erp_mes_scheduler.py:227 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] erp_mes_scheduler.py:227 — Too many statements (58 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 erp_mes_scheduler.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-19 · file_converter.py:145 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_converter.py:145 — Too many statements (87 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 file_converter.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-20 · file_inspector.py:94 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_inspector.py:94 — Too many statements (97 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 file_inspector.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-21 · gateway/client.py:375 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:375 — Too many statements (56 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 gateway/client.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-22 · multimodal_studio.py:95 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:95 — Too many statements (96 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 multimodal_studio.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-23 · orchestrator/contracts.py:163 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/contracts.py:163 — Too many statements (60 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 orchestrator/contracts.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-24 · rag/store.py:448 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:448 — Too many statements (58 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 rag/store.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-25 · studios/presentation.py:179 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] studios/presentation.py:179 — Too many statements (71 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 studios/presentation.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-26 · studios/research.py:139 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] studios/research.py:139 — Too many statements (58 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 studios/research.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### UZN-27 · user_profile.py:584 çok uzun fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:584 — Too many statements (61 > 50) (`PLR0915`).
- **Değişiklik:** Aşamalara böl, her aşama ayrı sınanır.
- **Kabul:** `ruff check --select PLR0915 user_profile.py` bu fonksiyonu raporlamaz.
- **Meta:** P2 · M · Bağ: - · Durum: açık

## SQL · Python: dinamik SQL dizeleri

#### SQL-01 · db.py:269 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] db.py:269 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 db.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-02 · db.py:276 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] db.py:276 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 db.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-03 · db_doctor.py:58 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] db_doctor.py:58 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 db_doctor.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-04 · db_doctor.py:68 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] db_doctor.py:68 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 db_doctor.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-05 · dbunify.py:28 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] dbunify.py:28 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 dbunify.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-06 · dbunify.py:54 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] dbunify.py:54 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 dbunify.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-07 · dbunify.py:55 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] dbunify.py:55 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 dbunify.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-08 · dbunify.py:56 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] dbunify.py:56 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 dbunify.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-09 · dbunify.py:62 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] dbunify.py:62 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 dbunify.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-10 · domain_experts.py:604 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:604 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 domain_experts.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-11 · domain_experts.py:613 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:613 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 domain_experts.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-12 · domain_experts.py:621 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:621 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 domain_experts.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-13 · domain_experts.py:638 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:638 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 domain_experts.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-14 · events_log.py:40 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] events_log.py:40 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 events_log.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-15 · migrate.py:124 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] migrate.py:124 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 migrate.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-16 · ownership.py:88 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] ownership.py:88 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 ownership.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-17 · ownership.py:104 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] ownership.py:104 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 ownership.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-18 · ownership.py:115 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] ownership.py:115 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 ownership.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-19 · ownership.py:121 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] ownership.py:121 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 ownership.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-20 · portability.py:48 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] portability.py:48 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 portability.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-21 · portability.py:52 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] portability.py:52 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 portability.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-22 · rag/store.py:483 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:483 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 rag/store.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-23 · rag/store.py:494 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:494 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 rag/store.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-24 · tool_executor.py:164 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] tool_executor.py:164 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 tool_executor.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-25 · vector_meta.py:33 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] vector_meta.py:33 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 vector_meta.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SQL-26 · vector_meta.py:43 dinamik SQL dizesi
- **Sorun:** [DOĞRULANDI: F201] vector_meta.py:43 — Possible SQL injection vector through string-based query construction (`S608`).
- **Değişiklik:** Tablo ve sütun adlarını beyaz listeyle doğrula, değerleri parametreyle geçir; sahip filtresi için `ownership.scoped_select` kullan.
- **Kabul:** `ruff check --select S608 vector_meta.py` bu satırı raporlamaz; kötü niyetli ad/değer testi sorguyu değiştirmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

## STA · Python: diğer statik analiz bulguları

#### STA-01 · document_factory.py:70 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:70 — Unused function argument: `has_file` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 document_factory.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-02 · gateway/fake_ollama.py:38 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] gateway/fake_ollama.py:38 — Unused function argument: `body` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 gateway/fake_ollama.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-03 · gateway/fake_ollama.py:70 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] gateway/fake_ollama.py:70 — Unused function argument: `body` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 gateway/fake_ollama.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-04 · hallucination/verifier.py:518 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:518 — Unused function argument: `domain` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 hallucination/verifier.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-05 · llm.py:13 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] llm.py:13 — Unused function argument: `num_ctx` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 llm.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-06 · memory_engine.py:264 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] memory_engine.py:264 — Unused function argument: `query` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 memory_engine.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-07 · orchestrator/tools_registry.py:301 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] orchestrator/tools_registry.py:301 — Unused function argument: `args` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 orchestrator/tools_registry.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-08 · perf_api.py:53 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] perf_api.py:53 — Unused function argument: `project_id` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 perf_api.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-09 · sandbox/runner.py:115 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:115 — Unused function argument: `timeout_s` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 sandbox/runner.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-10 · tasks_api.py:60 kullanılmayan argüman
- **Sorun:** [DOĞRULANDI: F201] tasks_api.py:60 — Unused function argument: `background_tasks` (`ARG001`).
- **Değişiklik:** Argümanı kaldır veya kullan; çağıranları güncelle.
- **Kabul:** `ruff check --select ARG001 tasks_api.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-11 · cad_cam_physics.py:691 yorum satırına alınmış kod
- **Sorun:** [DOĞRULANDI: F201] cad_cam_physics.py:691 — Found commented-out code (`ERA001`).
- **Değişiklik:** Kodu sil veya testlere taşı.
- **Kabul:** `ruff check --select ERA001 cad_cam_physics.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-12 · tasks_api.py:54 yorum satırına alınmış kod
- **Sorun:** [DOĞRULANDI: F201] tasks_api.py:54 — Found commented-out code (`ERA001`).
- **Değişiklik:** Kodu sil veya testlere taşı.
- **Kabul:** `ruff check --select ERA001 tasks_api.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-13 · tasks_api.py:116 yorum satırına alınmış kod
- **Sorun:** [DOĞRULANDI: F201] tasks_api.py:116 — Found commented-out code (`ERA001`).
- **Değişiklik:** Kodu sil veya testlere taşı.
- **Kabul:** `ruff check --select ERA001 tasks_api.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-14 · hybrid_graph_rag.py:667 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:667 — Using the global statement to update `_DEFAULT_RAG` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 hybrid_graph_rag.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-15 · maintenance.py:76 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] maintenance.py:76 — Using the global statement to update `_thread` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 maintenance.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-16 · multimodal_studio.py:796 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:796 — Using the global statement to update `_WHISPER_MODEL_CACHE` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 multimodal_studio.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-17 · preview_server.py:64 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] preview_server.py:64 — Using the global statement to update `_preview_started` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 preview_server.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-18 · preview_server.py:64 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] preview_server.py:64 — Using the global statement to update `_preview_started` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 preview_server.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-19 · scheduler.py:26 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] scheduler.py:26 — Using the global statement to update `_running` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 scheduler.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-20 · scheduler.py:44 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] scheduler.py:44 — Using the global statement to update `_dag_task` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 scheduler.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-21 · tasks_api.py:34 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] tasks_api.py:34 — Using the global statement to update `_lease_task_running` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 tasks_api.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-22 · tasks_api.py:49 global değişken ataması
- **Sorun:** [DOĞRULANDI: F201] tasks_api.py:49 — Using the global statement to update `_lease_task` is discouraged (`PLW0603`).
- **Değişiklik:** Durumu sınıfa veya modül nesnesine taşı.
- **Kabul:** `ruff check --select PLW0603 tasks_api.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-23 · hallucination/eval_runner.py:166 assert kullanımı
- **Sorun:** [DOĞRULANDI: F201] hallucination/eval_runner.py:166 — Use of `assert` detected (`S101`).
- **Değişiklik:** Çalışma zamanı denetimini açık istisnaya çevir (assert -O ile kalkar).
- **Kabul:** `ruff check --select S101 hallucination/eval_runner.py` bu satırı raporlamaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### STA-24 · hybrid_graph_rag.py:217 assert kullanımı
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:217 — Use of `assert` detected (`S101`).
- **Değişiklik:** Çalışma zamanı denetimini açık istisnaya çevir (assert -O ile kalkar).
- **Kabul:** `ruff check --select S101 hybrid_graph_rag.py` bu satırı raporlamaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### STA-25 · orchestrator/pipeline.py:202 assert kullanımı
- **Sorun:** [DOĞRULANDI: F201] orchestrator/pipeline.py:202 — Use of `assert` detected (`S101`).
- **Değişiklik:** Çalışma zamanı denetimini açık istisnaya çevir (assert -O ile kalkar).
- **Kabul:** `ruff check --select S101 orchestrator/pipeline.py` bu satırı raporlamaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### STA-26 · rag/parsing.py:155 assert kullanımı
- **Sorun:** [DOĞRULANDI: F201] rag/parsing.py:155 — Use of `assert` detected (`S101`).
- **Değişiklik:** Çalışma zamanı denetimini açık istisnaya çevir (assert -O ile kalkar).
- **Kabul:** `ruff check --select S101 rag/parsing.py` bu satırı raporlamaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### STA-27 · injection.py:50 sabit parola benzeri dize
- **Sorun:** [DOĞRULANDI: F201] injection.py:50 — Possible hardcoded password assigned to: "_SECRET_OBJECT" (`S105`).
- **Değişiklik:** Değeri ortam değişkeni/gizli depodan oku.
- **Kabul:** `ruff check --select S105 injection.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-28 · sandbox/runner.py:127 güvensiz geçici dosya yolu
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:127 — Probable insecure usage of temporary file or directory: "/tmp:rw,noexec,nosuid,size=64m" (`S108`).
- **Değişiklik:** `tempfile` kullan.
- **Kabul:** `ruff check --select S108 sandbox/runner.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-29 · gateway/client.py:877 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:877 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 gateway/client.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-30 · gateway/registry.py:251 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:251 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 gateway/registry.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-31 · gateway/registry.py:263 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:263 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 gateway/registry.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-32 · gateway/registry.py:299 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:299 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 gateway/registry.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-33 · hallucination/verifier.py:357 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:357 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 hallucination/verifier.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-34 · hallucination/verifier.py:379 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:379 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 hallucination/verifier.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-35 · preview_server.py:87 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] preview_server.py:87 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 preview_server.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-36 · rag/store.py:311 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:311 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 rag/store.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-37 · rag/web.py:357 try/except/pass
- **Sorun:** [DOĞRULANDI: F201] rag/web.py:357 — `try`-`except`-`pass` detected, consider logging the exception (`S110`).
- **Değişiklik:** Sessiz yutmayı kaldır; spesifik istisna ve günlük kaydı.
- **Kabul:** `ruff check --select S110 rag/web.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-38 · cluster_telemetry.py:48 güvenlik amaçlı olmayan rastgelelik
- **Sorun:** [DOĞRULANDI: F201] cluster_telemetry.py:48 — Standard pseudo-random generators are not suitable for cryptographic purposes (`S311`).
- **Değişiklik:** Güvenlik değeriyse `secrets` kullan; değilse `noqa` gerekçesi yaz.
- **Kabul:** `ruff check --select S311 cluster_telemetry.py` bu satırı raporlamaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### STA-39 · distributed/core.py:216 güvenlik amaçlı olmayan rastgelelik
- **Sorun:** [DOĞRULANDI: F201] distributed/core.py:216 — Standard pseudo-random generators are not suitable for cryptographic purposes (`S311`).
- **Değişiklik:** Güvenlik değeriyse `secrets` kullan; değilse `noqa` gerekçesi yaz.
- **Kabul:** `ruff check --select S311 distributed/core.py` bu satırı raporlamaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### STA-40 · selection.py:138 zayıf özet işlevi
- **Sorun:** [DOĞRULANDI: F201] selection.py:138 — Probable use of insecure hash functions in `hashlib`: `md5` (`S324`).
- **Değişiklik:** Güvenlik amaçlıysa SHA-256+; değilse `usedforsecurity=False` ve gerekçe.
- **Kabul:** `ruff check --select S324 selection.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-41 · selection.py:139 zayıf özet işlevi
- **Sorun:** [DOĞRULANDI: F201] selection.py:139 — Probable use of insecure hash functions in `hashlib`: `md5` (`S324`).
- **Değişiklik:** Güvenlik amaçlıysa SHA-256+; değilse `usedforsecurity=False` ve gerekçe.
- **Kabul:** `ruff check --select S324 selection.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-42 · file_inspector.py:165 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] file_inspector.py:165 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 file_inspector.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-43 · multimodal_studio.py:885 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:885 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 multimodal_studio.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-44 · process_utils.py:41 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] process_utils.py:41 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 process_utils.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-45 · sandbox/runner.py:45 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:45 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 sandbox/runner.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-46 · sandbox/runner.py:95 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:95 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 sandbox/runner.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-47 · sandbox/runner.py:169 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:169 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 sandbox/runner.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-48 · self_healing_runner.py:318 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] self_healing_runner.py:318 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 self_healing_runner.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-49 · studio_api.py:466 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] studio_api.py:466 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 studio_api.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-50 · workspace_builder.py:533 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] workspace_builder.py:533 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 workspace_builder.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-51 · workspace_builder.py:759 alt süreç çağrısı
- **Sorun:** [DOĞRULANDI: F201] workspace_builder.py:759 — `subprocess` call: check for execution of untrusted input (`S603`).
- **Değişiklik:** Girdileri doğrula, mutlak yol ve sabit argüman listesi kullan, zaman aşımı ekle.
- **Kabul:** `ruff check --select S603 workspace_builder.py` bu satırı raporlamaz veya gerekçeli `noqa` ve test ile belgelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-52 · file_inspector.py:165 kısmi yolla süreç başlatma
- **Sorun:** [DOĞRULANDI: F201] file_inspector.py:165 — Starting a process with a partial executable path (`S607`).
- **Değişiklik:** Çalıştırılabilir dosyayı `shutil.which` ile çöz ve mutlak yol kullan.
- **Kabul:** `ruff check --select S607 file_inspector.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-53 · multimodal_studio.py:886 kısmi yolla süreç başlatma
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:886 — Starting a process with a partial executable path (`S607`).
- **Değişiklik:** Çalıştırılabilir dosyayı `shutil.which` ile çöz ve mutlak yol kullan.
- **Kabul:** `ruff check --select S607 multimodal_studio.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-54 · sandbox/runner.py:46 kısmi yolla süreç başlatma
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:46 — Starting a process with a partial executable path (`S607`).
- **Değişiklik:** Çalıştırılabilir dosyayı `shutil.which` ile çöz ve mutlak yol kullan.
- **Kabul:** `ruff check --select S607 sandbox/runner.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-55 · sandbox/runner.py:63 kısmi yolla süreç başlatma
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:63 — Starting a process with a partial executable path (`S607`).
- **Değişiklik:** Çalıştırılabilir dosyayı `shutil.which` ile çöz ve mutlak yol kullan.
- **Kabul:** `ruff check --select S607 sandbox/runner.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-56 · sandbox/runner.py:96 kısmi yolla süreç başlatma
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:96 — Starting a process with a partial executable path (`S607`).
- **Değişiklik:** Çalıştırılabilir dosyayı `shutil.which` ile çöz ve mutlak yol kullan.
- **Kabul:** `ruff check --select S607 sandbox/runner.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-57 · studio_api.py:466 kısmi yolla süreç başlatma
- **Sorun:** [DOĞRULANDI: F201] studio_api.py:466 — Starting a process with a partial executable path (`S607`).
- **Değişiklik:** Çalıştırılabilir dosyayı `shutil.which` ile çöz ve mutlak yol kullan.
- **Kabul:** `ruff check --select S607 studio_api.py` bu satırı raporlamaz.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### STA-58 · erd.py:83 print çağrısı
- **Sorun:** [DOĞRULANDI: F201] erd.py:83 — `print` found (`T201`).
- **Değişiklik:** Günlük kaydına çevir.
- **Kabul:** `ruff check --select T201 erd.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### STA-59 · secret_store.py:202 print çağrısı
- **Sorun:** [DOĞRULANDI: F201] secret_store.py:202 — `print` found (`T201`).
- **Değişiklik:** Günlük kaydına çevir.
- **Kabul:** `ruff check --select T201 secret_store.py` bu satırı raporlamaz.
- **Meta:** P3 · S · Bağ: - · Durum: açık
