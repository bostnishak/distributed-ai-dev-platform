Kullanıcının yazdığı İŞ KURALINI Python kodunda denetleyen bir pytest + hypothesis testi yaz.
- Yalnız verilen kaynak dosyalarda gerçekten tanımlı sınıf ve fonksiyonları içe aktar.
- `from hypothesis import given, strategies as st, settings` kullan; `@settings(max_examples=60, deadline=None)`.
- `.example()` KULLANMA. Rastgele girdi yalnız `@given` parametreleriyle gelir. Ardışık işlemler için:
  `@given(st.lists(st.tuples(st.sampled_from(["deposit", "withdraw"]), st.integers(-1000, 1000)), max_size=20))`
  ve her adımdan sonra kuralı `assert` et.
- Kuralı bozabilecek rastgele girdiler üret (negatif sayılar, sıfır, büyük sayılar, ardışık işlemler).
- Kodun bilerek hata fırlattığı geçersiz girdileri `try/except (ValueError, TypeError)` ile kabul et; test yalnız KURAL bozulunca başarısız olsun.
Yalnızca Python kodunu ``` bloğu içinde ver. Kural koddaki hiçbir şeyle ilgili değilse boş yanıt ver.
