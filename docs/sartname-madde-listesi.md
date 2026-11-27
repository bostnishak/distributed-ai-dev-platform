# v1-v4 şartnameleri: madde madde durum

**canlı** = gerçek modellerle denendi ve geçti. **test** = otomatik testle geçti. **kısmi** = bir bölümü var.
**yok** = henüz yazılmadı. **dışarıda** = senin onayınla kapsam dışı. **teknik engel** = bu araçlarla yapılamıyor.

Bu dosya `scripts/spec_matrix.tsv` dosyasından üretilir: `python scripts/spec_matrix.py`

| Sürüm | canlı | test | kısmi | yok | dışarıda | teknik engel | Toplam |
|---|---|---|---|---|---|---|---|
| v1 | 17 | 13 | 2 | 0 | 0 | 0 | 32 |
| v2 | 9 | 13 | 13 | 6 | 2 | 1 | 44 |
| v3 | 9 | 16 | 12 | 6 | 5 | 2 | 50 |
| v4 | 16 | 11 | 5 | 1 | 0 | 0 | 33 |
| **Hepsi** | 51 | 53 | 32 | 13 | 7 | 3 | 159 |

## v1

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 1 Yasalar | Sahte veri ve yer tutucu yasağı (statik tarama + tarayıcı kapısı) | canlı | workspace_smoke, jsdom_probe |
| 1 Yasalar | Uydurma paket, dosya yolu, model adı engeli | canlı | package_check gerçek PyPI ile denendi |
| 1 Yasalar | Eleştirel, onaylayıcı olmayan akıl yürütme | test | prompts/agent_architect.md |
| 1 Yasalar | Renk, ölçü, etiket sadakati (spec.json) | canlı | spec_contract |
| 1 Yasalar | Ham kaynak saflığı (vurgulayıcı artığı yok) | canlı | pure_source |
| 2 Ajanlar | IntakeAgent, şemalı spec | test | agent_contracts |
| 2 Ajanlar | ArchitectAgent, plan ve risk denetimi | test | agent_contracts |
| 2 Ajanlar | Frontend ajanı, nokta atışı yama | test | patch_edit |
| 2 Ajanlar | Backend ajanı, gerçek kalıcılık | canlı | workspace_batches |
| 2 Ajanlar | Akış şeması ajanı, doğrulanmış diyagram | canlı | flowchart_studio |
| 2 Ajanlar | PDF üretimi | canlı | document_factory |
| 2 Ajanlar | Görsel üretimi, motoru bildirme | canlı | multimodal_studio |
| 2 QA | HTML, JS, Python, JSON sözdizimi denetimi | test | workspace_checks |
| 2 QA | Yer tutucu tarayıcı | test | workspace_smoke |
| 2 QA | Spec uyum denetçisi | test | spec_contract |
| 2 QA | Tarayıcıda davranış testi | canlı | jsdom_probe, workspace_behavior |
| 2 QA | API'yi gerçek isteklerle sınama | canlı | api_probe |
| 2 QA | PDF ve görsel bütünlük denetimi | test | office_verify, post_checks |
| 2 QA | Sınırlı onarım döngüsü, dürüst başarısızlık bildirimi | canlı | workspace_builder |
| 3 Ollama | Kurulu modelleri keşfetme ve role göre seçim, yedek model | test | gateway/registry |
| 3 Ollama | Role göre sıcaklık ve şemalı çıktı | test | gateway/client_helpers |
| 3 Ollama | Dosya dosya parçalı üretim | canlı | workspace_batches |
| 3 Ollama | Ajan bazında TTFT ve token/sn göstergesi | kısmi | run_trace aşama süresi tutuyor; TTFT arayüzde yok |
| 4 Bellek | Son turlar ve takip isteği birleştirme | canlı | followup |
| 4 Bellek | Proje durumu, sürüm anlık görüntüsü | test | workspace_builder_ops |
| 4 Bellek | Uzun süreli tercih belleği | test | memory_engine |
| 4 Bellek | Yıkıcı olmayan yineleme | canlı | revise_chat, tier0_edit |
| 5 IDE | Yalıtılmış çalışma alanı, yol kaçışı koruması | test | workspace_builder_ops |
| 5 IDE | Dosya gezgini, editör, diff, ZIP | canlı | diff artık bir önceki sürümle |
| 5 IDE | Korumalı önizleme ve hata köprüsü | kısmi | ide_error_bridge yalnız Node ile denendi |
| 5 IDE | API test konsolu sekmesi | canlı | workspace_inspect.py; gerçek Chromium'da denendi |
| 6 Teslim | Uçtan uca testler ve çalışma kılavuzu | canlı | scripts/e2e_stress.py |

## v2

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 2.1 | Sabit önek önce istem düzeni | kısmi | bazı istemlerde |
| 2.1 | keep_alive, num_ctx boyutlama | test | gateway/registry |
| 2.1 | Model yakınlığına göre görev gruplama | kısmi | tek GPU kilidi var; DAG gruplama yok |
| 2.2 | Tier 0 modelsiz düzenleme | canlı | tier0_edit |
| 2.2 | Karmaşıklığa göre model basamağı | test | complexity_governor |
| 2.2 | Logprob/entropi ile yükseltme | teknik engel | Ollama yanıtında güvenilir logprob kullanılmıyor |
| 2.3 | Paralel DAG yürütücü, spekülatif ön hazırlık | yok | 8 GB kartta paralel üretim hızlandırmaz; doğrulama adımları paralel yapılabilir |
| 2.3 | Yalnız etkilenen testleri koşma | test | repo_map.affected_tests; sohbet revizyonunda |
| 2.4 | AST çapalı yama, tam yazıma geri düşme | test | patch_edit |
| 2.4 | L1 birebir önbellek | yok |  |
| 2.4 | L2 anlamsal, L3 bileşen önbelleği | yok |  |
| 3.1 | Yörünge toplama, sır temizleme | test | run_trace |
| 3.1 | Tercih çiftleri (başarısız/onarılmış) | kısmi | training_pack yalnız başarılı kayıtları veriyor |
| 3.2 | Yerel LoRA/DPO/GRPO eğitimi | dışarıda | bellek ve veri yetersiz; yalnız betik |
| 3.2 | GGUF içe aktarma ve gölge değerlendirme kapısı | kısmi | import-gguf var, gerçek GGUF ile denenmedi |
| 3.3 | Doğrulanmış beceri kütüphanesi | test | skill_library |
| 3.3 | Otomatik istem optimizasyonu | yok |  |
| 4.1 | Hipotez temelli nedensel hata ayıklama + regresyon testi | kısmi | causal_debug.py canlıda zincirdeki 3 hatanın 2'sini çözdü; regresyon testi üretmiyor |
| 4.2 | En iyi N aday değerlendirme | kısmi | konsey; başarısız onarımda ikinci modele yükseltme |
| 4.3 | Doğrulanmış/çıkarım/varsayım defteri | kısmi | Mimar ajanı varsayımları bildiriyor; her ajanda defter yok |
| 4.4 | API fuzz ve sınır testi | canlı | api_probe; Docker kum havuzunda denendi |
| 4.4 | Arayüz kaos, erişilebilirlik, üç ekran genişliği | kısmi | üç genişlik, adsız denetim, kontrast, taşma; kaos tıklaması yok |
| 4.4 | Uydurma paket (slopsquatting) denetimi | canlı | package_check |
| 5.1 | Depo haritası | canlı | repo_map.py (AST/regex + PageRank; tree-sitter değil); düzenlemede kullanılıyor, birim testli |
| 5.2 | Melez kod araması (graf+BM25+gömme) | kısmi | hybrid_graph_rag belge için; kod için yok |
| 5.2 | Etki alanı (blast radius) analizi | test | repo_map.dependents_note |
| 5.3 | Anlık statik tanılama (ruff, node --check) | canlı | code_audit.diagnostics (ruff, node --check), üretim sonunda |
| 5.3 | LSP sunucuları | yok |  |
| 6.1 | Yalıtılmış çalıştırma (ağsız Docker, kaynak sınırı) | test | workspace_docker |
| 6.1 | gVisor/Firecracker | dışarıda | Windows'ta yok |
| 6.2 | Güvenilmeyen veri ayrımı | canlı | untrusted |
| 6.2 | Eylem yetki politikası kapısı | test | policy.py; MCP ve araştırmaya bağlı |
| 6.3 | Sır tarayıcı ve SAST | test | security_scan |
| 7.1 | Kalıcı iş akışı, kontrol noktasından devam | canlı | checkpoint.py; canlıda kesilip devam etti |
| 7.2 | MCP araç veri yolu ve izin kapsamları | kısmi | mcp_server, mcp_connector |
| 7.3 | Öncelikli GPU kuyruğu | kısmi | chat_queue bildirim veriyor; öncelik yok |
| 7.3 | WebSocket canlı DAG akışı | kısmi | SSE ile aşama akışı var |
| 8.1 | İzleme (OpenTelemetry) ve pano | kısmi | telemetry_otel, run_trace; pano yok |
| 8.2 | 25+ senaryoluk altın test takımı | canlı | scripts/golden.py: hızlı küme canlıda; --slow ile üretim senaryoları |
| 8.3 | Sürüm kapısı ölçütleri | test | eval_stats: golden ve release_guard içinde |
| 9 | Çalışırken duraklatma ve yönlendirme | yok |  |
| 9 | Kanıt kartı (doğrulama özeti) | canlı | IDE 'Kanıt' çekmecesi |
| 9 | İki varyant yan yana | test | variants.py: iki üretim arka arkaya, iki kart |
| 9 | Dürüst düşüş bildirimi | test | reply_labels |

## v3

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 1.1 | LAN çıkarım ağı ve zamanlayıcı | dışarıda | tek bilgisayar |
| 1.2 | Spekülatif çözme | dışarıda | Ollama denetim vermiyor |
| 1.3 | Radix KV önbellek havuzu | teknik engel | Ollama dışarıdan KV denetimi vermiyor |
| 1.4 | Şemaya zorlanmış JSON üretimi | test | Ollama format şeması |
| 1.4 | GBNF/XGrammar yama ve sözdizimi maskeleri | teknik engel | Ollama API'si özel dilbilgisi almıyor |
| 2.1 | Z3 ile sayısal doğrulama | canlı | z3_math |
| 2.1 | Z3 ile iş kuralı değişmezleri ve karşı örnek | kısmi | property_check rastgele karşı örnek arıyor; Z3 ile ispat değil |
| 2.1 | Durum makinesi tam tarama | kısmi | akış şemasında çıkışsız döngü taraması |
| 2.1 | Durumlu özellik testi (Hypothesis) | canlı | property_check.py: kuralı model yazıyor, canlıda 3/3 ihlal buldu; api_probe ekle-sil tutarlılığı |
| 2.2 | Mutasyon testi kapısı | canlı | mutation.py; uyarı verir, teslimi engellemez |
| 2.3 | Yerleşim geometrisi ve kontrast denetimi | test | visual_audit |
| 2.3 | Görsel model eleştirisi | canlı | vlm_critique; kusurların bir kısmını kaçırıyor |
| 3.1 | PRM eğitimi | dışarıda | eğitim |
| 3.1 | Bütçeli ağaç araması (MCTS) | yok |  |
| 3.2 | Boşta kendi kendine alıştırma (müfredat + kırmızı takım) | yok |  |
| 3.3 | Çoklu LoRA, TIES/DARE birleştirme | dışarıda | eğitim |
| 3.4 | Bilgi damıtma | dışarıda | eğitim |
| 4.1 | Ajan başına git worktree ve AST birleştirme | yok |  |
| 4.2 | Depolar arası sözleşme ve geri alınabilir göç | kısmi | migration_check.py: up/down çiftleri; depolar arası sözleşme yok |
| 4.3 | Sertleştirilmiş Dockerfile/Compose üretimi ve denetimi | test | deploy_kit.py: istenince Python web projesine; hadolint/trivy ile değil |
| 4.3 | Yük ve kaos testi | canlı | sohbetten 'yük testi yap' (ağsız kutuda); kaos senaryosu yok |
| 4.3 | Çalışma anı bekçisi | yok |  |
| 5.1 | Ekran görüntüsünden koda | canlı | design_from_image.py: ölçülen renk/yerleşim + görsel model; canlıda yerleşim %87, renk %97 |
| 5.2 | Typst/WeasyPrint belge stüdyosu | kısmi | PyMuPDF ile PDF; Typst yok |
| 5.2 | PDF sayfa sayfa görsel kanıtlama | test | office_verify.proof_page: boş sayfa, taşma, çakışma, küçük punto |
| 5.3 | Çoklu diyagram biçimi | kısmi | SVG ve Mermaid |
| 5.3 | Gerçek veriye bağlı grafik | kısmi | document_chart |
| 5.3 | Yerel ses (ASR/TTS) | kısmi | multimodal_studio_media STT; TTS yok |
| 6.1 | İki zamanlı bilgi grafiği | test | memory_timeline |
| 6.2 | Bağlam sayfalama | yok |  |
| 6.3 | Uyku birleştirmesi ve çelişki çözümü | kısmi | memory_conflicts, memory_maintenance |
| 6.3 | Bellek denetim ve silme | test | memory_api, retention |
| 7.1 | WASM ve iş nesnesi yalıtımı | test | isolation.py: sohbetten başlatılan canlı sunucu iş nesnesiyle sınırlı |
| 7.2 | Leke (taint) izleme ve yetki düşürme | test | policy.Context; çalışma düzeyinde, bayt düzeyinde değil |
| 7.3 | Kod olarak politika | test | policy.py (OPA/Cedar değil) |
| 7.4 | İmzalı köken kaydı ve SBOM | canlı | provenance |
| 7.4 | Lisans uyum kapısı | test | code_audit.licence_conflicts |
| 8 | Kontrol/veri akışı analizi | test | code_audit.flows (fonksiyon içi girdi-hedef akışı); fonksiyonlar arası değil |
| 8 | Performans profilleyici (SQL planı, N+1) | test | code_audit: N+1 ve SQLite sorgu planı; çalışma anı profili yok |
| 8 | Tüm projede sembol yeniden adlandırma | canlı | refactor.py (Python), sohbetten |
| 9.1 | Olay kaydı ve zaman yolculuğu | test | event_log.py + sürümler; çatallama yok |
| 9.2 | LSP ve DAP veri yolu | yok |  |
| 10 | Önizlemede tıklayıp düzenleme | canlı | öğe seçici; gerçek Chromium'da denendi |
| 10 | DAG savaş odası ve zaman kaydırıcı | kısmi | sürüm zaman çizelgesi var; canlı graf yok |
| 10 | Turnuva modu | kısmi | media_lab_arena model puanlama |
| 10 | Köken ve bellek çekmeceleri | kısmi | kanıt çekmecesi var; bellek çekmecesi yok |
| 10 | Elle yapılan düzenlemeyi koruma | kısmi | yama korur, geri al, tercih belleği; elle düzenlemeden sinyal yok |
| 11.1 | Parametrik benchmark üretici | test | golden.py: tohumdan rastgele değerler |
| 11.2 | İstatistiksel sürüm kapısı, SPRT | test | eval_stats |
| 11.2 | Otomatik geri alma | test | release_guard.py: gerileyen koşuda istemleri geri alır (golden.py --auto-rollback); canlı trafik izlemiyor |

## v4

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 1.1 | 5 vitesli orantılılık freni | test | complexity_governor |
| 1.2 | Otomatik vites yükseltme ve süre bütçesi | kısmi | onarım yükseltmesi var; süre bütçesi yok |
| 1.2 | @fast/@deep komutları | test | complexity_governor |
| 2.1 | Web araması ve temiz metin çıkarma | canlı | DuckDuckGo + trafilatura |
| 2.2 | Çok adımlı derin araştırma ve çelişki tespiti | canlı | research.py: yanıtsız kalanlar için ikinci tur |
| 2.2 | Alıntı doğrulama kapısı | canlı | research.py; çeviri hatasını yakalayamaz |
| 2.3 | Sürüme bağlı belge kasası, çevrimdışı mod | test | docs_vault.py: sürüm ve özet, 14 gün önbellek; belge metni indirmiyor |
| 3.1 | Üç sesli tartışma kurulu | canlı | tool_executor: 'konseyde tartış'; canlıda denendi |
| 3.2 | Tasarım kuralları ve şablon görünüm dedektörü | test | design_slop |
| 3.2 | OKLCH palet derleyici | test | design_system.py: renk verilmeyen görsel isteklerde |
| 3.3 | Kişisel beğeni belleği | canlı | preferences.py: açık kalıcı ifadeler; örtük beğeni öğrenmiyor |
| 4.1 | Özet ağacı (RAPTOR) | kısmi | doc_reader eşle-indirge; çok katmanlı özet ağacı ve gömme indeksi yok |
| 4.2 | Belge gezinme ve eşle-indirge okuma | canlı | doc_reader.py: 'belgenin tamamını' isteklerinde; satır numaralı doğrulanmış alıntı |
| 5.1 | Tarayıcı kullanan ajan (erişilebilirlik ağacı) | canlı | browser_agent.py: @tarayıcı <adres> <görev>; DOM öğe listesi, görsel model yedeği yok |
| 5.2 | Her eylemi doğrulama ve geri alınamaz eylemde onay | canlı | browser_agent.py: düğme adıyla onay; yerel gizli talimat testinde geçti |
| 6.1 | Hesapların kodla yapılması | canlı | z3_math, data_lab, doc_calc |
| 6.1 | SymPy/SciPy çekirdeği | canlı | math_kernel.py (SymPy); SciPy yok |
| 6.2 | Canlı formüllü Excel ve yeniden hesaplama | canlı | office_verify |
| 6.3 | Sunum üretimi | test | deck_flow |
| 6.3 | Slayt slayt görsel denetim | test | aynı denetim slaytlarda (LibreOffice ile PDF'e çevirip) |
| 6.4 | DuckDB veri çalışması | canlı | data_lab |
| 6.4 | Otomatik EDA ve ML hattı | canlı | eda.py: CSV için profil + 5 katlı çapraz doğrulama; Vega/Plotly grafik yok |
| 6.5 | Uzun yazıda sayı tutarlılığı | test | doc_sanity, doc_proof |
| 7 | Karma buluta yükseltme (varsayılan kapalı) | yok |  |
| 8 | Uzmanlığa göre anlatım ve netleştirme sorusu | kısmi | clarify |
| 9 | Dosya izleyici ve gelen kutusu tetikleyicisi | canlı | triggers.py: data/inbox; pilde/sıcakta bekler. Git kancası yok |
| 9 | Zamanlanmış görevler | test | cronjobs |
| 10.1 | Donanım profili ve doctor | canlı | scripts/ai_os.py |
| 10.2 | Tembel servisler ve boşta kapatma | kısmi | gateway/local_gpu, power_manager |
| 10.3 | ai-os setup ve yapılandırma dosyası | canlı | scripts/ai_os.py setup, ai-os.config.json |
| 10.3 | ai-os up, bench | test | bench ve up canlı denenmedi |
| 10.3 | Dockersız yerel mod | test | isolation |
| 11 | 7 boşluk kapatma testi | kısmi | bir kısmı e2e betiklerinde |
