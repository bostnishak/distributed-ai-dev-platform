# Kanıt denetimi: testte adı geçmeyen maddeler

`plan_tool` her `done` maddenin test dosyasının ve commit'inin var olduğunu doğrular. Aşağıdaki 150 maddenin kanıt testlerinde madde kimliği geçmez; yani madde, dolaylı olarak (toplu bir senaryo testiyle) kapsanıyor. Bu maddeler 'uygulandı, madde bazında ayrıştırılmadı' sayılmalıdır. Madde kimliğini taşıyan test eklendikçe satır bu listeden düşer.

| Madde | Kanıt testleri |
|---|---|
| DEF-03 | master/tests/test_full_implementation_plan.py, master/tests/test_def_foundation_parca1.py |
| DEF-04 | master/tests/test_ops.py |
| DEF-05 | master/tests/test_gateway_orchestrator_modes.py |
| DEF-06 | master/tests/test_studios_parca4.py |
| DEF-07 | master/tests/test_rag_hallucination_ml.py |
| DEF-08 | master/tests/test_gateway_orchestrator_modes.py |
| DEF-09 | master/tests/test_gateway_orchestrator_modes.py |
| DEF-10 | master/tests/test_gateway_orchestrator_modes.py |
| DEF-12 | master/tests/test_data_layer.py |
| DEF-16 | master/tests/test_distributed_and_ux.py |
| DEF-17 | master/tests/test_distributed_and_ux.py |
| DEF-18 | agent/tests/test_agent.py |
| SEC-03 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-04 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-05 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-06 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-07 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-08 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-09 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-10 | master/tests/test_access_control.py, master/tests/test_security_matrix.py |
| SEC-11 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-12 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-13 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-14 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-15 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-17 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-18 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-19 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-20 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-21 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-23 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| SEC-24 | master/tests/test_security_matrix.py, master/tests/test_access_control.py |
| GW-05 | master/tests/test_gateway_orchestrator_modes.py |
| GW-06 | master/tests/test_gateway_orchestrator_modes.py |
| GW-07 | master/tests/test_gateway_orchestrator_modes.py |
| GW-08 | master/tests/test_gateway_orchestrator_modes.py |
| GW-09 | master/tests/test_gateway_orchestrator_modes.py |
| GW-10 | master/tests/test_gateway_orchestrator_modes.py |
| GW-16 | master/tests/test_gateway_orchestrator_modes.py |
| GW-17 | master/tests/test_gateway_orchestrator_modes.py |
| GW-18 | master/tests/test_gateway_orchestrator_modes.py |
| GW-19 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-02 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-03 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-04 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-05 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-06 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-07 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-08 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-14 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-17 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-18 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-19 | master/tests/test_gateway_orchestrator_modes.py |
| ORC-20 | master/tests/test_gateway_orchestrator_modes.py |
| RAG-06 | master/tests/test_rag_hallucination_ml.py |
| RAG-09 | master/tests/test_rag_hallucination_ml.py |
| RAG-14 | master/tests/test_rag_hallucination_ml.py |
| RAG-27 | master/tests/test_rag_hallucination_ml.py |
| RAG-29 | master/tests/test_rag_hallucination_ml.py |
| HAL-12 | master/tests/test_rag_hallucination_ml.py |
| HAL-20 | master/tests/test_rag_hallucination_ml.py |
| ML-05 | master/tests/test_rag_hallucination_ml.py |
| ML-06 | master/tests/test_rag_hallucination_ml.py |
| RES-02 | master/tests/test_studios_parca4.py |
| RES-03 | master/tests/test_studios_parca4.py |
| RES-04 | master/tests/test_studios_parca4.py |
| RES-05 | master/tests/test_studios_parca4.py |
| RES-08 | master/tests/test_studios_parca4.py |
| RES-09 | master/tests/test_studios_parca4.py |
| RES-10 | master/tests/test_studios_parca4.py |
| PPT-04 | master/tests/test_studios_parca4.py |
| PPT-05 | master/tests/test_studios_parca4.py |
| PPT-06 | master/tests/test_studios_parca4.py |
| PPT-07 | master/tests/test_studios_parca4.py |
| DOC-04 | master/tests/test_studios_parca4.py |
| DOC-07 | master/tests/test_studios_parca4.py |
| DOC-09 | master/tests/test_studios_parca4.py |
| MM-04 | master/tests/test_studios_parca4.py |
| MM-07 | master/tests/test_studios_parca4.py |
| MM-12 | master/tests/test_studios_parca4.py |
| IDE-05 | master/tests/test_factory_games_domains.py |
| IDE-06 | master/tests/test_factory_games_domains.py |
| IDE-07 | master/tests/test_factory_games_domains.py |
| IDE-08 | master/tests/test_factory_games_domains.py |
| IDE-09 | master/tests/test_factory_games_domains.py |
| IDE-10 | master/tests/test_factory_games_domains.py |
| IDE-12 | master/tests/test_factory_games_domains.py |
| IDE-13 | master/tests/test_factory_games_domains.py |
| IDE-14 | master/tests/test_factory_games_domains.py |
| IDE-17 | master/tests/test_factory_games_domains.py |
| IDE-19 | master/tests/test_factory_games_domains.py |
| IDE-20 | master/tests/test_factory_games_domains.py |
| IDE-22 | master/tests/test_factory_games_domains.py |
| IDE-23 | master/tests/test_factory_games_domains.py |
| GAME-02 | master/tests/test_factory_games_domains.py |
| GAME-03 | master/tests/test_factory_games_domains.py |
| GAME-04 | master/tests/test_factory_games_domains.py |
| GAME-07 | master/tests/test_factory_games_domains.py |
| GAME-09 | master/tests/test_factory_games_domains.py |
| DOM-07 | master/tests/test_factory_games_domains.py |
| DOM-08 | master/tests/test_factory_games_domains.py |
| DOM-10 | master/tests/test_factory_games_domains.py |
| DOM-11 | master/tests/test_factory_games_domains.py |
| DIST-14 | master/tests/test_distributed_and_ux.py |
| DIST-16 | master/tests/test_distributed_and_ux.py |
| DIST-20 | master/tests/test_distributed_and_ux.py |
| DIST-21 | master/tests/test_distributed_and_ux.py |
| UX-03 | master/tests/test_distributed_and_ux.py |
| UX-04 | master/tests/test_distributed_and_ux.py |
| UX-05 | master/tests/test_distributed_and_ux.py |
| UX-09 | master/tests/test_distributed_and_ux.py |
| UX-10 | master/tests/test_distributed_and_ux.py |
| UX-13 | master/tests/test_distributed_and_ux.py |
| UX-14 | master/tests/test_distributed_and_ux.py |
| UX-15 | master/tests/test_distributed_and_ux.py |
| UX-18 | master/tests/test_distributed_and_ux.py |
| UX-19 | master/tests/test_distributed_and_ux.py |
| UX-20 | master/tests/test_distributed_and_ux.py |
| UX-22 | master/tests/test_distributed_and_ux.py |
| UX-23 | master/tests/test_distributed_and_ux.py |
| UX-26 | master/tests/test_ux_panels_backend.py, master/tests/test_security_matrix.py |
| UX-27 | master/tests/test_distributed_and_ux.py |
| DAT-02 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-03 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-05 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-06 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-07 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-08 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-09 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-10 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-11 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-12 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-13 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-14 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| DAT-15 | master/tests/test_data_layer.py, master/tests/test_data_services.py |
| OPS-02 | master/tests/test_ops.py |
| OPS-03 | master/tests/test_ops.py |
| OPS-04 | master/tests/test_ops_and_proc_parca7.py |
| OPS-05 | master/tests/test_ops_and_proc_parca7.py |
| OPS-07 | master/tests/test_ops_and_proc_parca7.py |
| OPS-08 | master/tests/test_ops_and_proc_parca7.py |
| OPS-09 | master/tests/test_ops_and_proc_parca7.py |
| OPS-11 | master/tests/test_ops.py |
| OPS-18 | master/tests/test_ops.py |
| OPS-19 | master/tests/test_ops.py |
| OPS-23 | master/tests/test_ops_and_proc_parca7.py |
| PROC-04 | master/tests/test_ops_and_proc_parca7.py |
| PROC-05 | master/tests/test_ops_and_proc_parca7.py |
| PROC-06 | master/tests/test_ops_and_proc_parca7.py |
| PROC-10 | master/tests/test_ops_and_proc_parca7.py |
