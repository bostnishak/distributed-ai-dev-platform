# Agent Node Kurulumu

Bu, Ensar Gül'ün DevOps dersi için yaptığımız çoklu-LLM orkestrasyon projesi. Bir kişi ("orkestratör") istem alıyor, işi en uygun açık kaynak modele yönlendiriyor. Senin bilgisayarın o modellerden birini ("sub-agent") çalıştıracak.

Bu klasördeki script kendi bilgisayarında **Ollama**'yı kurup sana atanan modeli çeker, test eder ve gateway'i kuran arkadaşımıza iletmen gereken bilgiyi ekrana yazdırır. Herkes aynı script'i kullanıyor, sadece kendi model parametrenizi veriyorsunuz.

## Model ataması (doğrulandı — Ollama kütüphanesinde mevcut, 2026-09-24)

| Kim | Ollama model tag'i | Model | Şirket | İndirme boyutu (~) |
|---|---|---|---|---|
| İshak Bostan (Üye-1) | `qwen3.5:4b` | Qwen3.5 4B | Alibaba | *(orkestratör makinesinde zaten kuruldu)* |
| Duru Küçük (Üye-2) | `phi4-mini` | Phi-4-mini (3.8B) | Microsoft | ~2.5 GB |
| Furkan Kaan (Üye-3) | `llama3.2:3b` | Llama 3.2 3B | Meta | ~2 GB |
| Semih Sarıca (Üye-4) | `gemma4:e4b` | Gemma 4 E4B | Google | ~3 GB |
| Işıl Karademir (Üye-5) | `qwen2.5-coder:7b` | Qwen2.5-Coder 7B | Alibaba (kod uzmanı) | ~4.5 GB |
| Berfin Yiğit (Üye-6) | `qwen3:1.7b` | Qwen3 1.7B | Alibaba (en hafif) | ~1.4 GB |

(Boyutlar yaklaşık — indirme hızına göre birkaç dakika sürebilir.)

## Kullanım

**Windows:**
```powershell
.\setup.ps1 -Model "phi4-mini"
```

**Mac / Linux:**
```bash
chmod +x setup.sh
./setup.sh phi4-mini
```

Kendi satırındaki model tag'ini kullan (yukarıdaki tablo). Script şunları yapar:
1. Ollama kurulu değilse kurar
2. **Ollama'yı LAN'daki diğer bilgisayarlardan (gateway) erişilebilir hale getirir** — bkz. aşağıdaki not
3. Belirtilen modeli çeker (`ollama pull`)
4. Kısa bir test isteği atıp yanıt aldığını doğrular
5. Bu bilgisayarın LAN IP adresini yazdırır

**Kurulum bitince:** ekrana yazdırılan LAN IP adresini ve hangi modeli çektiğini (`Üye-N`) gateway'i kuran arkadaşımıza ilet — `gateway/litellm_config.yaml`'a eklenmesi gerekiyor.

**Ollama arka planda açık kalmalı:** kurulumdan sonra bilgisayarın açık ve Ollama çalışır durumda olduğu sürece istekleri karşılayabilir. Kapatırsan gateway sana ulaşamaz (diğer üyelere/bulut modellerine düşer).

## Not: LAN erişimi ve güvenlik

Script, Ollama'yı varsayılan (sadece localhost) yerine **tüm ağ arayüzlerinden** erişilebilir hale getiriyor (`OLLAMA_HOST=0.0.0.0`) — bu olmadan gateway sana hiç ulaşamıyor. Bunun anlamı: kurulum süresince **aynı LAN'daki herkes** (sadece bizim ekip değil) kimlik doğrulamasız olarak bu modeli sorgulayabilir. Ekip bunu güvenilir bir ev/okul ağında kabul edilebilir bir risk olarak değerlendirdi. Halka açık/güvenilmeyen bir ağdaysan (ör. kafe wifi'si) script'i çalıştırmadan önce bunu bilerek karar ver.

## Not: "thinking" modu

Bu modeller (özellikle Qwen ailesi) varsayılan olarak uzun bir iç muhakeme ("thinking") süreci çalıştırabilir ve CPU'da yanıtları yavaşlatabilir. Bunu orkestratör, her istekte `think: true/false` parametresiyle görev tipine göre kontrol edecek — sizin tarafınızda ekstra bir ayar yapmanıza gerek yok.
