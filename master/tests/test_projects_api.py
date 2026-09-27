import db
import llm
import projects_api
from spec_factory import make_spec


def fake_chat_returning(spec_json: str):
    async def chat(system, user, schema, num_ctx):
        return spec_json

    return chat


def create_with_text(client, text="Kütüphane sistemi: kitap ve üye yönetimi.", name="Kütüphane"):
    return client.post("/api/projects", data={"name": name, "text": text})


def test_create_analyzes_in_background_and_returns_plan(client, monkeypatch):
    monkeypatch.setattr(projects_api, "llm_chat", fake_chat_returning(make_spec().model_dump_json()))
    resp = create_with_text(client)
    assert resp.status_code == 202
    project_id = resp.json()["id"]

    # TestClient runs background tasks before returning, so the analysis is already done.
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["status"] == "decomposed"
    assert project["spec"]["open_questions"] == ["Bir üye aynı anda kaç kitap alabilir?"]
    assert project["chunk_count"] == 1
    assert project["analysis_seconds"] is not None
    tasks = project["tasks"]
    assert tasks[0]["key"] == "T1" and tasks[0]["status"] == "done"
    assert any(t["depends_on"] for t in tasks[1:])

    listed = client.get("/api/projects").json()
    assert listed[0]["id"] == project_id
    assert listed[0]["task_count"] == len(tasks)


def test_upload_markdown_file(client, monkeypatch):
    monkeypatch.setattr(projects_api, "llm_chat", fake_chat_returning(make_spec().model_dump_json()))
    files = {"file": ("gereksinim.md", "# Kütüphane\nKitap ekleme".encode(), "text/markdown")}
    resp = client.post("/api/projects", data={"name": "Dosyadan"}, files=files)
    assert resp.status_code == 202
    project = client.get(f"/api/projects/{resp.json()['id']}").json()
    assert project["source_filename"] == "gereksinim.md"
    assert project["document"].startswith("# Kütüphane")


def test_requires_exactly_one_source(client):
    assert client.post("/api/projects", data={"name": "x"}).status_code == 422
    files = {"file": ("a.txt", b"metin", "text/plain")}
    both = client.post("/api/projects", data={"name": "x", "text": "metin"}, files=files)
    assert both.status_code == 422


def test_rejects_unsupported_file(client):
    files = {"file": ("foto.png", b"\x89PNG", "image/png")}
    assert client.post("/api/projects", data={"name": "x"}, files=files).status_code == 415


def test_model_failure_marks_project_failed(client, monkeypatch):
    async def broken_chat(*_args):
        raise llm.LLMError("Master modeline ulaşılamadı")

    monkeypatch.setattr(projects_api, "llm_chat", broken_chat)
    project_id = create_with_text(client).json()["id"]
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["status"] == "failed"
    assert "ulaşılamadı" in project["error"]
    assert project["tasks"] == []


def test_reanalyze_after_failure(client, monkeypatch):
    async def broken_chat(*_args):
        raise llm.LLMError("geçici hata")

    monkeypatch.setattr(projects_api, "llm_chat", broken_chat)
    project_id = create_with_text(client).json()["id"]

    monkeypatch.setattr(projects_api, "llm_chat", fake_chat_returning(make_spec().model_dump_json()))
    assert client.post(f"/api/projects/{project_id}/reanalyze").status_code == 202
    project = client.get(f"/api/projects/{project_id}").json()
    assert project["status"] == "decomposed"
    assert project["error"] is None


def test_reanalyze_and_delete_blocked_while_analyzing(client, monkeypatch):
    monkeypatch.setattr(projects_api, "llm_chat", fake_chat_returning(make_spec().model_dump_json()))
    project_id = create_with_text(client).json()["id"]
    db.mark_analyzing(project_id)
    assert client.post(f"/api/projects/{project_id}/reanalyze").status_code == 409
    assert client.delete(f"/api/projects/{project_id}").status_code == 409


def test_delete_project(client, monkeypatch):
    monkeypatch.setattr(projects_api, "llm_chat", fake_chat_returning(make_spec().model_dump_json()))
    project_id = create_with_text(client).json()["id"]
    assert client.delete(f"/api/projects/{project_id}").status_code == 204
    assert client.get(f"/api/projects/{project_id}").status_code == 404


def test_restart_recovers_interrupted_analyses(client):
    project_id = db.create_project("Yarım", "metin", None)
    assert projects_api.recover_interrupted() == 1
    project = db.get_project(project_id)
    assert project["status"] == "failed"
    assert project["error"] == projects_api.INTERRUPTED_MESSAGE
