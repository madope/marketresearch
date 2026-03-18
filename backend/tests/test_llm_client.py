from app.core.config import Settings
from app.services.ark_client import VolcengineArkClient
from app.services.llm_client import LLMClient


def test_llm_client_uses_kimi_provider_when_configured(monkeypatch) -> None:
    settings = Settings(
        llm_provider="kimi",
        kimi_api_key="test-kimi-key",
    )
    monkeypatch.setattr("app.services.llm_client.get_settings", lambda: settings)

    client = LLMClient()

    assert client.provider_name == "kimi"
    assert client._provider.__class__.__name__ == "KimiClient"


def test_llm_client_uses_volcengine_provider_when_configured(monkeypatch) -> None:
    settings = Settings(
        llm_provider="volcengine",
        ark_api_key="test-ark-key",
    )
    monkeypatch.setattr("app.services.llm_client.get_settings", lambda: settings)

    client = LLMClient()

    assert client.provider_name == "volcengine"
    assert client._provider.__class__.__name__ == "VolcengineArkClient"


def test_llm_client_falls_back_when_volcengine_not_enabled(monkeypatch) -> None:
    settings = Settings(
        llm_provider="volcengine",
        ark_api_key=None,
    )
    monkeypatch.setattr("app.services.llm_client.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.get_settings", lambda: settings)

    client = LLMClient()
    result = client.generate_json("test", fallback={"ok": True})

    assert result.status == "fallback"
    assert result.value == {"ok": True}
    assert "模型未启用" in (result.message or "")


def test_volcengine_ark_client_uses_chat_completions_for_text(monkeypatch) -> None:
    class FakeCompletions:
        def __init__(self) -> None:
            self.called = False

        def create(self, **kwargs):
            self.called = True
            return type(
                "Response",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {"message": type("Message", (), {"content": "ok"})()},
                        )
                    ]
                },
            )()

    class FakeOpenAI:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    settings = Settings(
        llm_provider="volcengine",
        ark_api_key="test-ark-key",
        ark_model="glm-4-7-251222",
    )
    monkeypatch.setattr("app.services.ark_client.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.OpenAI", FakeOpenAI)

    client = VolcengineArkClient()
    result = client.generate_structured_text("ping", fallback="fallback")

    assert result.status == "success"
    assert result.value == "ok"
    assert client._client.chat.completions.called is True


def test_volcengine_ark_client_uses_chat_completions_for_json(monkeypatch) -> None:
    captured_kwargs = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured_kwargs.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {"message": type("Message", (), {"content": '{"ok": true}'})()},
                        )
                    ]
                },
            )()

    class FakeOpenAI:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    settings = Settings(
        llm_provider="volcengine",
        ark_api_key="test-ark-key",
        ark_model="glm-4-7-251222",
    )
    monkeypatch.setattr("app.services.ark_client.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.OpenAI", FakeOpenAI)

    client = VolcengineArkClient()
    result = client.generate_json("ping", fallback={"ok": False})

    assert result.status == "success"
    assert result.value == {"ok": True}
    assert captured_kwargs["response_format"] == {"type": "json_object"}


def test_volcengine_ark_client_logs_status(monkeypatch, tmp_path) -> None:
    class FakeCompletions:
        def create(self, **kwargs):
            return type(
                "Response",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {"message": type("Message", (), {"content": '{"ok": true}'})()},
                        )
                    ]
                },
            )()

    class FakeOpenAI:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    settings = Settings(
        llm_provider="volcengine",
        ark_api_key="test-ark-key",
        ark_model="glm-4-7-251222",
        app_log_dir=str(tmp_path),
    )
    monkeypatch.setattr("app.core.logging.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.OpenAI", FakeOpenAI)

    client = VolcengineArkClient()
    result = client.generate_json("ping", fallback={"ok": False})

    assert result.status == "success"
    content = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "llm_call provider=volcengine" in content
    assert "output_preview=" in content


def test_volcengine_ark_client_log_truncates_prompt_and_output_to_1000_chars(monkeypatch, tmp_path) -> None:
    long_output = "o" * 1200

    class FakeCompletions:
        def create(self, **kwargs):
            return type(
                "Response",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {"message": type("Message", (), {"content": long_output})()},
                        )
                    ]
                },
            )()

    class FakeOpenAI:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    settings = Settings(
        llm_provider="volcengine",
        ark_api_key="test-ark-key",
        ark_model="glm-4-7-251222",
        app_log_dir=str(tmp_path),
    )
    monkeypatch.setattr("app.core.logging.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.OpenAI", FakeOpenAI)

    client = VolcengineArkClient()
    client.generate_structured_text("p" * 1200, fallback="fallback")

    content = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert f"prompt_preview={'p' * 1000!r}" in content
    assert f"output_preview={'o' * 1000!r}" in content


def test_llm_client_web_search_uses_volcengine_provider(monkeypatch) -> None:
    settings = Settings(
        llm_provider="volcengine",
        ark_api_key="test-ark-key",
        ark_model="glm-4-7-251222",
    )
    monkeypatch.setattr("app.services.llm_client.get_settings", lambda: settings)

    client = LLMClient()

    assert client.provider_name == "volcengine"
    assert client._provider.__class__.__name__ == "VolcengineArkClient"


def test_kimi_web_search_falls_back_with_clear_message(monkeypatch) -> None:
    settings = Settings(
        llm_provider="kimi",
        kimi_api_key="test-kimi-key",
        kimi_model="kimi-k2-0905-preview",
    )
    monkeypatch.setattr("app.services.kimi_client.get_settings", lambda: settings)

    client = __import__("app.services.kimi_client", fromlist=["KimiClient"]).KimiClient()
    result = client.search_web("调研宠物烘干箱平台", fallback={"platforms": []})

    assert result.status == "fallback"
    assert "web search" in (result.message or "").lower()


def test_volcengine_web_search_returns_platforms_and_evidence(monkeypatch) -> None:
    class FakeResponses:
        def create(self, **kwargs):
            return type(
                "Response",
                (),
                {
                    "output_text": (
                        '{"platforms":[{"platform_name":"京东","platform_domain":"jd.com","platform_type":"marketplace",'
                        '"priority":1,"reason":"搜索命中商品页","search_evidence":[{"query":"宠物烘干箱 京东","title":"京东宠物烘干箱",'
                        '"url":"https://www.jd.com/item/1","snippet":"商品页"}]}]}'
                    )
                },
            )()

    class FakeOpenAI:
        def __init__(self, *args, **kwargs) -> None:
            self.responses = FakeResponses()

    settings = Settings(
        llm_provider="volcengine",
        ark_api_key="test-ark-key",
        ark_model="glm-4-7-251222",
    )
    monkeypatch.setattr("app.services.ark_client.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.ark_client.OpenAI", FakeOpenAI)

    client = VolcengineArkClient()
    result = client.search_web("调研宠物烘干箱平台", fallback={"platforms": []})

    assert result.status == "success"
    assert result.value["platforms"][0]["platform_domain"] == "jd.com"
    assert result.value["platforms"][0]["search_evidence"][0]["url"] == "https://www.jd.com/item/1"
