# Tarayıcı taraması (8 rota, masaüstü ve 375 px)

Yöntem: izole sunucu (port 8099) tarayıcı panelinde açıldı; her rota için `location.hash` değiştirilip 2,5 sn beklendi ve DOM sorgulandı.

| Rota | h1 sayısı | Etiketsiz form kontrolü | Konsol hatası | Başarısız istek | 375 px: <32 px hedef |
|---|---|---|---|---|---|
| #/new | 2 | 5 | 0 | 0 | 4 |
| #/projects | 2 | 3 | 0 | 0 | 2 |
| #/agents | 2 | 3 | 0 | 0 | 2 |
| #/studios | 2 | **341** | 0 | 0 | 11 |
| #/artifacts | 2 | 3 | 0 | 0 | 2 |
| #/files | 2 | 3 | 0 | 0 | 3 |
| #/dashboard | 1 | 3 | 0 | 0 | 2 |
| #/assistant | 1 | 3 | 0 | 0 | 8 |

Diğer gözlemler: tüm rotalarda `document.title` aynı; yatay taşma yok (375 px); `#/assistant` ana kutusu `#promptInput` ve 2 `input[type=file]` etiketsiz.
