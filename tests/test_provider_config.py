import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.genai.errors import ServerError

from app.config import StudioSettings
from app.services import ai_service


class StructuredProviderTests(unittest.TestCase):
    def test_provider_service_failure_is_distinct_from_missing_credentials(self):
        failure = ai_service._classify_provider_error(ServerError(
            503, {"error": {"code": 503, "message": "private diagnostic"}}
        ))
        self.assertEqual(failure.code, "provider_unavailable")
        self.assertIn("HTTP 503", str(failure))
        self.assertIn("not a missing API key", str(failure))
        self.assertIn("settings were not changed", str(failure))
        self.assertNotIn("private diagnostic", str(failure))

    def test_script_json_and_long_timeout_are_sent_without_changing_model(self):
        settings = StudioSettings(gemini_api_key="test-only", active_model="selected-model")
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text='{"scenes":[]}')
        schema = {"type": "object", "properties": {"scenes": {"type": "array", "items": {"type": "object"}}}}
        with patch.object(ai_service, "load_settings", return_value=settings), \
                patch("google.genai.Client", return_value=client) as factory:
            ai_service.generate_ai_text("synthetic", "system", response_schema=schema, timeout_ms=120_000)
        self.assertEqual(factory.call_args.kwargs["http_options"]["timeout"], 120_000)
        self.assertEqual(factory.call_args.kwargs["http_options"]["retry_options"]["attempts"], 1)
        request = client.models.generate_content.call_args.kwargs
        self.assertEqual(request["model"], "selected-model")
        self.assertEqual(request["config"]["response_json_schema"], schema)
        self.assertEqual(request["config"]["response_mime_type"], "application/json")
        self.assertTrue(request["config"]["automatic_function_calling"]["disable"])
        client.close.assert_called_once()

    def test_one_bounded_outage_retry_can_recover_without_model_fallback(self):
        settings = StudioSettings(gemini_api_key="test-only", active_model="selected-model")
        client = Mock()
        client.models.generate_content.side_effect = [
            ServerError(503, {"error": {"code": 503, "message": "not logged"}}),
            SimpleNamespace(text="recovered"),
        ]
        with patch.object(ai_service, "load_settings", return_value=settings), \
                patch("google.genai.Client", return_value=client), \
                patch.object(ai_service.time, "sleep") as delay:
            self.assertEqual(ai_service.call_gemini("synthetic"), "recovered")
        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertTrue(all(call.kwargs["model"] == "selected-model"
                            for call in client.models.generate_content.call_args_list))
        delay.assert_called_once_with(2.5)
        client.close.assert_called_once()
