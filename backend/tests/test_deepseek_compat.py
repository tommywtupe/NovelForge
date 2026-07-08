import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.endpoints import llm_configs
from app.schemas.llm_config import LLMCapabilityTestRequest, LLMGetModelsRequest
from app.services.ai.core import chat_model_factory, llm_capability_probe


class DeepSeekChatModelFactoryTests(unittest.TestCase):
    @mock.patch("app.services.ai.core.chat_model_factory.llm_config_service.resolve_transport_settings")
    @mock.patch("app.services.ai.core.chat_model_factory.ChatDeepSeek", create=True)
    def test_build_chat_model_uses_chatdeepseek_and_disabled_tool_choice(
        self,
        chat_deepseek_cls: mock.Mock,
        resolve_transport_settings: mock.Mock,
    ) -> None:
        resolve_transport_settings.return_value = {
            "provider": "deepseek",
            "request_base": "https://api.deepseek.com/v1/chat/completions",
            "default_headers": {"User-Agent": "NovelForge/1.0"},
            "api_protocol": "chat_completions",
            "use_responses_api": False,
        }
        chat_deepseek_cls.return_value = object()

        result = chat_model_factory.build_chat_model_from_payload(
            provider="deepseek",
            model_name="deepseek-chat",
            api_key="sk-test",
            api_base="https://api.deepseek.com/v1",
            custom_request_path="/chat/completions",
            user_agent="NovelForge/1.0",
            temperature=0.3,
            max_tokens=1024,
            timeout=30,
            thinking_enabled=True,
            reasoning_effort="high",
        )

        self.assertIs(result, chat_deepseek_cls.return_value)
        kwargs = chat_deepseek_cls.call_args.kwargs
        self.assertEqual(kwargs["model"], "deepseek-chat")
        self.assertEqual(kwargs["api_key"], "sk-test")
        self.assertEqual(kwargs["base_url"], "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(kwargs["default_headers"], {"User-Agent": "NovelForge/1.0"})
        self.assertEqual(kwargs["disabled_params"], {"tool_choice": None})
        self.assertEqual(
            kwargs["extra_body"],
            {"thinking": {"type": "enabled"}, "reasoning_effort": "high"},
        )

    @mock.patch("app.services.ai.core.chat_model_factory.build_chat_model_from_payload")
    @mock.patch("app.services.ai.core.chat_model_factory._get_llm_config")
    def test_build_chat_model_reads_thinking_defaults_from_llm_config(
        self,
        get_llm_config: mock.Mock,
        build_chat_model_from_payload: mock.Mock,
    ) -> None:
        get_llm_config.return_value = SimpleNamespace(
            provider="deepseek",
            model_name="deepseek-reasoner",
            api_key="sk-test",
            api_base="https://api.deepseek.com/v1",
            base_url=None,
            api_protocol="chat_completions",
            custom_request_path="/chat/completions",
            user_agent="NovelForge/1.0",
            thinking=True,
            reasoning_effort="medium",
        )

        chat_model_factory.build_chat_model(
            session=mock.sentinel.session,
            llm_config_id=7,
        )

        kwargs = build_chat_model_from_payload.call_args.kwargs
        self.assertTrue(kwargs["thinking_enabled"])
        self.assertEqual(kwargs["reasoning_effort"], "medium")


class DeepSeekModelsEndpointTests(unittest.IsolatedAsyncioTestCase):
    @mock.patch("app.api.endpoints.llm_configs.build_chat_model_from_payload")
    async def test_connection_test_endpoint_forwards_reasoning_settings(
        self,
        build_chat_model_from_payload: mock.Mock,
    ) -> None:
        model = mock.AsyncMock()
        build_chat_model_from_payload.return_value = model

        await llm_configs.test_llm_connection_endpoint(
            llm_configs.LLMConnectionTest(
                provider="deepseek",
                model_name="deepseek-chat",
                api_base="https://api.deepseek.com/v1",
                api_key="sk-test",
                api_protocol="chat_completions",
                custom_request_path="/chat/completions",
                user_agent="NovelForge/1.0",
                thinking=True,
                reasoning_effort="high",
            )
        )

        kwargs = build_chat_model_from_payload.call_args.kwargs
        self.assertTrue(kwargs["thinking_enabled"])
        self.assertEqual(kwargs["reasoning_effort"], "high")

    @mock.patch("app.api.endpoints.llm_configs.llm_config_service.resolve_transport_settings")
    @mock.patch("app.api.endpoints.llm_configs.httpx.AsyncClient")
    async def test_get_models_endpoint_supports_deepseek(
        self,
        async_client_cls: mock.Mock,
        resolve_transport_settings: mock.Mock,
    ) -> None:
        resolve_transport_settings.return_value = {
            "provider": "deepseek",
            "models_url": "https://api.deepseek.com/models",
            "default_headers": {"User-Agent": "NovelForge/1.0"},
        }
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]
        }
        client = mock.AsyncMock()
        client.get.return_value = response
        async_cm = mock.AsyncMock()
        async_cm.__aenter__.return_value = client
        async_cm.__aexit__.return_value = False
        async_client_cls.return_value = async_cm

        result = await llm_configs.get_models_endpoint(
            LLMGetModelsRequest(
                provider="deepseek",
                api_base="https://api.deepseek.com/v1",
                api_key="sk-test",
                api_protocol="chat_completions",
                models_path="/models",
                user_agent="NovelForge/1.0",
            )
        )

        self.assertEqual(result.data, ["deepseek-chat", "deepseek-reasoner"])


class DeepSeekCapabilityProbeTests(unittest.IsolatedAsyncioTestCase):
    def test_probe_payload_kwargs_forward_reasoning_settings(self) -> None:
        kwargs = llm_capability_probe._payload_kwargs(
            LLMCapabilityTestRequest(
                provider="deepseek",
                model_name="deepseek-chat",
                api_base="https://api.deepseek.com/v1",
                api_key="sk-test",
                api_protocol="chat_completions",
                custom_request_path="/chat/completions",
                user_agent="NovelForge/1.0",
                thinking=True,
                reasoning_effort="high",
            )
        )

        self.assertTrue(kwargs["thinking_enabled"])
        self.assertEqual(kwargs["reasoning_effort"], "high")

    @mock.patch("app.services.ai.core.llm_capability_probe.llm_config_service.resolve_transport_settings")
    @mock.patch("app.services.ai.core.llm_capability_probe.httpx.AsyncClient")
    async def test_probe_models_list_supports_deepseek(
        self,
        async_client_cls: mock.Mock,
        resolve_transport_settings: mock.Mock,
    ) -> None:
        resolve_transport_settings.return_value = {
            "provider": "deepseek",
            "models_url": "https://api.deepseek.com/models",
            "default_headers": {"User-Agent": "NovelForge/1.0"},
        }
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]
        }
        client = mock.AsyncMock()
        client.get.return_value = response
        async_cm = mock.AsyncMock()
        async_cm.__aenter__.return_value = client
        async_cm.__aexit__.return_value = False
        async_client_cls.return_value = async_cm

        result = await llm_capability_probe._probe_models_list(
            LLMCapabilityTestRequest(
                provider="deepseek",
                model_name="deepseek-chat",
                api_base="https://api.deepseek.com/v1",
                api_key="sk-test",
                api_protocol="chat_completions",
                models_path="/models",
                user_agent="NovelForge/1.0",
                test_models_list=True,
            )
        )

        self.assertEqual(result.status, "pass")
        self.assertIn("2 item", result.message)


if __name__ == "__main__":
    unittest.main()
