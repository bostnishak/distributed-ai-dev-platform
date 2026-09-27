from model_info import collect_host_info, parse_show_response

# Trimmed from real /api/show responses on the master's computer (Ollama 0.34.4, 2026-09-27).
QWEN35_SHOW = {
    "capabilities": ["completion", "vision", "tools", "thinking"],
    "details": {"family": "qwen35", "parameter_size": "4.7B", "quantization_level": "Q4_K_M"},
    "model_info": {"general.architecture": "qwen35", "qwen35.context_length": 262144},
}
CODER_SHOW = {
    "capabilities": ["completion", "tools", "insert"],
    "details": {"family": "qwen2", "parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
    "model_info": {"general.architecture": "qwen2", "qwen2.context_length": 32768},
}


def test_parses_vision_and_thinking_model():
    info = parse_show_response(QWEN35_SHOW)
    assert info == {
        "model_family": "qwen35",
        "parameter_size": "4.7B",
        "quantization": "Q4_K_M",
        "context_length": 262144,
        "capabilities": ["completion", "vision", "tools", "thinking"],
    }


def test_parses_model_without_thinking():
    info = parse_show_response(CODER_SHOW)
    assert info["context_length"] == 32768
    assert "thinking" not in info["capabilities"]


def test_context_length_found_without_architecture_key():
    info = parse_show_response({"model_info": {"llama.context_length": 131072}})
    assert info["context_length"] == 131072
    assert info["capabilities"] == []


def test_missing_fields_do_not_crash():
    assert parse_show_response({})["context_length"] is None


def test_host_info_shape():
    info = collect_host_info()
    assert set(info) == {"hostname", "os", "cpu_count", "ram_gb", "runtime"}
    assert info["ram_gb"] > 0
    assert info["runtime"] in ("native", "docker")
