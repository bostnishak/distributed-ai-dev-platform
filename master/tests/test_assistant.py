"""Assistant tab logic that does not need a model or the gateway."""

from assistant import keyword_category_override, parse_classifier_response


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
