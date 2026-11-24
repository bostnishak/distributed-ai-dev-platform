"""Canonical Pydantic response contracts and OpenAPI description registry (SMA/SMB/ACK/ACL)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.datastructures import DefaultPlaceholder
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field


class ApiEnvelope(BaseModel):
    """Base contract for JSON API responses preserving explicit OpenAPI schema visibility."""

    model_config = ConfigDict(extra="allow")


class HealthResponse(ApiEnvelope):
    status: str = Field(default="ok", description="Servis sağlık durumu")


class ReadyResponse(ApiEnvelope):
    status: str = Field(default="ok", description="Hazırlık durumu (ok | degraded)")
    components: dict[str, Any] = Field(default_factory=dict, description="Alt bileşen sağlık özetleri")


class AdminResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="İşlem başarı bayrağı")


class AgentResponse(ApiEnvelope):
    agents: list[dict[str, Any]] | None = Field(default=None, description="Kayıtlı ajan listesi")


class AuthResponse(ApiEnvelope):
    authenticated: bool | None = Field(default=None, description="Oturum durumu")
    user: dict[str, Any] | None = Field(default=None, description="Oturum sahibi bilgisi")


class ProjectResponse(ApiEnvelope):
    projects: list[dict[str, Any]] | None = Field(default=None, description="Proje listesi")


class AssistantResponse(ApiEnvelope):
    content: str | None = Field(default=None, description="Asistan yanıt metni")


class UserProfileResponse(ApiEnvelope):
    user_id: str | None = Field(default=None, description="Kullanıcı profil kimliği")


class MemoryResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="Hafıza işlemi durumu")


class RagResponse(ApiEnvelope):
    results: list[dict[str, Any]] | None = Field(default=None, description="RAG arama veya belge sonuçları")


class HallucinationResponse(ApiEnvelope):
    passed: bool | None = Field(default=None, description="Doğrulama sonucu")


class OrchestratorResponse(ApiEnvelope):
    intent: str | None = Field(default=None, description="Sınıflandırılan niyet veya yürütme sonucu")


class GatewayResponse(ApiEnvelope):
    status: str | None = Field(default=None, description="LLM geçidi durumu veya model listesi")


class StudioResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="Stüdyo çıktı sonucu")


class DistributedResponse(ApiEnvelope):
    status: str | None = Field(default=None, description="Dağıtık yürütme durumu")


class DomainResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="Alan motoru sonucu")


class MlOpsResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="MLOps işlem sonucu")


class UxResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="Arayüz servis yanıtı")


class OrgResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="Organizasyon ve RBAC işlem sonucu")
    orgs: list[dict[str, Any]] | None = Field(default=None, description="Kullanıcı organizasyon listesi")


class PrivacyResponse(ApiEnvelope):
    ok: bool | None = Field(default=None, description="Gizlilik, şifreleme veya RTBF kanıt sonucu")
    proof_id: str | None = Field(default=None, description="Kriptografik silme kanıt kimliği")


_PREFIX_MODEL_MAP: tuple[tuple[str, type[ApiEnvelope], str], ...] = (
    ("/health", HealthResponse, "Master servisinin canlılık (liveness) kontrolünü döndürür."),
    ("/ready", ReadyResponse, "Veritabanı, disk, Ollama ve sandbox bileşenlerinin hazırlık durumunu döndürür."),
    ("/metrics", AdminResponse, "Prometheus biçiminde veya özet çalışma metriklerini döndürür."),
    ("/api/admin", AdminResponse, "Yönetim, gözlemlenebilirlik ve bakım işlemlerini yürütür."),
    ("/api/backup", AdminResponse, "Veritabanı yedekleme ve geri yükleme işlemlerini yürütür."),
    ("/api/audit", AdminResponse, "Değiştirilemez güvenlik ve işlem denetim kayıtlarını döndürür."),
    ("/api/agents", AgentResponse, "Dağıtık ajan kaydı, kalp atışı, anahtar ve durum işlemlerini yönetir."),
    ("/api/auth/orgs", OrgResponse, "Çoklu kullanıcı organizasyon, davet ve RBAC yetki matrisi işlemlerini yönetir."),
    ("/api/auth", AuthResponse, "Kullanıcı oturumu, giriş, kurulum ve kimlik doğrulama akışlarını yönetir."),
    ("/api/privacy", PrivacyResponse, "Alan düzeyi şifreleme, zararlı yazılım taraması ve RTBF silme kanıtlarını yönetir."),
    ("/api/projects", ProjectResponse, "Scrum proje oluşturma, görev ayrıştırma ve durum işlemlerini yönetir."),
    ("/api/tasks", ProjectResponse, "Ajan görev dağıtımı, kiralama ve sonuç bildirimlerini yönetir."),
    ("/api/output", ProjectResponse, "Üretilen proje çıktıları ve artefakt indirme işlemlerini sunar."),
    ("/api/perf", DistributedResponse, "Performans, gecikme ve model karşılaştırma ölçümlerini sunar."),
    ("/api/assistant", AssistantResponse, "Yerel yapay zeka asistanı sohbet, medya ve yapılandırma uç noktası."),
    ("/api/cnc", DomainResponse, "Teknik çizim balonlama, tolerans ve CNC üretim raporlama işlemlerini yürütür."),
    ("/api/studio", StudioResponse, "Kod çalışma alanı (IDE), dosya düzenleme, derleme ve önizleme işlemlerini yönetir."),
    ("/api/studios", StudioResponse, "Araştırma, sunum, belge, veri bilimi ve medya stüdyo işlemlerini yürütür."),
    ("/api/factory", StudioResponse, "Çok dosyalı yazılım fabrikası planlama, üretim ve doğrulama uç noktası."),
    ("/api/games", StudioResponse, "Oyun stüdyosu şablon, derleme ve kalite doğrulama uç noktası."),
    ("/api/domains", DomainResponse, "Finans, hukuk, sağlık, mühendislik ve akademik alan motoru uç noktası."),
    ("/api/distributed", DistributedResponse, "Dağıtık ajan yönlendirme, görev çakışması ve kaos dayanıklılık uç noktası."),
    ("/api/gateway", GatewayResponse, "LLM geçidi model kaydı, sağlık, önbellek ve çağrı izi uç noktası."),
    ("/api/orchestrator", OrchestratorResponse, "Niyet sınıflandırma, planlama, araç çağrısı ve mod sözleşmesi uç noktası."),
    ("/api/rag", RagResponse, "Hibrit bilgi tabanı (BM25 + vektör + grafik) ekleme ve arama uç noktası."),
    ("/api/hallucination", HallucinationResponse, "İddia doğrulama, NLI, atıf zorunluluğu ve eval raporu uç noktası."),
    ("/api/ml", MlOpsResponse, "Tercih toplama, kalibrasyon, deney takibi ve model kapısı uç noktası."),
    ("/api/memory", MemoryResponse, "Semantik hafıza ve konuşma sıkıştırma işlemlerini yönetir."),
    ("/api/mcp", AdminResponse, "Harici MCP bağlayıcı yönetimi ve güvenli araç çağrısı uç noktası."),
    ("/api/user", UserProfileResponse, "Kullanıcı profili, ayarlar, sohbet geçmişi ve gizlilik işlemlerini yönetir."),
    ("/api/ux", UxResponse, "Sağlık sihirbazı, ayar şeması, paylaşım ve SLO pano servisi."),
    ("/api/security", AdminResponse, "2FA TOTP, parola politikası, oturum yönetimi, IP izin listesi ve sır tarama servisi."),
    ("/api/tools", DomainResponse, "Eğitim stüdyosu ve doğrulanmış alan hesaplayıcıları (vergi, metraj, malzeme, devre, sağlık)."),
    ("/api/productivity", StudioResponse, "Sohbet, kod, veri, medya, takvim, ajan ve operasyon üretkenlik araçları."),
    ("/api/master", GatewayResponse, "Master düğüm ve yerel LLM çalışma durumunu döndürür."),
)


def _match_contract(path: str) -> tuple[type[ApiEnvelope], str]:
    for prefix, model_cls, default_desc in _PREFIX_MODEL_MAP:
        if path == prefix or path.startswith(prefix + "/"):
            return model_cls, default_desc
    return ApiEnvelope, f"`{path}` uç noktası için yapılandırılmış JSON yanıtı döndürür."


def _is_unset_response_model(val: Any) -> bool:
    return val is None or isinstance(val, DefaultPlaceholder)


def _ensure_route_contract(route: APIRoute) -> None:
    model_cls, default_desc = _match_contract(route.path)
    if not (route.description or (route.endpoint.__doc__ or "").strip()):
        methods = "/".join(sorted(m for m in (route.methods or set()) if m != "HEAD"))
        route.description = f"{methods} {route.path}: {default_desc}"
    if _is_unset_response_model(route.response_model) and route.path != "/":
        route.response_model = model_cls


def _register_openapi_components(schema: dict[str, Any]) -> None:
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    models: list[type[ApiEnvelope]] = [*(m for _, m, _ in _PREFIX_MODEL_MAP), ApiEnvelope]
    for model_cls in models:
        name = model_cls.__name__
        if name not in components:
            components[name] = model_cls.model_json_schema(ref_template="#/components/schemas/{model}")


def _enrich_openapi_paths(schema: dict[str, Any]) -> None:
    http_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    for path, methods in (schema.get("paths") or {}).items():
        model_cls, default_desc = _match_contract(path)
        ref = {"$ref": f"#/components/schemas/{model_cls.__name__}"}
        for method, op in methods.items():
            if method.upper() not in http_methods:
                continue
            if not (op.get("description") or "").strip():
                op["description"] = f"{method.upper()} {path}: {default_desc}"
            resp_200 = op.setdefault("responses", {}).setdefault("200", {"description": "Successful Response"})
            app_json = resp_200.setdefault("content", {}).setdefault("application/json", {})
            if not app_json.get("schema"):
                app_json["schema"] = ref


def attach_openapi_contracts(app: FastAPI) -> None:
    """Ensure every registered APIRoute has a concrete description and OpenAPI 200 JSON schema."""
    for route in app.routes:
        if isinstance(route, APIRoute):
            _ensure_route_contract(route)

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        _register_openapi_components(schema)
        _enrich_openapi_paths(schema)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    app.openapi_schema = None


def validate_openapi_contracts(app: FastAPI) -> dict[str, Any]:
    """EPK-04: Verify every OpenAPI operation has a description and typed 200 JSON schema."""
    schema = app.openapi()
    missing_desc: list[str] = []
    missing_schema: list[str] = []
    total_ops = 0
    for path, methods in (schema.get("paths") or {}).items():
        for method, op in methods.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            total_ops += 1
            if not (op.get("description") or "").strip():
                missing_desc.append(f"{method.upper()} {path}")
            resp_200 = (op.get("responses") or {}).get("200") or {}
            json_schema = ((resp_200.get("content") or {}).get("application/json") or {}).get("schema")
            if not json_schema:
                missing_schema.append(f"{method.upper()} {path}")
    return {
        "ok": not missing_desc and not missing_schema,
        "total_operations": total_ops,
        "schema_count": len((schema.get("components") or {}).get("schemas") or {}),
        "missing_descriptions": missing_desc,
        "missing_schemas": missing_schema,
    }
