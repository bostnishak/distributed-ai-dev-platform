# Denetim betikleri

Plan v3'ün bulgularını üreten, yeniden çalıştırılabilir yoklamalar. Hepsi **izole** bir sunucuya karşı çalışır; üretim verisine dokunmaz.

```powershell
$env:DB_PATH="$PWD\.audit_tmp\data\platform.db"
master\venv\Scripts\python.exe -m uvicorn app:app --app-dir master --port 8099
```

| Betik | Ne yapar |
|---|---|
| `probe_routes.py out.json` | OpenAPI'deki her güvenli route'a istek atar (silme/çalıştırma/yükleme atlanır) |
| `probe_http.py out.json` | Başlık, CORS, hız sınırı, bozuk JSON, yol geçişi, şema ve açıklama kapsamı |
| `battery.py [desen] [çıktı.jsonl]` | Gerçek sohbet isteklerini modele gönderir ve yanıtları makinece denetler |
| `features.py out.json` | Büyük asistanların yeteneklerinin kodda/OpenAPI'de izini arar |
| `scan_js.py out.json` | Arayüz kaynak taraması |
| `build_plan.py` | `docs/plan-v3/kanit/*.json` dosyalarından planı üretir |
