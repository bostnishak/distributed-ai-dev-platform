"""Assistant tab logic that does not need a model or the gateway."""

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


class TestRunCode:
    """/run-code needs no gateway or model (plain subprocess isolation), unlike the other
    assistant flows, so it is exercised directly through the client fixture."""

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
