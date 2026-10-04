> **ÖRNEK DOKÜMAN** — Bu gereksinim dokümanı, platformun gereksinim analizi ve görev ayrıştırma
> özelliğini test etmek için ekip tarafından hazırlanmış kurgusal bir örnektir.
> Gerçek bir kurum veya müşteriye ait değildir.

# Online Klinik Randevu Sistemi — Yazılım Gereksinim Dokümanı

Sürüm 1.0 · Hazırlayan: team6 (örnek)

## 1. Amaç

Bu doküman, birden fazla uzmanlık bölümü olan özel bir polikliniğin randevu işlerini yönetecek
web tabanlı bir uygulamanın gereksinimlerini tanımlar. Klinik bugün randevuları telefonla
alıp bir takvim defterine yazmaktadır. Yeni sistemin amacı, hastaların randevuyu kendilerinin
alabilmesi, doktorların günlük programını tek ekranda görebilmesi ve gelinmeyen randevuların
azaltılmasıdır.

## 2. Kapsam

Sistem, hastaların kullanacağı bir randevu arayüzü, doktorların kullanacağı bir program
arayüzü ve sekreterlerin kullanacağı bir yönetim arayüzünden oluşur. Uygulama web
tarayıcısından kullanılacak ve kliniğin kendi sunucusunda çalışacaktır.

Kapsam dışı olanlar:

- Muayene notları, reçete ve tahlil sonuçları (elektronik sağlık kaydı)
- Sigorta ve fatura işlemleri
- Mobil uygulama (web arayüzünün mobil tarayıcıda düzgün görünmesi yeterlidir)

## 3. Kullanıcılar

- **Hasta:** Hesap açar, uygun saatleri görür, randevu alır, iptal eder veya erteler.
- **Doktor:** Kendi çalışma saatlerini ve izinlerini girer, günlük randevu listesini görür,
  hastayı "geldi" veya "gelmedi" olarak işaretler.
- **Sekreter:** Telefonla arayan hasta adına randevu oluşturur, randevuları düzenler, bölüm
  ve doktor kayıtlarını yönetir.
- **Yönetici:** Sekreter ve doktor hesaplarını oluşturur, raporları görüntüler, sistem
  ayarlarını değiştirir.

## 4. Fonksiyonel Gereksinimler

### 4.1 Bölüm ve doktor yönetimi

- FR-1: Sekreter yeni bölüm ekleyebilmelidir (ör. dahiliye, göz, kulak burun boğaz). Her
  bölümün adı ve açıklaması kaydedilir.
- FR-2: Sekreter doktor kaydı oluşturabilmelidir. Doktorun adı, soyadı, unvanı, bölümü,
  e-posta adresi ve telefon numarası kaydedilir. Bir doktor yalnızca bir bölüme bağlıdır.
- FR-3: Bir doktorun gelecekte randevusu varsa kaydı silinemez, yalnızca pasif yapılabilir.

### 4.2 Çalışma saatleri ve izinler

- FR-4: Doktor, haftanın her günü için çalışma saatlerini girer (ör. pazartesi 09:00–17:00).
- FR-5: Randevular sabit uzunlukta aralıklara bölünür. Varsayılan aralık 20 dakikadır ve her
  bölüm için ayrı ayarlanabilir.
- FR-6: Doktor izin günü veya izinli saat aralığı girebilir. İzinli zamanlarda randevu
  verilmez.
- FR-7: Doktor izin girdiği zaman aralığında zaten alınmış randevular varsa, bu randevuların
  hastalarına bildirim gönderilir ve randevular sekreterin listesine "yeniden planlanacak"
  olarak düşer.

### 4.3 Hasta hesabı

- FR-8: Hasta adı, soyadı, T.C. kimlik numarası, doğum tarihi, telefon numarası ve e-posta
  adresi ile hesap açar.
- FR-9: Aynı T.C. kimlik numarasıyla ikinci bir hesap açılamaz.
- FR-10: Hasta kendi iletişim bilgilerini güncelleyebilir.

### 4.4 Randevu alma

- FR-11: Hasta önce bölümü, sonra doktoru seçer ve doktorun boş aralıklarını takvim
  görünümünde görür.
- FR-12: Hasta boş bir aralığı seçerek randevu alır. Aynı aralık iki hastaya verilemez.
- FR-13: Bir hastanın aynı bölümde aynı anda en fazla 2 ileri tarihli randevusu olabilir.
- FR-14: Randevular en fazla 30 gün sonrası için alınabilir.
- FR-15: Sekreter, hesap açmamış bir hasta adına da randevu oluşturabilir. Bu durumda hastanın
  adı, soyadı ve telefon numarası kaydedilir.

### 4.5 İptal ve erteleme

- FR-16: Hasta, randevusuna 24 saatten fazla varsa randevuyu iptal edebilir veya başka bir
  boş aralığa erteleyebilir.
- FR-17: 24 saatten az kalan randevular yalnızca sekreter tarafından iptal edilebilir.
- FR-18: İptal edilen aralık hemen yeniden boş görünür.

### 4.6 Gelmeyen hastalar

- FR-19: Doktor veya sekreter, randevu saati geçtikten sonra hastayı "geldi" ya da "gelmedi"
  olarak işaretler.
- FR-20: Son 90 günde 3 kez gelmeyen hastanın yeni randevu alması engellenir; bu hasta yalnızca
  sekreter aracılığıyla randevu alabilir.

### 4.7 Bildirimler

- FR-21: Randevu oluşturulduğunda, ertelendiğinde ve iptal edildiğinde hastaya e-posta
  gönderilir.
- FR-22: Randevudan 1 gün önce hastaya hatırlatma mesajı gönderilir.

### 4.8 Raporlar

- FR-23: Yönetici, seçilen tarih aralığında bölüm ve doktor bazında randevu sayılarını görür.
- FR-24: Yönetici, gelmeyen hasta oranını doktor ve bölüm bazında görür.

### 4.9 Hesaplar ve giriş

- FR-25: Hastalar, doktorlar, sekreterler ve yönetici e-posta adresi ve şifre ile giriş yapar.
- FR-26: Yönetici sekreter ve doktor hesabı oluşturabilir ve devre dışı bırakabilir.

## 5. Ekranlar

1. Giriş ve kayıt ekranı
2. Bölüm ve doktor seçimi
3. Doktor takvimi ve randevu alma
4. Hastanın randevularım sayfası
5. Doktorun günlük programı
6. Doktorun çalışma saatleri ve izinleri
7. Sekreter randevu yönetimi
8. Bölüm ve doktor yönetimi
9. Raporlar

## 6. Fonksiyonel Olmayan Gereksinimler

- NFR-1: Bir doktorun boş aralıkları 1 saniyeden kısa sürede gösterilmelidir.
- NFR-2: Şifreler düz metin olarak saklanmamalıdır.
- NFR-3: Arayüz Türkçe olmalı ve masaüstü ile mobil tarayıcılarda kullanılabilir olmalıdır.
- NFR-4: T.C. kimlik numarası ve doğum tarihi yalnızca hastanın kendisi, sekreterler ve
  yönetici tarafından görülebilmelidir.
- NFR-5: Aynı aralık için aynı anda gelen iki randevu isteğinden yalnızca biri kabul
  edilmelidir.
- NFR-6: Randevu oluşturma, erteleme ve iptal işlemleri kim tarafından ve ne zaman yapıldığıyla
  birlikte kaydedilmelidir.

## 7. Veri

Sistem en az şu bilgileri saklar: bölümler, doktorlar, çalışma saatleri, izinler, hastalar,
randevular, bildirim kayıtları ve kullanıcı hesapları.
