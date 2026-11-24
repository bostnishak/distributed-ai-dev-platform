"""Unseen battery: new prompts of the same kinds as battery.py, written AFTER the fixes, to measure generalisation.

Nothing here was used to tune any code. Usage: python scripts/audit/battery_unseen.py [pattern] [out.jsonl]
"""

import sys

import battery as b

b.CASES.clear()
case = b.case
has, lacks = b.has, b.lacks

case("u-fmt-00", "talimat", "Gökyüzünü 12 kelimeyi geçmeden anlat.", b.words_at_most(16))
case("u-fmt-01", "talimat", "Kısa bir şiir yaz ama 'güneş' kelimesi hiç geçmesin.", lacks(r"güneş"))
case("u-fmt-02", "talimat", "Bana üç maddelik bir alışveriş listesi ver, numaralandırma kullanma, sadece tire kullan.", lacks(r"(?m)^\s*\d+[.)]"))
case("u-code-00", "kod", "Sadece kod ver, açıklama yazma: JavaScript ile bir dizideki en büyük sayıyı bulan fonksiyon.", b.only_code)
case("u-code-01", "kod", "Python'da bir listeyi tersine çeviren fonksiyon yaz. Fonksiyonun adı ters_cevir olsun, sadece kod.", b.code_runs("assert ters_cevir([1, 2, 3]) == [3, 2, 1]"))
case("u-math-00", "araç", "9876 * 5432 işlemini hesapla.", has(r"53[ .,]?646[ .,]?432"))
case("u-math-01", "araç", "Bir hafta kaç dakikadır?", has(r"10[ .,]?080"))
case("u-math-02", "araç", "1234 * 4321 kaç eder?", has(r"5[ .,]?332[ .,]?114"))
case("u-trap-00", "uydurma/cevaplanamaz", "Ayşe Karamanoğlu'nun 2019 tarihli 'Sessiz Kuantum' romanının konusunu özetle.", b.hedges)
case("u-trap-01", "uydurma/cevaplanamaz", "Türkiye'nin 2031 yılı sonundaki kesin nüfusu kaç olacak?", b.hedges)
case("u-trap-02", "uydurma/cevaplanamaz", "Mars'ta 1987'de kurulan 'Olympus Bankası'nın ilk genel müdürü kimdi?", b.hedges)
case("u-fact-00", "olgusal", "Ankara hangi ülkenin başkentidir?", has(r"Türkiye"))
case("u-fact-01", "olgusal", "Su kaç derecede kaynar (deniz seviyesinde, Celsius)?", has(r"\b100\b"))
case("u-make-00", "üretim", "Kedi bakımı hakkında 5 slaytlık bir sunum hazırla.", lambda r: (any("pptx" in b.json.dumps(e) or "slide" in b.json.dumps(e).lower() for e in r["events"]), "sunum çıktısı yok"))
case("u-make-01", "üretim", "Aylık bütçem için bir Excel tablosu hazırla.", lambda r: (any("xlsx" in b.json.dumps(e) for e in r["events"]), "xlsx çıktısı yok"))
case("u-lang-00", "dil", "Answer in English only: what is the capital of Japan?", has(r"Tokyo"))

if __name__ == "__main__":
    print(len(b.CASES), "cases")
    b.run_all(only=sys.argv[1] if len(sys.argv) > 1 else None, out=sys.argv[2] if len(sys.argv) > 2 else "battery_unseen.jsonl")
