# Parça 4 — Python statik analiz bulguları (1)

## BLE · Python: kapsamsız except

#### BLE-01 · access_control.py:25 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] access_control.py:25 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 access_control.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-02 · access_control.py:48 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] access_control.py:48 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 access_control.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-03 · assistant.py:374 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:374 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-04 · assistant.py:769 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:769 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-05 · assistant.py:788 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:788 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-06 · assistant.py:796 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:796 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-07 · assistant.py:818 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:818 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-08 · assistant.py:1012 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1012 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-09 · assistant.py:1265 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1265 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-10 · assistant.py:1322 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1322 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-11 · assistant.py:1360 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1360 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-12 · assistant.py:1395 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1395 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-13 · assistant.py:1411 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1411 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-14 · assistant.py:1499 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1499 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-15 · assistant.py:1513 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1513 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-16 · assistant.py:1535 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1535 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-17 · assistant.py:1563 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1563 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-18 · assistant.py:1621 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1621 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-19 · assistant.py:1678 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1678 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-20 · assistant.py:1738 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1738 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 assistant.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-21 · auth/service.py:90 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] auth/service.py:90 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 auth/service.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-22 · auth/service.py:99 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] auth/service.py:99 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 auth/service.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-23 · benchmarks.py:387 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] benchmarks.py:387 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 benchmarks.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-24 · benchmarks.py:399 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] benchmarks.py:399 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 benchmarks.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-25 · cluster_telemetry.py:70 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] cluster_telemetry.py:70 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 cluster_telemetry.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-26 · cluster_telemetry.py:217 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] cluster_telemetry.py:217 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 cluster_telemetry.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-27 · cluster_telemetry.py:299 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] cluster_telemetry.py:299 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 cluster_telemetry.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-28 · cnc_api.py:77 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] cnc_api.py:77 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 cnc_api.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-29 · cnc_ballooning.py:817 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:817 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 cnc_ballooning.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-30 · cnc_ballooning.py:895 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:895 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 cnc_ballooning.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-31 · cnc_ballooning.py:1135 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1135 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 cnc_ballooning.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-32 · code_graph.py:217 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:217 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 code_graph.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-33 · company_rag.py:44 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] company_rag.py:44 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 company_rag.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-34 · deep_research.py:388 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] deep_research.py:388 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 deep_research.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-35 · distributed/api.py:63 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] distributed/api.py:63 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 distributed/api.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-36 · distributed/core.py:416 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] distributed/core.py:416 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 distributed/core.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-37 · document_factory.py:157 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:157 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 document_factory.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-38 · enterprise_security_mcp.py:115 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] enterprise_security_mcp.py:115 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 enterprise_security_mcp.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-39 · error_tracker.py:36 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] error_tracker.py:36 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 error_tracker.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-40 · extract.py:44 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] extract.py:44 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 extract.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-41 · extract.py:113 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] extract.py:113 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 extract.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-42 · gateway/client.py:511 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:511 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 gateway/client.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-43 · gateway/client.py:842 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:842 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 gateway/client.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-44 · gateway/client.py:877 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:877 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 gateway/client.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-45 · gateway/registry.py:251 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:251 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 gateway/registry.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-46 · gateway/registry.py:263 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:263 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 gateway/registry.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-47 · gateway/registry.py:299 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] gateway/registry.py:299 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 gateway/registry.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-48 · hallucination/verifier.py:357 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:357 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 hallucination/verifier.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-49 · hallucination/verifier.py:379 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:379 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 hallucination/verifier.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-50 · hybrid_graph_rag.py:188 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:188 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 hybrid_graph_rag.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-51 · hybrid_graph_rag.py:298 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:298 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 hybrid_graph_rag.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-52 · llmops_pipeline.py:150 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] llmops_pipeline.py:150 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 llmops_pipeline.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-53 · log_sanitizer.py:86 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] log_sanitizer.py:86 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 log_sanitizer.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-54 · logging_setup.py:78 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] logging_setup.py:78 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 logging_setup.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-55 · mcp_connector.py:290 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] mcp_connector.py:290 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 mcp_connector.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-56 · multimodal_studio.py:69 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:69 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-57 · multimodal_studio.py:514 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:514 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-58 · multimodal_studio.py:732 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:732 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-59 · multimodal_studio.py:764 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:764 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-60 · multimodal_studio.py:828 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:828 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-61 · multimodal_studio.py:848 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:848 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-62 · multimodal_studio.py:870 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:870 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-63 · multimodal_studio.py:895 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:895 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 multimodal_studio.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-64 · orchestrator/planner.py:217 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] orchestrator/planner.py:217 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 orchestrator/planner.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-65 · orchestrator/planner.py:239 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] orchestrator/planner.py:239 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 orchestrator/planner.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-66 · orchestrator/planner.py:271 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] orchestrator/planner.py:271 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 orchestrator/planner.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-67 · orchestrator/tools_registry.py:170 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] orchestrator/tools_registry.py:170 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 orchestrator/tools_registry.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-68 · preview_server.py:87 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] preview_server.py:87 — Do not catch blind exception: `BaseException` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 preview_server.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-69 · rag/parsing.py:114 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] rag/parsing.py:114 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 rag/parsing.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-70 · rag/store.py:311 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:311 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 rag/store.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-71 · rag/web.py:257 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] rag/web.py:257 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 rag/web.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-72 · rag/web.py:317 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] rag/web.py:317 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 rag/web.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-73 · rag/web.py:357 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] rag/web.py:357 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 rag/web.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-74 · readiness.py:40 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] readiness.py:40 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 readiness.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-75 · readiness.py:63 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] readiness.py:63 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 readiness.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-76 · readiness.py:86 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] readiness.py:86 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 readiness.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-77 · sandbox/runner.py:53 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:53 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 sandbox/runner.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-78 · sandbox/runner.py:74 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:74 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 sandbox/runner.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-79 · sandbox/runner.py:193 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] sandbox/runner.py:193 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 sandbox/runner.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-80 · scheduler.py:35 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] scheduler.py:35 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 scheduler.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-81 · secret_store.py:45 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] secret_store.py:45 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 secret_store.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-82 · secret_store.py:69 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] secret_store.py:69 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 secret_store.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-83 · secret_store.py:186 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] secret_store.py:186 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 secret_store.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-84 · security_middleware.py:56 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] security_middleware.py:56 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 security_middleware.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-85 · self_healing_runner.py:336 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] self_healing_runner.py:336 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 self_healing_runner.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-86 · studio_api.py:66 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] studio_api.py:66 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 studio_api.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-87 · studio_api.py:89 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] studio_api.py:89 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 studio_api.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-88 · studios/multimedia.py:250 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] studios/multimedia.py:250 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 studios/multimedia.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-89 · tasks_api.py:43 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] tasks_api.py:43 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 tasks_api.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-90 · user_profile.py:503 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:503 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 user_profile.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-91 · user_profile.py:913 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:913 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 user_profile.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-92 · ux_api.py:68 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] ux_api.py:68 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 ux_api.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-93 · workspace_builder.py:169 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] workspace_builder.py:169 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 workspace_builder.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### BLE-94 · workspace_builder.py:629 kapsamsız except
- **Sorun:** [DOĞRULANDI: F201] workspace_builder.py:629 — Do not catch blind exception: `Exception` (`BLE001`).
- **Değişiklik:** Beklenen istisna türüne daralt; kullanıcıyı etkiliyorsa uyarı olayı gönder, aksi halde `log.warning(..., exc_info=True)` yaz.
- **Kabul:** `ruff check --select BLE001 workspace_builder.py` bu satırı raporlamaz ve hata enjekte eden test log satırını doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

## KMP · Python: karmaşık fonksiyonlar

#### KMP-01 · assistant.py:522 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:522 — `_try_extended_calculation` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 assistant.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-02 · assistant.py:678 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:678 — `_prepare_chat_request` is too complex (30 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 assistant.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-03 · assistant.py:917 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:917 — `get_assistant_media` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 assistant.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-04 · assistant.py:953 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:953 — `_tracked_stream` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 assistant.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-05 · assistant.py:1151 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] assistant.py:1151 — `_chat_stream_impl` is too complex (102 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 assistant.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-06 · automl_studio.py:38 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] automl_studio.py:38 — `profile_dataset` is too complex (27 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 automl_studio.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-07 · automl_studio.py:205 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] automl_studio.py:205 — `train_and_forecast` is too complex (16 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 automl_studio.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-08 · backup_manager.py:95 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] backup_manager.py:95 — `restore_enterprise_backup_zip` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 backup_manager.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-09 · cad_cam_physics.py:137 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cad_cam_physics.py:137 — `analyze_3d_cad_file` is too complex (29 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cad_cam_physics.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-10 · cnc_ballooning.py:135 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:135 — `enrich_cnc_engineering_fields` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-11 · cnc_ballooning.py:231 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:231 — `build_cnc_manufacturing_plan` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-12 · cnc_ballooning.py:552 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:552 — `parse_cnc_dimension` is too complex (29 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-13 · cnc_ballooning.py:843 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:843 — `_analyze_image_with_vlm` is too complex (14 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-14 · cnc_ballooning.py:941 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:941 — `_extract_dxf_balloons` is too complex (19 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-15 · cnc_ballooning.py:1145 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1145 — `process_drawing` is too complex (34 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-16 · cnc_ballooning.py:1446 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1446 — `export_excel_report` is too complex (27 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-17 · cnc_ballooning.py:1674 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] cnc_ballooning.py:1674 — `export_word_report` is too complex (25 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 cnc_ballooning.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-18 · code_graph.py:281 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:281 — `parse_python_file` is too complex (15 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 code_graph.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-19 · code_graph.py:391 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:391 — `parse_js_ts_file` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 code_graph.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-20 · code_graph.py:539 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:539 — `_resolve_python_import` is too complex (16 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 code_graph.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-21 · code_graph.py:631 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:631 — `build_workspace_code_graph` is too complex (32 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 code_graph.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-22 · code_graph.py:849 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:849 — `_format_symbol_contract` is too complex (19 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 code_graph.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-23 · code_graph.py:890 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] code_graph.py:890 — `get_file_context_contract` is too complex (16 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 code_graph.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-24 · conflict_detector.py:18 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] conflict_detector.py:18 — `detect_and_save` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 conflict_detector.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-25 · db_doctor.py:47 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] db_doctor.py:47 — `diagnose` is too complex (21 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 db_doctor.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-26 · decompose.py:214 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] decompose.py:214 — `merge_specs` is too complex (15 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 decompose.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-27 · decompose.py:346 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] decompose.py:346 — `build_task_plan` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 decompose.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-28 · document_factory.py:205 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:205 — `_build_xlsx` is too complex (16 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 document_factory.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-29 · document_factory.py:329 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:329 — `_build_docx` is too complex (16 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 document_factory.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-30 · document_factory.py:387 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] document_factory.py:387 — `_build_pdf` is too complex (17 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 document_factory.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-31 · domain_experts.py:172 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:172 — `analyze_legal_contract` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 domain_experts.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-32 · domain_experts.py:576 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] domain_experts.py:576 — `_translate_natural_query_to_sql` is too complex (15 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 domain_experts.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-33 · domains/engines.py:270 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] domains/engines.py:270 — `validate_gcode_safety` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 domains/engines.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-34 · erp_mes_scheduler.py:14 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] erp_mes_scheduler.py:14 — `optimize_1d_bar_nesting` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 erp_mes_scheduler.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-35 · erp_mes_scheduler.py:99 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] erp_mes_scheduler.py:99 — `optimize_2d_sheet_nesting` is too complex (15 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 erp_mes_scheduler.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-36 · erp_mes_scheduler.py:227 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] erp_mes_scheduler.py:227 — `schedule_cnc_job_shop` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 erp_mes_scheduler.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-37 · extract.py:81 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] extract.py:81 — `extract_zip_text` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 extract.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-38 · factory/deploy_verify.py:54 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] factory/deploy_verify.py:54 — `verify_web_workspace_ui` is too complex (17 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 factory/deploy_verify.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-39 · file_converter.py:99 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_converter.py:99 — `detect_conversion_or_archive_action` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 file_converter.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-40 · file_converter.py:145 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_converter.py:145 — `extract_structured_content` is too complex (25 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 file_converter.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-41 · file_converter.py:257 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_converter.py:257 — `convert_uploaded_file` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 file_converter.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-42 · file_inspector.py:94 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] file_inspector.py:94 — `inspect_uploaded_file` is too complex (40 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 file_inspector.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-43 · games/studio.py:191 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] games/studio.py:191 — `run_automated_bot_playtest` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 games/studio.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-44 · gateway/client.py:375 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/client.py:375 — `chat` is too complex (15 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 gateway/client.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-45 · gateway/fake_ollama.py:12 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] gateway/fake_ollama.py:12 — `create_fake_ollama_app` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 gateway/fake_ollama.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-46 · hallucination/verifier.py:241 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:241 — `verify_numbers_and_tables` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 hallucination/verifier.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-47 · hallucination/verifier.py:328 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hallucination/verifier.py:328 — `audit_python_code_apis` is too complex (20 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 hallucination/verifier.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-48 · hybrid_graph_rag.py:357 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:357 — `search` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 hybrid_graph_rag.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-49 · hybrid_graph_rag.py:446 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:446 — `extract_and_store_triples` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 hybrid_graph_rag.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-50 · hybrid_graph_rag.py:531 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:531 — `query_knowledge_subgraph` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 hybrid_graph_rag.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-51 · hybrid_graph_rag.py:701 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] hybrid_graph_rag.py:701 — `verify_citations` is too complex (19 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 hybrid_graph_rag.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-52 · multimodal_studio.py:95 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:95 — `process_and_edit_image` is too complex (19 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 multimodal_studio.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-53 · multimodal_studio.py:443 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:443 — `_design_spec_from_llm` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 multimodal_studio.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-54 · multimodal_studio.py:804 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] multimodal_studio.py:804 — `_decode_audio_to_float32_16k` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 multimodal_studio.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-55 · ops.py:52 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] ops.py:52 — `__call__` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 ops.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-56 · orchestrator/contracts.py:163 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/contracts.py:163 — `validate_contract` is too complex (27 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 orchestrator/contracts.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-57 · orchestrator/pipeline.py:187 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/pipeline.py:187 — `stage_execute` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 orchestrator/pipeline.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-58 · orchestrator/planner.py:175 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] orchestrator/planner.py:175 — `execute` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 orchestrator/planner.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-59 · portability.py:69 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] portability.py:69 — `import_user` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 portability.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-60 · rag/parsing.py:322 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/parsing.py:322 — `_split_atomic_blocks` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 rag/parsing.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-61 · rag/parsing.py:367 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/parsing.py:367 — `chunk_document` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 rag/parsing.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-62 · rag/parsing.py:442 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/parsing.py:442 — `query_table_numeric` is too complex (15 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 rag/parsing.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-63 · rag/store.py:448 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] rag/store.py:448 — `search` is too complex (15 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 rag/store.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-64 · safe_archive.py:106 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] safe_archive.py:106 — `scan_active_content` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 safe_archive.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-65 · self_healing_runner.py:133 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] self_healing_runner.py:133 — `scan_code_security` is too complex (24 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 self_healing_runner.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-66 · self_healing_runner.py:276 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] self_healing_runner.py:276 — `run_workspace_smoke_check` is too complex (14 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 self_healing_runner.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-67 · studios/research.py:139 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] studios/research.py:139 — `run_deep_research` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 studios/research.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-68 · tasks_api.py:132 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] tasks_api.py:132 — `submit_result` is too complex (11 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 tasks_api.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-69 · user_profile.py:135 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:135 — `sanitize_settings` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 user_profile.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-70 · user_profile.py:431 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:431 — `cross_chat_snippets` is too complex (14 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 user_profile.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-71 · user_profile.py:584 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:584 — `cross_chat_context_block` is too complex (19 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 user_profile.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-72 · user_profile.py:851 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] user_profile.py:851 — `wipe_data` is too complex (13 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 user_profile.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-73 · validation.py:11 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] validation.py:11 — `validate_result` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 validation.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-74 · validation.py:50 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] validation.py:50 — `extract_files_from_output` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 validation.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### KMP-75 · workspace_builder.py:492 karmaşık fonksiyon
- **Sorun:** [DOĞRULANDI: F201] workspace_builder.py:492 — `_build_exe_blocking` is too complex (12 > 10) (`C901`).
- **Değişiklik:** Fonksiyonu adımlara böl (karmaşıklık ≤ 10), davranışı koruyan testleri önce yaz.
- **Kabul:** `ruff check --select C901 workspace_builder.py` bu fonksiyonu raporlamaz; mevcut testler geçer.
- **Meta:** P2 · M · Bağ: - · Durum: açık
