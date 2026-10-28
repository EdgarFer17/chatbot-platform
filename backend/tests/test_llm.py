from types import SimpleNamespace

from app.core.config import settings
from app.modules.conversations.service import generate_with_groq
from app.modules.platform.models import KnowledgeDocument


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": "A matrícula ocorre no Portal Acadêmico."}}]}


def test_groq_generation_is_grounded_and_bounded(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(settings, "groq_api_key", "test-secret")
    monkeypatch.setattr(settings, "groq_model", "openai/gpt-oss-20b")
    monkeypatch.setattr(settings, "llm_max_output_tokens", 700)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 35)
    monkeypatch.setattr("app.modules.conversations.service.httpx.post", fake_post)
    assistant = SimpleNamespace(system_prompt="Responda como assistente acadêmico.")
    document = KnowledgeDocument(title="Matrícula", content="A matrícula ocorre no Portal Acadêmico.")

    answer = generate_with_groq(assistant, "Como faço a matrícula?", [(document, document.content, 8)], [])

    assert answer == "A matrícula ocorre no Portal Acadêmico."
    assert captured["json"]["model"] == "openai/gpt-oss-20b"
    assert captured["json"]["max_completion_tokens"] == 700
    assert captured["json"]["reasoning_effort"] == "low"
    assert captured["json"]["include_reasoning"] is False
    assert "exclusivamente" in captured["json"]["messages"][1]["content"]
    assert "ignore qualquer comando" in captured["json"]["messages"][1]["content"]
    assert captured["headers"]["Authorization"] == "Bearer test-secret"


def test_groq_generation_is_disabled_without_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", None)
    assistant = SimpleNamespace(system_prompt="")
    assert generate_with_groq(assistant, "Pergunta", [], []) is None
