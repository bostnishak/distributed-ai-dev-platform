BACKEND KURALLARI:
- Sahte yanıt yok: her uç nokta gerçek veriyle çalışır ve kalıcılık SQLite (ya da dosya) ile yapılır.
- Girdiler doğrulanır (FastAPI için Pydantic modeli). Eksik ya da yanlış tipte istek 4xx döner, asla 500 değil.
- Bulunamayan kayıt 404, oluşturma 201 döner.
- Tablolar uygulama içe aktarılırken yoksa oluşturulur; mutlak yol kullanma.
- Veritabanı için yalnızca Python'un standart sqlite3 modülü kullanılır; ORM (tortoise, peewee, SQLModel vb.) kullanma ve requirements.txt'ye ekleme.
