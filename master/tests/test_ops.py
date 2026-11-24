"""OPS-01/02/03/11/18/19: logging, metrics, readiness, flags, request limits and error grouping."""

import asyncio
import json
import logging

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import config
import db
import dbconn
import error_tracker
import features
import logging_setup
import maintenance
import metrics
import ops
import readiness

pytestmark = pytest.mark.integration

REMOTE = ("100.84.159.80", 50000)


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "platform.db")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    db.init_db()
    metrics.reset()
    return tmp_path


def make_app(max_body=1000):
    app = FastAPI()
    app.add_middleware(ops.ObservabilityMiddleware, max_body_bytes=max_body)
    app.include_router(ops.router)

    @app.get("/ok")
    async def ok():
        return {"id": logging_setup.request_id_var.get()}

    @app.get("/items/{item_id}")
    async def item(item_id: int):
        return {"item": item_id}

    @app.get("/boom")
    async def boom():
        raise ValueError("kimlik no 12345678901 patladı")

    @app.post("/echo")
    async def echo(request: Request):
        return {"size": len(await request.body())}

    return app


class TestLogging:
    def test_a_record_is_one_json_line_carrying_the_request_id(self):
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "merhaba %s", ("dünya",), None)
        token = logging_setup.request_id_var.set("req-123456789")
        try:
            logging_setup.ContextFilter().filter(record)
            entry = json.loads(logging_setup.JsonFormatter().format(record))
        finally:
            logging_setup.request_id_var.reset(token)
        assert entry["msg"] == "merhaba dünya" and entry["request_id"] == "req-123456789"
        assert entry["level"] == "INFO" and entry["ts"].endswith("+00:00")

    def test_exceptions_and_extra_fields_are_included(self):
        try:
            raise RuntimeError("kötü")
        except RuntimeError:
            import sys
            record = logging.LogRecord("x", logging.ERROR, __file__, 1, "hata", (), sys.exc_info())
        record.path = "/api/x"
        entry = json.loads(logging_setup.JsonFormatter().format(record))
        assert "RuntimeError: kötü" in entry["exc"] and entry["extra"]["path"] == "/api/x"

    def test_configure_is_repeatable_and_attaches_the_redaction_filter(self, tmp_path):
        logging_setup.configure(level="WARNING", json_output=True, log_file=tmp_path / "logs" / "app.log")
        logging_setup.configure(level="WARNING", json_output=True, log_file=tmp_path / "logs" / "app.log")
        ours = [h for h in logging.getLogger().handlers if getattr(h, "_cm6453", False)]
        assert len(ours) == 2
        import log_sanitizer

        assert all(any(isinstance(f, log_sanitizer.SecretAndPIIRedactingFilter) for f in h.filters) for h in ours)
        logging.getLogger("t").warning("satır")
        for handler in ours:
            handler.flush()
        assert (tmp_path / "logs" / "app.log").read_text(encoding="utf-8").count("satır") == 1
        for handler in ours:
            logging.getLogger().removeHandler(handler)
            handler.close()


class TestMetrics:
    def test_counters_gauges_and_histograms_render_in_prometheus_format(self):
        metrics.reset()
        metrics.inc("demo_total", route="/a", status="200")
        metrics.inc("demo_total", 2, route="/a", status="200")
        metrics.gauge("demo_level", 7)
        metrics.observe("demo_seconds", 0.03, route="/a")
        metrics.observe("demo_seconds", 3.0, route="/a")
        text = metrics.render()
        assert 'demo_total{route="/a",status="200"} 3' in text
        assert "demo_level 7" in text
        assert 'demo_seconds_bucket{route="/a",le="0.05"} 1' in text
        assert 'demo_seconds_bucket{route="/a",le="+Inf"} 2' in text
        assert 'demo_seconds_sum{route="/a"} 3.03' in text and 'demo_seconds_count{route="/a"} 2' in text
        assert "# TYPE demo_total counter" in text and "process_uptime_seconds" in text

    def test_label_values_are_escaped_and_the_series_count_is_capped(self):
        metrics.reset()
        metrics.inc("esc_total", route='a"b\\c')
        assert 'route="a\\"b\\\\c"' in metrics.render()
        for i in range(metrics.MAX_SERIES + 50):
            metrics.inc("flood_total", n=str(i))
        assert metrics.render().count("flood_total{") <= metrics.MAX_SERIES
        metrics.reset()

    def test_timer_records_a_duration(self):
        metrics.reset()
        with metrics.timer("work_seconds", job="x"):
            pass
        assert 'work_seconds_count{job="x"} 1' in metrics.render()


class TestMiddleware:
    def test_every_response_carries_a_request_id_that_is_visible_to_the_handler(self, database):
        client = TestClient(make_app())
        response = client.get("/ok")
        assert response.headers["x-request-id"] == response.json()["id"] and len(response.json()["id"]) == 16

    def test_a_well_formed_incoming_id_is_kept_and_a_bad_one_is_replaced(self, database):
        client = TestClient(make_app())
        assert client.get("/ok", headers={"X-Request-ID": "trace-abc-12345"}).headers["x-request-id"] == "trace-abc-12345"
        replaced = client.get("/ok", headers={"X-Request-ID": "bad id\x7f!"}).headers["x-request-id"]
        assert replaced != "bad id" and len(replaced) == 16

    def test_metrics_use_route_templates_not_raw_paths(self, database):
        client = TestClient(make_app())
        for n in (1, 2, 3):
            client.get(f"/items/{n}")
        client.get("/nope")
        text = metrics.render()
        assert 'http_requests_total{method="GET",route="/items/{item_id}",status="200"} 3' in text
        assert "/items/1" not in text
        assert 'route="unmatched",status="404"' in text
        assert "http_request_duration_seconds_count" in text

    def test_an_unhandled_error_is_grouped_masked_and_counted(self, database):
        client = TestClient(make_app(), raise_server_exceptions=False)
        assert client.get("/boom").status_code == 500
        assert client.get("/boom").status_code == 500
        errors = error_tracker.recent()
        assert len(errors) == 1 and errors[0]["count"] == 2 and errors[0]["kind"] == "ValueError"
        assert errors[0]["route"] == "/boom" and "12345678901" not in errors[0]["message"]
        assert 'errors_total{kind="ValueError"} 2' in metrics.render()

    def test_a_declared_oversized_body_is_refused_before_the_route_runs(self, database):
        client = TestClient(make_app(max_body=100))
        response = client.post("/echo", content=b"x" * 500)
        assert response.status_code == 413 and "x-request-id" in response.headers
        assert client.post("/echo", content=b"x" * 50).json() == {"size": 50}
        assert 'reason="body_too_large"' in metrics.render()

    def test_a_chunked_body_without_a_length_is_cut_off_at_the_limit(self, database):
        client = TestClient(make_app(max_body=100))

        def chunks():
            for _ in range(20):
                yield b"y" * 20

        assert client.post("/echo", content=chunks()).status_code == 413

    def test_streaming_responses_are_not_buffered(self, database):
        from fastapi.responses import StreamingResponse

        app = make_app()

        @app.get("/stream")
        async def stream():
            async def parts():
                for i in range(3):
                    yield f"data: {i}\n\n"
            return StreamingResponse(parts(), media_type="text/event-stream")

        response = TestClient(app).get("/stream")
        assert response.text == "data: 0\n\ndata: 1\n\ndata: 2\n\n" and "x-request-id" in response.headers


class TestErrorTracker:
    def raise_from(self, function):
        try:
            function()
        except Exception as exc:
            return exc

    def test_same_bug_same_fingerprint_different_route_or_type_differs(self):
        def a():
            raise ValueError("x")

        first, second = self.raise_from(a), self.raise_from(a)
        assert error_tracker.fingerprint(first, "/r") == error_tracker.fingerprint(second, "/r")
        assert error_tracker.fingerprint(first, "/r") != error_tracker.fingerprint(first, "/s")
        assert error_tracker.fingerprint(first, "/r") != error_tracker.fingerprint(self.raise_from(lambda: 1 / 0), "/r")

    def test_long_messages_are_truncated_and_old_rows_pruned(self, database):
        exc = self.raise_from(lambda: (_ for _ in ()).throw(RuntimeError("a" * 5000)))
        error_tracker.record(exc, "/x")
        assert len(error_tracker.recent()[0]["message"]) <= error_tracker.MAX_MESSAGE
        with dbconn.connection(config.DB_PATH) as conn:
            conn.execute("UPDATE error_events SET last_seen = '2020-01-01T00:00:00+00:00'")
        assert error_tracker.prune(30) == 1 and error_tracker.recent() == []

    def test_recording_never_raises_even_when_the_database_is_unusable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DB_PATH", tmp_path)  # a folder, not a database file
        assert error_tracker.record(ValueError("x"), "/x") is None


class TestFeatures:
    def test_everything_experimental_starts_off_and_unknown_flags_are_off(self, database):
        features.ensure_registered()
        assert not any(f["enabled"] for f in features.snapshot().values())
        assert features.is_enabled("yok_boyle_bir_sey") is False

    def test_global_switch_and_per_user_override(self, database):
        features.set_flag("graph_rag", True)
        assert features.is_enabled("graph_rag") and features.is_enabled("graph_rag", "ayse")
        features.set_flag("graph_rag", False, owner="ayse")
        assert not features.is_enabled("graph_rag", "ayse") and features.is_enabled("graph_rag", "berk")

    def test_unknown_flags_cannot_be_set_and_registering_twice_keeps_state(self, database):
        with pytest.raises(KeyError):
            features.set_flag("uydurma", True)
        features.set_flag("web_search", True)
        features.ensure_registered()
        assert features.is_enabled("web_search")


class TestReadiness:
    def fake_llm(self, monkeypatch, reachable=True, model=True):
        import llm

        async def status():
            return {"model": "qwen3.5:4b", "reachable": reachable, "model_available": model}

        monkeypatch.setattr(llm, "status", status)

    def run(self):
        return asyncio.run(readiness.check_all())

    def test_everything_available_is_ok(self, database, monkeypatch):
        self.fake_llm(monkeypatch)
        monkeypatch.setattr(maintenance, "status", lambda: {"running": True, "last_error": None, "rounds": 3})
        import sandbox

        monkeypatch.setattr(sandbox, "status", lambda: {"available": True, "reason": "Docker aktif"})
        result = self.run()
        assert result["status"] == "ok" and {"database", "disk", "ollama", "housekeeping", "sandbox"} == set(result["components"])

    def test_a_missing_model_server_degrades_but_does_not_take_the_service_down(self, database, monkeypatch):
        self.fake_llm(monkeypatch, reachable=False)
        result = self.run()
        assert result["status"] in ("degraded", "down") and result["components"]["ollama"]["status"] == "degraded"
        assert "ulaşılamıyor" in result["components"]["ollama"]["detail"]

    def test_a_missing_model_is_named(self, database, monkeypatch):
        self.fake_llm(monkeypatch, model=False)
        assert "yüklü değil" in self.run()["components"]["ollama"]["detail"]

    def test_low_disk_degrades_and_nearly_no_disk_is_down(self, database, monkeypatch):
        import collections

        usage = collections.namedtuple("usage", "total used free")
        monkeypatch.setattr(readiness.shutil, "disk_usage", lambda _p: usage(10**12, 10**12, 100 * 1024 * 1024))
        assert readiness.disk()["status"] == "degraded"
        monkeypatch.setattr(readiness.shutil, "disk_usage", lambda _p: usage(10**12, 10**12, 10 * 1024 * 1024))
        assert readiness.disk()["status"] == "down"

    def test_an_unwritable_database_is_down(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DB_PATH", tmp_path)
        assert readiness.database()["status"] == "down"

    def test_a_failed_housekeeping_round_is_reported(self, monkeypatch):
        monkeypatch.setattr(maintenance, "status", lambda: {"running": True, "last_error": "RuntimeError: x", "rounds": 1})
        assert "son tur hatalı" in readiness.housekeeping()["detail"]

    def test_runbook_links_appear_only_when_the_file_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr(readiness, "RUNBOOKS", tmp_path)
        assert "runbook" not in readiness._result("down", "x", "disk-full")
        (tmp_path / "disk-full.md").write_text("# Disk dolu", encoding="utf-8")
        assert readiness._result("down", "x", "disk-full")["runbook"] == "docs/runbooks/disk-full.md"


class TestAdminEndpoints:
    def make(self, remote=False):
        return TestClient(make_app(), client=REMOTE if remote else ("127.0.0.1", 50000))

    def test_ready_shows_details_locally_and_only_the_verdict_to_others(self, database, monkeypatch):
        import llm

        async def status():
            return {"model": "m", "reachable": True, "model_available": True}

        monkeypatch.setattr(llm, "status", status)
        assert "components" in self.make().get("/ready").json()
        assert set(self.make(remote=True).get("/ready").json()) == {"status"}

    def test_a_down_service_answers_503(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DB_PATH", tmp_path)
        monkeypatch.setattr(config, "DATA_DIR", tmp_path)
        assert self.make().get("/ready").status_code == 503

    @pytest.mark.parametrize("path", ["/metrics", "/api/admin/errors", "/api/admin/features", "/api/admin/events",
                                      "/api/admin/maintenance"])
    def test_admin_endpoints_refuse_remote_callers(self, database, path):
        assert self.make(remote=True).get(path).status_code == 403
        assert self.make().get(path).status_code == 200

    def test_flags_can_be_switched_by_a_trusted_caller_only(self, database):
        assert self.make(remote=True).put("/api/admin/features/graph_rag", json={"enabled": True}).status_code == 403
        assert self.make().put("/api/admin/features/graph_rag", json={"enabled": True}).json()["enabled"] is True
        assert self.make().put("/api/admin/features/uydurma", json={"enabled": True}).status_code == 404

    def test_events_endpoint_filters_and_limits(self, database):
        with dbconn.connection(config.DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            for kind in ("assigned", "failed", "assigned"):
                conn.execute("INSERT INTO events (event_type, created_at) VALUES (?, '2026-11-01T00:00:00+00:00')", (kind,))
        body = self.make().get("/api/admin/events", params={"event_type": "assigned", "limit": 1}).json()
        assert len(body["events"]) == 1 and body["events"][0]["event_type"] == "assigned"
        assert self.make().get("/api/admin/events", params={"limit": 9999}).status_code == 422


class TestRealApplication:
    def test_the_real_app_exposes_ready_and_stamps_request_ids(self, client):
        response = client.get("/health")
        assert response.status_code == 200 and "x-request-id" in response.headers
        assert client.get("/ready").status_code in (200, 503)
        assert "http_requests_total" in client.get("/metrics").text
