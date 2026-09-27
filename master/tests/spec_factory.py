"""Builds a realistic RequirementsSpec for tests (a small library management system)."""

from decompose import RequirementsSpec


def make_spec(**overrides) -> RequirementsSpec:
    data = {
        "project_name": "Kütüphane Yönetim Sistemi",
        "summary": "Kitap ödünç verme takibi",
        "actors": ["Kütüphaneci", "Üye"],
        "entities": [
            {"name": "Kitap", "description": "Kütüphanedeki kitap", "fields": [
                {"name": "baslik", "type": "string", "required": True},
                {"name": "isbn", "type": "string", "required": True},
            ]},
            {"name": "Üye", "description": "Kayıtlı kişi", "fields": [
                {"name": "ad", "type": "string", "required": True},
            ]},
            {"name": "Ödünç", "description": "Ödünç kaydı", "fields": [
                {"name": "iade_tarihi", "type": "date", "required": False},
            ]},
        ],
        "api_endpoints": [
            {"method": "GET", "path": "/api/kitaplar", "description": "Kitapları listele", "entity": "Kitap"},
            {"method": "POST", "path": "/api/uyeler", "description": "Üye ekle", "entity": ""},
            {"method": "POST", "path": "/api/odunc", "description": "Ödünç ver", "entity": "Ödünç"},
            {"method": "GET", "path": "/api/rapor", "description": "Rapor", "entity": ""},
        ],
        "pages": [
            {"name": "Kitap listesi", "description": "Tüm kitaplar", "entities": ["Kitap"]},
            {"name": "Üye kaydı", "description": "Yeni üye", "entities": ["Üye"]},
            {"name": "Ödünç ekranı", "description": "Ödünç ver/al", "entities": ["Ödünç"]},
        ],
        "non_functional": ["Yanıt süresi 2 saniyenin altında olmalı"],
        "open_questions": ["Bir üye aynı anda kaç kitap alabilir?"],
    }
    data.update(overrides)
    return RequirementsSpec.model_validate(data)
