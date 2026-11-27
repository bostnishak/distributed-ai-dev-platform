# v1-v4 şartnameleri: madde madde durum

**canlı** = gerçek modellerle denendi ve geçti. **test** = otomatik testle geçti. **kısmi** = bir bölümü var.
**yok** = henüz yazılmadı. **dışarıda** = senin onayınla kapsam dışı. **teknik engel** = bu araçlarla yapılamıyor.

Bu dosya `scripts/spec_matrix.tsv` dosyasından üretilir: `python scripts/spec_matrix.py`

| Sürüm | canlı | test | kısmi | yok | dışarıda | teknik engel | Toplam |
|---|---|---|---|---|---|---|---|
| v1 | 31 | 1 | 0 | 0 | 0 | 0 | 32 |
| v2 | 38 | 3 | 0 | 0 | 2 | 1 | 44 |
| v3 | 43 | 0 | 0 | 0 | 5 | 2 | 50 |
| v4 | 29 | 3 | 0 | 0 | 1 | 0 | 33 |
| **Hepsi** | 141 | 7 | 0 | 0 | 8 | 3 | 159 |

## v1

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 1 Yasalar | Sahte veri ve yer tutucu yasağı (statik tarama + tarayıcı kapısı) | canlı | workspace_smoke, jsdom_probe |
| 1 Yasalar | Uydurma paket, dosya yolu, model adı engeli | canlı | package_check gerçek PyPI ile denendi |
| 1 Yasalar | Eleştirel, onaylayıcı olmayan akıl yürütme | test | prompts/agent_architect.md |
| 1 Yasalar | Renk, ölçü, etiket sadakati (spec.json) | canlı | spec_contract |
| 1 Yasalar | Ham kaynak saflığı (vurgulayıcı artığı yok) | canlı | pure_source |
| 2 Ajanlar | IntakeAgent, şemalı spec | canlı | canlı deneme: scripts/live_items.py |
| 2 Ajanlar | ArchitectAgent, plan ve risk denetimi | canlı | canlı deneme: scripts/live_items.py |
| 2 Ajanlar | Frontend ajanı, nokta atışı yama | canlı | canlı deneme: scripts/live_items.py |
| 2 Ajanlar | Backend ajanı, gerçek kalıcılık | canlı | workspace_batches |
| 2 Ajanlar | Akış şeması ajanı, doğrulanmış diyagram | canlı | flowchart_studio |
| 2 Ajanlar | PDF üretimi | canlı | document_factory |
| 2 Ajanlar | Görsel üretimi, motoru bildirme | canlı | multimodal_studio |
| 2 QA | HTML, JS, Python, JSON sözdizimi denetimi | canlı | canlı deneme: scripts/live_items.py |
| 2 QA | Yer tutucu tarayıcı | canlı | canlı deneme: scripts/live_items.py |
| 2 QA | Spec uyum denetçisi | canlı | canlı deneme: scripts/live_items.py |
| 2 QA | Tarayıcıda davranış testi | canlı | jsdom_probe, workspace_behavior |
| 2 QA | API'yi gerçek isteklerle sınama | canlı | api_probe |
| 2 QA | PDF ve görsel bütünlük denetimi | canlı | canlı deneme: scripts/live_items.py code |
| 2 QA | Sınırlı onarım döngüsü, dürüst başarısızlık bildirimi | canlı | workspace_builder |
| 3 Ollama | Kurulu modelleri keşfetme ve role göre seçim, yedek model | canlı | canlı deneme: scripts/live_items.py |
| 3 Ollama | Role göre sıcaklık ve şemalı çıktı | canlı | canlı deneme: scripts/live_items.py |
| 3 Ollama | Dosya dosya parçalı üretim | canlı | workspace_batches |
| 3 Ollama | Ajan bazında TTFT ve token/sn göstergesi | canlı | 'performans durumu': model bazında token/sn ve akışlı yanıtlarda ilk kelime süresi |
| 4 Bellek | Son turlar ve takip isteği birleştirme | canlı | followup |
| 4 Bellek | Proje durumu, sürüm anlık görüntüsü | canlı | canlı deneme: scripts/live_items.py |
| 4 Bellek | Uzun süreli tercih belleği | canlı | canlı deneme: scripts/live_items.py |
| 4 Bellek | Yıkıcı olmayan yineleme | canlı | revise_chat, tier0_edit |
| 5 IDE | Yalıtılmış çalışma alanı, yol kaçışı koruması | canlı | canlı deneme: scripts/live_items.py |
| 5 IDE | Dosya gezgini, editör, diff, ZIP | canlı | diff artık bir önceki sürümle |
| 5 IDE | Korumalı önizleme ve hata köprüsü | canlı | gerçek Chromium'da denendi; satır numarası düzeltildi |
| 5 IDE | API test konsolu sekmesi | canlı | workspace_inspect.py; gerçek Chromium'da denendi |
| 6 Teslim | Uçtan uca testler ve çalışma kılavuzu | canlı | scripts/e2e_stress.py |

## v2

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 2.1 | Sabit önek önce istem düzeni | canlı | prompt_layout.py: değişenler soruyla en sonda; ikinci turda istem okuma 1161 ms yerine 364 ms ölçüldü |
| 2.1 | keep_alive, num_ctx boyutlama | canlı | canlı deneme: scripts/live_items.py |
| 2.1 | Model yakınlığına göre görev gruplama | canlı | canlı deneme: scripts/live_items.py code |
| 2.2 | Tier 0 modelsiz düzenleme | canlı | tier0_edit |
| 2.2 | Karmaşıklığa göre model basamağı | canlı | canlı deneme: scripts/live_items.py |
| 2.2 | Logprob/entropi ile yükseltme | teknik engel | Ollama yanıtında güvenilir logprob kullanılmıyor |
| 2.3 | Paralel DAG yürütücü, spekülatif ön hazırlık | canlı | dag.py ve build_dag.py: bağımlılık sırası, model yakınlığı, arka planda denetim ön hazırlığı; gerçek üretimde canlı |
| 2.3 | Yalnız etkilenen testleri koşma | canlı | canlı deneme: scripts/live_items.py |
| 2.4 | AST çapalı yama, tam yazıma geri düşme | canlı | canlı deneme: scripts/live_items.py |
| 2.4 | L1 birebir önbellek | canlı | canlı deneme: scripts/live_items.py |
| 2.4 | L2 anlamsal, L3 bileşen önbelleği | test | semantic_cache.py (belge bazlı) ve skill_library (doğrulanmış bileşen) |
| 3.1 | Yörünge toplama, sır temizleme | canlı | canlı deneme: scripts/live_items.py |
| 3.1 | Tercih çiftleri (başarısız/onarılmış) | test | repair_pairs.py: başarılı onarımlardan çift |
| 3.2 | Yerel LoRA/DPO/GRPO eğitimi | dışarıda | bellek ve veri yetersiz; yalnız betik |
| 3.2 | GGUF içe aktarma ve gölge değerlendirme kapısı | canlı | ai_os.py import-gguf gerçek GGUF ile denendi: zayıf aday reddedildi, eşit aday yayımlandı |
| 3.3 | Doğrulanmış beceri kütüphanesi | canlı | canlı deneme: scripts/live_items.py |
| 3.3 | Otomatik istem optimizasyonu | test | scripts/optimize_prompt.py: yalnız ölçülen iyileşmede tutar; canlıda koşulmadı |
| 4.1 | Hipotez temelli nedensel hata ayıklama + regresyon testi | canlı | causal_debug + DAP durumu; regresyon testi üretmiyor |
| 4.2 | En iyi N aday değerlendirme | canlı | best_of_n.py: 2-3 aday, eleştirmen ve kural puanı; canlı |
| 4.3 | Doğrulanmış/çıkarım/varsayım defteri | canlı | canlı deneme: scripts/live_items.py |
| 4.4 | API fuzz ve sınır testi | canlı | api_probe; Docker kum havuzunda denendi |
| 4.4 | Arayüz kaos, erişilebilirlik, üç ekran genişliği | canlı | ui_chaos + visual_audit |
| 4.4 | Uydurma paket (slopsquatting) denetimi | canlı | package_check |
| 5.1 | Depo haritası | canlı | repo_map.py (AST/regex + PageRank; tree-sitter değil); düzenlemede kullanılıyor, birim testli |
| 5.2 | Melez kod araması (graf+BM25+gömme) | canlı | code_search.py: BM25 + sembol + CPU gömme |
| 5.2 | Etki alanı (blast radius) analizi | canlı | canlı deneme: scripts/live_items.py |
| 5.3 | Anlık statik tanılama (ruff, node --check) | canlı | code_audit.diagnostics (ruff, node --check), üretim sonunda |
| 5.3 | LSP sunucuları | canlı | lsp_client.py: pylsp ile 'X nerede kullanılıyor'; yalnız Python |
| 6.1 | Yalıtılmış çalıştırma (ağsız Docker, kaynak sınırı) | canlı | canlı deneme: scripts/live_items.py |
| 6.1 | gVisor/Firecracker | dışarıda | Windows'ta yok |
| 6.2 | Güvenilmeyen veri ayrımı | canlı | untrusted |
| 6.2 | Eylem yetki politikası kapısı | canlı | canlı deneme: scripts/live_items.py |
| 6.3 | Sır tarayıcı ve SAST | canlı | canlı deneme: scripts/live_items.py |
| 7.1 | Kalıcı iş akışı, kontrol noktasından devam | canlı | checkpoint.py; canlıda kesilip devam etti |
| 7.2 | MCP araç veri yolu ve izin kapsamları | canlı | canlı deneme: scripts/live_items.py |
| 7.3 | Öncelikli GPU kuyruğu | canlı | canlı deneme: scripts/live_items.py |
| 7.3 | WebSocket canlı DAG akışı | canlı | run_api.py /api/runs/ws; tarayıcıda canlı doğrulandı |
| 8.1 | İzleme (OpenTelemetry) ve pano | canlı | perf_report: 'performans durumu' |
| 8.2 | 25+ senaryoluk altın test takımı | canlı | scripts/golden.py: hızlı küme canlıda; --slow ile üretim senaryoları |
| 8.3 | Sürüm kapısı ölçütleri | canlı | canlı deneme: scripts/live_items.py code |
| 9 | Çalışırken duraklatma ve yönlendirme | canlı | Gerçek üretim 100 sn duraklatıldı, talimat eklendi, sonraki dosyaya uygulandı |
| 9 | Kanıt kartı (doğrulama özeti) | canlı | IDE 'Kanıt' çekmecesi |
| 9 | İki varyant yan yana | canlı | canlı deneme: scripts/live_items.py |
| 9 | Dürüst düşüş bildirimi | canlı | canlı deneme: scripts/live_items.py code |

## v3

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 1.1 | LAN çıkarım ağı ve zamanlayıcı | dışarıda | tek bilgisayar |
| 1.2 | Spekülatif çözme | dışarıda | Ollama denetim vermiyor |
| 1.3 | Radix KV önbellek havuzu | teknik engel | Ollama dışarıdan KV denetimi vermiyor |
| 1.4 | Şemaya zorlanmış JSON üretimi | canlı | canlı deneme: scripts/live_items.py |
| 1.4 | GBNF/XGrammar yama ve sözdizimi maskeleri | teknik engel | Ollama API'si özel dilbilgisi almıyor |
| 2.1 | Z3 ile sayısal doğrulama | canlı | z3_math |
| 2.1 | Z3 ile iş kuralı değişmezleri ve karşı örnek | canlı | symbolic.py: tamsayı koşul/atama alt kümesinde ispat ya da karşı örnek; döngü ve çağrı içeren kodda ispat yok |
| 2.1 | Durum makinesi tam tarama | canlı | statecheck.py: çıkmaz, livelock, yetim, yarış; en kısa yol örneğiyle |
| 2.1 | Durumlu özellik testi (Hypothesis) | canlı | property_check.py: kuralı model yazıyor, canlıda 3/3 ihlal buldu; api_probe ekle-sil tutarlılığı |
| 2.2 | Mutasyon testi kapısı | canlı | mutation.py; uyarı verir, teslimi engellemez |
| 2.3 | Yerleşim geometrisi ve kontrast denetimi | canlı | canlı deneme: scripts/live_items.py |
| 2.3 | Görsel model eleştirisi | canlı | vlm_critique; kusurların bir kısmını kaçırıyor |
| 3.1 | PRM eğitimi | dışarıda | eğitim |
| 3.1 | Bütçeli ağaç araması (MCTS) | canlı | tree_search.py: onarımda UCT, canlıda 3 hatayı çözdü; PUCT/PRM yok |
| 3.2 | Boşta kendi kendine alıştırma (müfredat + kırmızı takım) | canlı | self_play.py: referansla tutarlı testler, tuzaklı görev, beceri kartı ve başarısızlık dosyası; PRM etiketi yok |
| 3.3 | Çoklu LoRA, TIES/DARE birleştirme | dışarıda | eğitim |
| 3.4 | Bilgi damıtma | dışarıda | eğitim |
| 4.1 | Ajan başına git worktree ve AST birleştirme | canlı | swarm.py ve semantic_merge.py: iki ajan aynı dosyada, canlıda birleşti; Python sembol düzeyinde (tree-sitter değil, ast) |
| 4.2 | Depolar arası sözleşme ve geri alınabilir göç | canlı | federation.py: etki alanı, kopyada ileri-geri-ileri kanıtı, hepsi ya da hiçbiri; iki projede canlı |
| 4.3 | Sertleştirilmiş Dockerfile/Compose üretimi ve denetimi | canlı | canlı deneme: scripts/live_items.py |
| 4.3 | Yük ve kaos testi | canlı | sohbetten 'yük testi yap' (ağsız kutuda); kaos senaryosu yok |
| 4.3 | Çalışma anı bekçisi | canlı | canlı deneme: scripts/live_items.py |
| 5.1 | Ekran görüntüsünden koda | canlı | design_from_image.py: ölçülen renk/yerleşim + görsel model; canlıda yerleşim %87, renk %97 |
| 5.2 | Typst/WeasyPrint belge stüdyosu | canlı | typst_render.py: Typst istenince ya da denklemli belgede; WeasyPrint yok |
| 5.2 | PDF sayfa sayfa görsel kanıtlama | canlı | canlı deneme: scripts/live_items.py code |
| 5.3 | Çoklu diyagram biçimi | canlı | SVG + Mermaid, Graphviz, PlantUML metni (D2 yok) |
| 5.3 | Gerçek veriye bağlı grafik | canlı | data_chart.py: CSV'den çubuk grafik; etkileşimli Vega/Plotly değil |
| 5.3 | Yerel ses (ASR/TTS) | canlı | tts.py (Piper tr_TR) + faster-whisper; üretilen ses geri çözülerek canlı doğrulandı; ses verisi lisansı ticari kullanıma kapalı |
| 6.1 | İki zamanlı bilgi grafiği | canlı | canlı deneme: scripts/live_items.py |
| 6.2 | Bağlam sayfalama | canlı | context_pager.py: pencere dışındaki ilgili turlar geri çağrılır; uzun sohbette canlı |
| 6.3 | Uyku birleştirmesi ve çelişki çözümü | canlı | canlı deneme: scripts/live_items.py |
| 6.3 | Bellek denetim ve silme | canlı | canlı deneme: scripts/live_items.py |
| 7.1 | WASM ve iş nesnesi yalıtımı | canlı | canlı deneme: scripts/live_items.py |
| 7.2 | Leke (taint) izleme ve yetki düşürme | canlı | canlı deneme: scripts/live_items.py |
| 7.3 | Kod olarak politika | canlı | canlı deneme: scripts/live_items.py code |
| 7.4 | İmzalı köken kaydı ve SBOM | canlı | provenance |
| 7.4 | Lisans uyum kapısı | canlı | canlı deneme: scripts/live_items.py |
| 8 | Kontrol/veri akışı analizi | canlı | canlı deneme: scripts/live_items.py |
| 8 | Performans profilleyici (SQL planı, N+1) | canlı | canlı deneme: scripts/live_items.py |
| 8 | Tüm projede sembol yeniden adlandırma | canlı | refactor.py (Python), sohbetten |
| 9.1 | Olay kaydı ve zaman yolculuğu | canlı | canlı deneme: scripts/live_items.py |
| 9.2 | LSP ve DAP veri yolu | canlı | lsp_client + debug_probe (debugpy, kum havuzunda canlı); ortak bir veri yolu soyutlaması yalnız mesaj çerçevesi |
| 10 | Önizlemede tıklayıp düzenleme | canlı | öğe seçici; gerçek Chromium'da denendi |
| 10 | DAG savaş odası ve zaman kaydırıcı | canlı | war_room.js: canlı graf, süre ve yaklaşık tok/sn, zaman çubuğu, sürümden dallanma |
| 10 | Turnuva modu | canlı | arena.py: aynı istek iki modelle, süre-denetim-renk tablosu ve önizlemeler; canlı |
| 10 | Köken ve bellek çekmeceleri | canlı | IDE: Kanıt ve Bellek çekmeceleri |
| 10 | Elle yapılan düzenlemeyi koruma | canlı | merge3 + geri al; elle düzenlemeden tercih öğrenmiyor |
| 11.1 | Parametrik benchmark üretici | canlı | canlı deneme: scripts/live_items.py |
| 11.2 | İstatistiksel sürüm kapısı, SPRT | canlı | canlı deneme: scripts/live_items.py |
| 11.2 | Otomatik geri alma | canlı | canlı deneme: scripts/live_items.py |

## v4

| Bölüm | Madde | Durum | Not |
|---|---|---|---|
| 1.1 | 5 vitesli orantılılık freni | canlı | canlı deneme: scripts/live_items.py |
| 1.2 | Otomatik vites yükseltme ve süre bütçesi | canlı | canlı deneme: scripts/live_items.py code |
| 1.2 | @fast/@deep komutları | canlı | canlı deneme: scripts/live_items.py |
| 2.1 | Web araması ve temiz metin çıkarma | canlı | DuckDuckGo + trafilatura |
| 2.2 | Çok adımlı derin araştırma ve çelişki tespiti | canlı | research.py: yanıtsız kalanlar için ikinci tur |
| 2.2 | Alıntı doğrulama kapısı | canlı | research.py; çeviri hatasını yakalayamaz |
| 2.3 | Sürüme bağlı belge kasası, çevrimdışı mod | canlı | canlı deneme: scripts/live_items.py |
| 3.1 | Üç sesli tartışma kurulu | canlı | tool_executor: 'konseyde tartış'; canlıda denendi |
| 3.2 | Tasarım kuralları ve şablon görünüm dedektörü | canlı | canlı deneme: scripts/live_items.py |
| 3.2 | OKLCH palet derleyici | canlı | canlı deneme: scripts/live_items.py |
| 3.3 | Kişisel beğeni belleği | canlı | preferences.py: açık kalıcı ifadeler; örtük beğeni öğrenmiyor |
| 4.1 | Özet ağacı (RAPTOR) | canlı | doc_tree.py: parça → bölüm → bütün, satır aralıklı; gömme indeksi yok |
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
| 7 | Karma buluta yükseltme (varsayılan kapalı) | dışarıda | Kullanıcı istemedi (ücretli servis olmasın); yalnız ücretsiz yerel anonimleştirme komutu var, hiçbir yere gönderim yok |
| 8 | Uzmanlığa göre anlatım ve netleştirme sorusu | canlı | pacing.audience_note + clarify |
| 9 | Dosya izleyici ve gelen kutusu tetikleyicisi | canlı | triggers.py: data/inbox; pilde/sıcakta bekler. Git kancası yok |
| 9 | Zamanlanmış görevler | canlı | canlı deneme: scripts/live_items.py |
| 10.1 | Donanım profili ve doctor | canlı | scripts/ai_os.py |
| 10.2 | Tembel servisler ve boşta kapatma | canlı | daemons.py: arama kabı kapalıyken ihtiyaçta açıldı ve boşta kapandı; ses motorları boşta bırakılır; servis durumu komutu |
| 10.3 | ai-os setup ve yapılandırma dosyası | canlı | scripts/ai_os.py setup, ai-os.config.json |
| 10.3 | ai-os up, bench | canlı | canlı deneme: scripts/live_items.py code (up; bench yalnız giriş noktası) |
| 10.3 | Dockersız yerel mod | canlı | canlı deneme: scripts/live_items.py |
| 11 | 7 boşluk kapatma testi | canlı | scripts/gap_suite.py: yedisi de canlı geçti; soğuk açılış 3.2 sn ve 214 MB |
