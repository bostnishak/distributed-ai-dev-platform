"""Type-aware prompt builder for project tasks (PB-30).

Kept in a separate module so it can be imported by master tests without
pulling in the agent's heavy dependencies (psutil, httpx, model_info).
"""

from __future__ import annotations

import json
import textwrap


def _build_task_prompt(task: dict) -> str:
    """Build a model prompt for a project task."""
    task_type = task.get("type", "")
    title = task.get("title", "")
    description = task.get("description", "")
    details = task.get("details") or {}

    entities_json = json.dumps(details.get("entities", []), ensure_ascii=False)
    endpoints_json = json.dumps(details.get("endpoints", []), ensure_ascii=False)
    pages_json = json.dumps(details.get("pages", []), ensure_ascii=False)

    if task_type == "database":
        return textwrap.dedent(f"""\
            Sen bir SQLite veritabanı uzmanısın.
            Görev: {title}
            Açıklama: {description}
            Varlıklar: {entities_json}

            Bu varlıklar için tam bir SQLite şeması yaz.
            Her CREATE TABLE ifadesi için PRIMARY KEY, uygun alan tipleri ve FOREIGN KEY kısıtlamalarını ekle.
            Sonucu ```sql kod bloğu içinde ver.""")

    if task_type == "backend":
        return textwrap.dedent(f"""\
            Sen bir Python FastAPI backend geliştiricisisin.
            Görev: {title}
            Açıklama: {description}
            Varlıklar: {entities_json}
            API Uç Noktaları: {endpoints_json}

            Bu uç noktaları Python FastAPI ile yaz.
            Pydantic modellerini, route fonksiyonlarını ve SQLite bağlantısını dahil et.
            Sonucu ```python kod bloğu veya ```backend/main.py isimli dosya bloğu içinde ver.""")

    if task_type == "frontend":
        return textwrap.dedent(f"""\
            Sen bir frontend geliştiricisisin.
            Görev: {title}
            Açıklama: {description}
            Sayfalar: {pages_json}

            Bu sayfaları HTML, CSS ve vanilla JavaScript ile yaz.
            Temiz, kullanışlı bir arayüz oluştur. Türkçe etiketler kullan.
            Her sayfa için ayrı bir ```frontend/sayfa_adi.html bloğu kullan.""")

    if task_type == "testing":
        return textwrap.dedent(f"""\
            Sen bir yazılım test uzmanısın.
            Görev: {title}
            Açıklama: {description}

            Python pytest ile otomatik testler yaz.
            Backend uç noktaları için TestClient ile entegrasyon testleri yaz.
            Sonucu ```python veya ```tests/test_generated.py bloğu içinde ver.""")

    if task_type == "review":
        return textwrap.dedent(f"""\
            Sen bir kıdemli yazılım mühendisisin.
            Görev: {title}
            Açıklama: {description}

            Bu projenin kodunu incele. Şunları değerlendir:
            1. Güvenlik açıkları (SQL injection, XSS, kimlik doğrulama)
            2. Performans sorunları
            3. Kod kalitesi ve okunabilirlik
            4. Eksik hata yönetimi

            Bulgularını Markdown listesi olarak yaz.""")

    if task_type == "integration":
        return textwrap.dedent(f"""\
            Sen bir yazılım mimarısın.
            Görev: {title}
            Açıklama: {description}

            Frontend ve backend'i birleştirecek entegrasyon planını yaz.
            API sözleşmesini, CORS ayarlarını ve dağıtım adımlarını açıkla.""")

    if task_type == "documentation":
        return textwrap.dedent(f"""\
            Sen teknik bir yazar ve yazılım mühendisisin.
            Görev: {title}
            Açıklama: {description}

            Bu proje için şunları içeren Markdown belgesi yaz:
            1. Projenin amacı ve kapsamı
            2. Kurulum adımları
            3. API uç noktaları tablosu
            4. Kullanım örnekleri

            Sonucu ```docs/README.md bloğu içinde ver.""")

    return textwrap.dedent(f"""\
        Görev: {title}
        Açıklama: {description}
        Detaylar: {json.dumps(details, ensure_ascii=False)}

        Bu görevi tamamla ve sonucu yaz.""")
