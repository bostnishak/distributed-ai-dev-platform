> **ÖRNEK DOKÜMAN** — Bu gereksinim dokümanı, platformun gereksinim analizi ve görev ayrıştırma
> özelliğini test etmek için ekip tarafından hazırlanmış kurgusal bir örnektir.
> Gerçek bir kurum veya müşteriye ait değildir.

# Üniversite Kulüp Etkinlik Yönetimi — Yazılım Gereksinim Dokümanı

Sürüm 1.0 · Hazırlayan: team6 (örnek)

## 1. Amaç

Bu doküman, bir üniversitedeki öğrenci kulüplerinin üyelik ve etkinlik işlerini yönetecek web
tabanlı bir uygulamanın gereksinimlerini tanımlar. Kulüpler bugün duyurularını sosyal medya
gruplarından yapmakta, etkinlik kayıtlarını çevrim içi formlarla toplamakta ve salon
rezervasyonlarını Sağlık, Kültür ve Spor Daire Başkanlığı'na e-postayla iletmektedir. Yeni
sistemin amacı, tüm kulüplerin etkinliklerini tek bir yerde toplamak, salon çakışmalarını
önlemek ve katılımı ölçebilmektir.

## 2. Kapsam

Sistem, öğrencilerin kullanacağı bir etkinlik arayüzü, kulüp yöneticilerinin kullanacağı bir
kulüp paneli ve daire başkanlığı personelinin kullanacağı bir onay ve yönetim arayüzünden
oluşur. Uygulama web tarayıcısından kullanılacak ve üniversitenin kendi sunucusunda
çalışacaktır.

Kapsam dışı olanlar:

- Ücretli etkinlikler için ödeme alma
- Kulüplerin bütçe ve harcama takibi
- Mobil uygulama (web arayüzünün mobil tarayıcıda düzgün görünmesi yeterlidir)

## 3. Kullanıcılar

- **Öğrenci:** Kulüpleri ve etkinlikleri inceler, kulüplere üye olur, etkinliklere kayıt olur.
- **Kulüp yöneticisi:** Kulübünün bilgilerini ve üyelerini yönetir, etkinlik oluşturur, salon
  talep eder, katılımı işaretler. Her kulübün bir başkanı ve en fazla 4 yönetim kurulu üyesi
  vardır.
- **Daire başkanlığı personeli:** Yeni kulüp başvurularını ve etkinlik taleplerini onaylar
  veya reddeder, salonları yönetir.
- **Yönetici:** Personel hesaplarını oluşturur, raporları görüntüler, sistem ayarlarını
  değiştirir.

## 4. Fonksiyonel Gereksinimler

### 4.1 Kulüp yönetimi

- FR-1: Bir öğrenci yeni kulüp kurmak için başvuru yapabilir. Başvuruda kulübün adı, amacı,
  danışman öğretim üyesi ve en az 15 kurucu üyenin öğrenci numarası bulunur.
- FR-2: Personel başvuruyu onaylar veya gerekçe yazarak reddeder. Onaylanan kulüp yayına
  alınır.
- FR-3: Kulüp yöneticisi kulübün açıklamasını, logosunu ve iletişim bilgilerini güncelleyebilir.
- FR-4: Bir dönem boyunca hiç etkinlik yapmayan kulüp personel tarafından pasif yapılabilir.

### 4.2 Üyelik

- FR-5: Öğrenci, üniversite e-posta adresiyle hesap açar. Hesapta adı, soyadı, öğrenci
  numarası, bölümü ve sınıfı bulunur.
- FR-6: Öğrenci bir kulübe üyelik isteği gönderir; kulüp yöneticisi isteği kabul eder veya
  reddeder.
- FR-7: Bir öğrenci aynı anda en fazla 5 kulübe üye olabilir.
- FR-8: Kulüp yöneticisi bir üyeyi kulüpten çıkarabilir.

### 4.3 Etkinlik oluşturma ve onay

- FR-9: Kulüp yöneticisi etkinlik taslağı oluşturur. Etkinliğin başlığı, açıklaması, tarihi,
  başlangıç ve bitiş saati, kontenjanı, yalnızca üyelere mi açık olduğu ve istenen salon
  kaydedilir.
- FR-10: Etkinlik, personel onayından sonra yayına girer. Personel, gerekçe yazarak etkinliği
  reddedebilir veya değişiklik isteyebilir.
- FR-11: Etkinlik tarihinden en az 7 gün önce onaya gönderilmelidir.
- FR-12: Yayındaki bir etkinlik iptal edildiğinde kayıtlı öğrencilere bildirim gönderilir.

### 4.4 Salon rezervasyonu

- FR-13: Personel salonları kaydeder. Her salonun adı, binası, kapasitesi ve donanımı
  (projeksiyon, ses sistemi gibi) bulunur.
- FR-14: Aynı salon aynı saat aralığında iki etkinliğe verilemez.
- FR-15: Etkinliğin kontenjanı seçilen salonun kapasitesinden büyük olamaz.

### 4.5 Etkinlik kaydı ve katılım

- FR-16: Öğrenci yayındaki bir etkinliğe kayıt olur. Kontenjan dolduysa bekleme listesine
  alınır.
- FR-17: Kayıtlı bir öğrenci kaydını iptal ederse bekleme listesindeki ilk öğrenci kayda
  alınır ve bilgilendirilir.
- FR-18: Etkinlik günü kulüp yöneticisi, öğrencinin gösterdiği QR kodu okutarak katılımı
  işaretler.
- FR-19: Etkinlikten sonra katılan öğrenciler etkinliği 1–5 arasında puanlayıp yorum
  yazabilir.

### 4.6 Duyurular ve bildirimler

- FR-20: Kulüp yöneticisi kulüp üyelerine duyuru gönderebilir.
- FR-21: Öğrenci, kayıtlı olduğu etkinlikten 1 gün önce hatırlatma alır.

### 4.7 Raporlar

- FR-22: Yönetici, dönem bazında kulüplerin etkinlik sayısını, toplam katılımcı sayısını ve
  ortalama puanını görür.
- FR-23: Kulüp yöneticisi kendi etkinliklerinin kayıt ve katılım sayılarını görür.

### 4.8 Hesaplar ve giriş

- FR-24: Öğrenciler, personel ve yönetici e-posta adresi ve şifre ile giriş yapar.
- FR-25: Yönetici personel hesabı oluşturabilir ve devre dışı bırakabilir.

## 5. Ekranlar

1. Giriş ve kayıt ekranı
2. Kulüp listesi ve kulüp sayfası
3. Etkinlik takvimi ve etkinlik detayı
4. Öğrencinin kulüplerim ve etkinliklerim sayfası
5. Kulüp paneli (üyeler, duyurular)
6. Etkinlik oluşturma ve düzenleme
7. Katılım işaretleme (QR okutma)
8. Personel onay ekranı (kulüp başvuruları, etkinlik talepleri)
9. Salon yönetimi ve doluluk takvimi
10. Raporlar

## 6. Fonksiyonel Olmayan Gereksinimler

- NFR-1: Etkinlik takvimi 2 saniyeden kısa sürede yüklenmelidir (yaklaşık 200 kulüp ve dönemde
  3.000 etkinlik için).
- NFR-2: Şifreler düz metin olarak saklanmamalıdır.
- NFR-3: Arayüz Türkçe olmalı ve masaüstü ile mobil tarayıcılarda kullanılabilir olmalıdır.
- NFR-4: Öğrencilerin telefon numarası ve öğrenci numarası yalnızca üye oldukları kulübün
  yöneticileri ve personel tarafından görülebilmelidir.
- NFR-5: Bir etkinliğe aynı anda gelen kayıt isteklerinde kontenjan aşılmamalıdır.
- NFR-6: Onay, ret ve iptal işlemleri kim tarafından ve ne zaman yapıldığıyla birlikte
  kaydedilmelidir.

## 7. Veri

Sistem en az şu bilgileri saklar: kulüpler, kulüp başvuruları, üyelikler, etkinlikler, salonlar,
salon rezervasyonları, etkinlik kayıtları, bekleme listeleri, katılım kayıtları, puanlar,
duyurular ve kullanıcı hesapları.
