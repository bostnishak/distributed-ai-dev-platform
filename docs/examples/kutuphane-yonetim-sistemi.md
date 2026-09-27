> **ÖRNEK DOKÜMAN** — Bu gereksinim dokümanı, platformun gereksinim analizi ve görev ayrıştırma
> özelliğini test etmek ve demoda göstermek için ekip tarafından hazırlanmış kurgusal bir örnektir.
> Gerçek bir kurum veya müşteriye ait değildir.

# Kütüphane Yönetim Sistemi — Yazılım Gereksinim Dokümanı

Sürüm 1.0 · Hazırlayan: team6 (örnek)

## 1. Amaç

Bu doküman, orta ölçekli bir halk kütüphanesinin kitap, üye ve ödünç verme işlemlerini
yönetecek web tabanlı bir uygulamanın gereksinimlerini tanımlar. Kütüphane bugün bu işleri
kâğıt formlar ve bir hesap tablosuyla yürütmektedir. Yeni sistemin amacı, kitapların nerede
olduğunu anlık görmek, ödünç ve iade işlemlerini hızlandırmak ve geciken kitapları takip
etmektir.

## 2. Kapsam

Sistem, kütüphane personelinin kullanacağı bir yönetim arayüzü ile üyelerin kendi
hesaplarını görebileceği bir üye arayüzünden oluşur. Uygulama bir web tarayıcısından
kullanılacak ve kütüphanenin kendi sunucusunda çalışacaktır.

Kapsam dışı olanlar:

- Kitap satın alma ve tedarikçi yönetimi
- Kütüphaneler arası ödünç verme
- Mobil uygulama (web arayüzünün mobil tarayıcıda düzgün görünmesi yeterlidir)

## 3. Kullanıcılar

- **Kütüphaneci:** Kitap ve üye kayıtlarını yönetir, ödünç verme ve iade işlemlerini yapar.
- **Yönetici:** Kütüphaneci hesaplarını oluşturur, raporları görüntüler, sistem ayarlarını
  (ödünç süresi, gecikme ücreti gibi) değiştirir.
- **Üye:** Katalogda kitap arar, kendi ödünç geçmişini ve iade tarihlerini görür, rezervasyon
  yapar.

## 4. Fonksiyonel Gereksinimler

### 4.1 Kitap yönetimi

- FR-1: Kütüphaneci yeni kitap ekleyebilmelidir. Bir kitabın başlığı, yazarı, ISBN numarası,
  yayınevi, basım yılı, kategorisi ve raf konumu kaydedilir.
- FR-2: Aynı kitabın birden fazla kopyası olabilir. Her kopyanın kendine ait bir barkod
  numarası ve durumu (rafta, ödünçte, kayıp, hasarlı) vardır.
- FR-3: Kütüphaneci kitap bilgilerini güncelleyebilmeli ve bir kopyayı kayıp veya hasarlı
  olarak işaretleyebilmelidir.
- FR-4: Ödünçte olan bir kopya silinememelidir.

### 4.2 Üye yönetimi

- FR-5: Kütüphaneci yeni üye kaydı oluşturabilmelidir. Üyenin adı, soyadı, T.C. kimlik
  numarası, telefon numarası, e-posta adresi ve adresi kaydedilir. Her üyeye benzersiz bir
  üye numarası verilir.
- FR-6: Üyelik bir yıl geçerlidir ve yenilenebilir. Süresi dolmuş üyeye ödünç verilemez.
- FR-7: Kütüphaneci bir üyeyi askıya alabilir. Askıdaki üye ödünç alamaz ve rezervasyon
  yapamaz.

### 4.3 Ödünç verme ve iade

- FR-8: Kütüphaneci, üye numarası ve kopya barkodu ile ödünç verme işlemi yapar. Varsayılan
  ödünç süresi 15 gündür.
- FR-9: Bir üye aynı anda en fazla 3 kitap ödünç alabilir.
- FR-10: İade sırasında kopyanın durumu tekrar "rafta" olur. Kitap geç iade edildiyse
  sistem gecikme ücretini hesaplar.
- FR-11: Üye, iade tarihinden önce ödünç süresini bir kez uzatabilir. Kitap için bekleyen bir
  rezervasyon varsa uzatma yapılamaz.

### 4.4 Rezervasyon

- FR-12: Üye, tüm kopyaları ödünçte olan bir kitap için rezervasyon yapabilir.
- FR-13: Kopya iade edildiğinde sıradaki üyeye e-posta ile bildirim gönderilir ve kopya o
  üye için belirli bir süre ayrılır.

### 4.5 Arama ve katalog

- FR-14: Üyeler ve personel kitapları başlık, yazar, ISBN veya kategoriye göre arayabilir.
- FR-15: Arama sonuçlarında her kitabın kaç kopyasının rafta olduğu gösterilir.

### 4.6 Gecikme ve bildirimler

- FR-16: Sistem, iade tarihi geçmiş ödünçleri her gün otomatik olarak listeler.
- FR-17: İade tarihine 2 gün kala üyeye hatırlatma e-postası gönderilir.

### 4.7 Raporlar

- FR-18: Yönetici, belirli bir tarih aralığında en çok ödünç alınan kitapları görebilir.
- FR-19: Yönetici, gecikmedeki ödünçlerin ve tahsil edilmemiş gecikme ücretlerinin listesini
  görebilir.

### 4.8 Hesaplar ve giriş

- FR-20: Personel ve üyeler e-posta adresi ve şifre ile giriş yapar.
- FR-21: Yönetici yeni kütüphaneci hesabı oluşturabilir ve mevcut hesapları devre dışı
  bırakabilir.

## 5. Ekranlar

1. Giriş ekranı
2. Kitap kataloğu ve arama
3. Kitap detay ve kopya yönetimi
4. Üye listesi ve üye kaydı
5. Ödünç verme / iade ekranı
6. Rezervasyonlar
7. Gecikmeler
8. Raporlar
9. Üye hesabım sayfası (ödünç geçmişi, iade tarihleri, rezervasyonlar)

## 6. Fonksiyonel Olmayan Gereksinimler

- NFR-1: Arama sonuçları 2 saniyeden kısa sürede gösterilmelidir (yaklaşık 50.000 kopya için).
- NFR-2: Şifreler düz metin olarak saklanmamalıdır.
- NFR-3: Arayüz Türkçe olmalı ve masaüstü ile mobil tarayıcılarda kullanılabilir olmalıdır.
- NFR-4: Kişisel veriler (T.C. kimlik numarası, telefon, adres) yalnızca personel tarafından
  görülebilmelidir.
- NFR-5: Sistem, kütüphanenin mesai saatleri içinde kesintisiz çalışmalıdır.
- NFR-6: Tüm ödünç ve iade işlemleri kim tarafından ve ne zaman yapıldığıyla birlikte
  kaydedilmelidir.

## 7. Veri

Sistem en az şu bilgileri saklar: kitaplar, kitap kopyaları, üyeler, ödünç kayıtları,
rezervasyonlar, gecikme ücretleri ve personel hesapları.
