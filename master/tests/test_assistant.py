"""Assistant tab logic that does not need a model or the gateway."""

import pytest

import config
from assistant import keyword_category_override, parse_classifier_response, try_calculate


class TestKeywordCategoryOverride:
    def test_detects_python_keyword(self):
        assert keyword_category_override("Python'da bir fonksiyon yaz") == "kod"

    def test_detects_uygulama_yap(self):
        assert keyword_category_override("Basit bir hesap makinesi uygulamasi yap") == "kod"

    def test_detects_debug_request(self):
        assert keyword_category_override("Bu kodda hata var, debug et") == "kod"

    def test_no_match_for_general_question(self):
        assert keyword_category_override("Fotosentez nedir?") is None

    def test_no_match_for_emotional_message(self):
        assert keyword_category_override("Isimden kovuldum, ne yapmaliyim?") is None

    def test_case_insensitive(self):
        assert keyword_category_override("PYTHON ile bir script yaz") == "kod"


class TestParseClassifierResponse:
    def test_clean_format(self):
        category, inappropriate = parse_classifier_response("KATEGORI: kod\nUYGUNSUZ: hayir")
        assert category == "kod"
        assert inappropriate is False

    def test_inappropriate_true(self):
        category, inappropriate = parse_classifier_response("KATEGORI: genel\nUYGUNSUZ: evet")
        assert category == "genel"
        assert inappropriate is True

    def test_handles_markdown_bold(self):
        # Seen in real runs (2026-09-25): the model wrapped values in bold markers.
        category, inappropriate = parse_classifier_response("KATEGORI: **kod**\nUYGUNSUZ: **hayir**")
        assert category == "kod"
        assert inappropriate is False

    def test_template_echo_does_not_crash(self):
        # Seen in real runs: the model copied the template verbatim. That must not raise,
        # and a clear UYGUNSUZ value must not block the message.
        category, inappropriate = parse_classifier_response("KATEGORI: kod|analiz|genel\nUYGUNSUZ: hayir")
        assert category in ("kod", "genel")
        assert inappropriate is False

    def test_missing_uygunsuz_field_fails_open(self):
        category, inappropriate = parse_classifier_response("KATEGORI: kod")
        assert category == "kod"
        assert inappropriate is False

    def test_completely_malformed_fails_open(self):
        category, inappropriate = parse_classifier_response("bunun hicbir anlami yok")
        assert category == "genel"
        assert inappropriate is False

    def test_evet_appearing_elsewhere_does_not_trigger_false_positive(self):
        # A stray "evet" outside the UYGUNSUZ line used to trigger a false block.
        text = "KATEGORI: kod\nUYGUNSUZ: hayir\nEvet, bu kod ornegi calisir."
        _category, inappropriate = parse_classifier_response(text)
        assert inappropriate is False


class TestTryCalculate:
    def test_multiplication_with_trailing_question(self):
        assert try_calculate("125*4 kaç eder") == "125*4 = 500"

    def test_division_normalizes_clean_float_to_int(self):
        assert try_calculate("10/2 nedir") == "10/2 = 5"

    def test_parentheses_and_clean_division_becomes_int(self):
        assert try_calculate("(38+7)/3 hesapla") == "(38+7)/3 = 15"

    def test_no_trailing_words_still_works(self):
        assert try_calculate("7+8") == "7+8 = 15"

    def test_caret_power(self):
        assert try_calculate("2^10 kaç eder") == "2^10 = 1024"

    def test_non_arithmetic_prompt_returns_none(self):
        assert try_calculate("Fotosentez nedir?") is None

    def test_bare_number_does_not_trigger(self):
        assert try_calculate("100") is None

    def test_bare_signed_number_does_not_trigger(self):
        assert try_calculate("-5") is None

    def test_division_by_zero_returns_none(self):
        assert try_calculate("5/0 nedir") is None

    def test_huge_exponent_rejected_for_resource_safety(self):
        assert try_calculate("2^999999 kaç eder") is None

    def test_overly_long_expression_rejected(self):
        assert try_calculate("1+" * 150 + "1") is None


class TestRunCodeSwitch:
    def test_disabled_by_default(self, client):
        data = client.get("/api/assistant/config").json()
        assert data["code_run_enabled"] is False
        assert "sandbox_available" in data
        resp = client.post("/api/assistant/run-code", json={"code": "print(1)"})
        assert resp.status_code == 403

    def test_config_reports_enabled(self, client, monkeypatch):
        import sandbox

        monkeypatch.setattr(config, "CODE_RUN_ENABLED", True)
        monkeypatch.setattr(sandbox, "status", lambda: {"available": True, "reason": "ok"})
        data = client.get("/api/assistant/config").json()
        assert data["code_run_enabled"] is True


class TestRunCode:
    """/run-code delegates to SEC-13 container sandbox; tests exercise endpoint contract with mocked or live sandbox."""

    @pytest.fixture(autouse=True)
    def enable_code_run(self, monkeypatch):
        import sandbox

        monkeypatch.setattr(config, "CODE_RUN_ENABLED", True)
        if not sandbox.docker_daemon_ready()[0]:
            def _fake_sandbox_run(code: str, *, timeout_s: int = 10):
                if "AGENT_TOKEN" in code:
                    return {"stdout": "None\n", "stderr": "", "exit_code": 0, "timed_out": False, "docker_available": True}
                if "2 + 2" in code:
                    return {"stdout": "4\n", "stderr": "", "exit_code": 0, "timed_out": False, "docker_available": True}
                if "1 / 0" in code:
                    return {"stdout": "", "stderr": "ZeroDivisionError: division by zero\n", "exit_code": 1, "timed_out": False, "docker_available": True}
                if "sleep(" in code:
                    return {"stdout": "", "stderr": "timed out", "exit_code": 124, "timed_out": True, "docker_available": True}
                return {"stdout": "", "stderr": "", "exit_code": 0, "timed_out": False, "docker_available": True}

            monkeypatch.setattr(sandbox, "docker_daemon_ready", lambda: (True, "mocked"))
            monkeypatch.setattr(sandbox, "status", lambda: {"available": True, "reason": "mocked"})
            monkeypatch.setattr(sandbox, "run_python_code", _fake_sandbox_run)

    def test_master_secrets_not_visible(self, client, monkeypatch):
        monkeypatch.setenv("AGENT_TOKEN", "secret-that-must-not-leak")
        code = "import os; print(os.environ.get('AGENT_TOKEN'))"
        resp = client.post("/api/assistant/run-code", json={"code": code})
        assert resp.json()["stdout"].strip() == "None"

    def test_stdout_captured(self, client):
        resp = client.post("/api/assistant/run-code", json={"code": "print(2 + 2)"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stdout"].strip() == "4"
        assert data["exit_code"] == 0
        assert data["timed_out"] is False

    def test_runtime_error_captured_in_stderr(self, client):
        resp = client.post("/api/assistant/run-code", json={"code": "1 / 0"})
        data = resp.json()
        assert data["exit_code"] != 0
        assert "ZeroDivisionError" in data["stderr"]

    def test_timeout_is_reported(self, client, monkeypatch):
        import assistant

        monkeypatch.setattr(assistant, "CODE_RUN_TIMEOUT_SECONDS", 1)
        resp = client.post("/api/assistant/run-code", json={"code": "import time; time.sleep(5)"})
        assert resp.json()["timed_out"] is True


class TestEnterpriseBackgroundRouting:
    def test_detects_project_build_requests(self):
        from assistant import _detect_project_type, _is_project_build_request

        assert _is_project_build_request("Bana modern bir e-ticaret sitesi yap", None) is True
        assert _is_project_build_request("Python ile uzay oyunu yap exe olsun", None) is True
        assert _is_project_build_request("Dosyalarıyla birlikte bir web sitesi oluştur", None) is True
        assert _is_project_build_request("bana bilgisayarda çalışacak hesap makinesi uygulaması yapabilir misin", None) is True

        ptype, wants_exe = _detect_project_type("bana bilgisayarda çalışacak hesap makinesi uygulaması yapabilir misin")
        assert ptype == "desktop"
        assert wants_exe is True

    def test_ignores_code_only_and_conceptual_questions(self):
        from assistant import _is_project_build_request

        assert _is_project_build_request("Bana hesap makinesi kodunu ver", None) is False
        assert _is_project_build_request("Bu oyunun kod halini ver", None) is False
        assert _is_project_build_request("E-ticaret nedir?", None) is False
        assert _is_project_build_request("Oyun motoru ne demek açıkla", None) is False
        assert _is_project_build_request("Merhaba nasılsın", None) is False


class TestUniversalMultimodalAndDocuments:
    def test_image_processing_and_editing(self, tmp_path, monkeypatch):
        import io

        from PIL import Image

        import config
        import multimodal_studio as mms

        monkeypatch.setattr(config, "DATA_DIR", tmp_path)
        im = Image.new("RGB", (320, 240), (120, 160, 200))
        buf = io.BytesIO()
        im.save(buf, format="PNG")

        res = mms.process_and_edit_image(
            buf.getvalue(),
            'Bu görüntüyü siyah beyaz yap, kontrast artır ve "TEST" yazı ekle',
        )
        assert res["output_size"] == "320x240 px"
        assert len(res["applied_filters"]) >= 2
        assert (tmp_path / "media" / f"{res['file_id']}.png").is_file()

    def test_audio_wav_transcription_metadata(self, tmp_path):
        import io
        import wave

        import multimodal_studio as mms

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 8000)  # 0.5 sec silence

        info = mms.transcribe_audio_bytes("ses_kaydi.wav", buf.getvalue())
        assert info["duration_sec"] == 0.5
        assert info["filename"] == "ses_kaydi.wav"

    def test_detect_document_requests(self):
        import document_factory as df

        assert df.detect_document_request("Bana 12 aylık şirket bütçesi Excel tablosu hazırla", False) == "xlsx"
        assert df.detect_document_request("Kira sözleşmesi Word dosyası oluştur", False) == "docx"
        assert df.detect_document_request("Pazar araştırması PDF raporu çıkar", False) == "pdf"
        assert df.detect_document_request("Merhaba nasılsın", False) is None
