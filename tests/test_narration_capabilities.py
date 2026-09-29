import unittest
from unittest.mock import patch

from app.routers import narration
from app.services.audio_service import MediaPrerequisiteError


class NarrationCapabilityTests(unittest.TestCase):
    def test_reports_local_readiness_without_remote_calls_or_secret_metadata(self):
        with patch.object(narration, "list_cloned_voices", return_value=[{
            "voice_id": "voice_test", "name": "Dad", "sample": "private-path",
            "profile_verified": True, "secret": "must-not-return",
        }]), patch.object(narration, "is_voice_clone_available", return_value=True), \
                patch.object(narration.narration, "alignment_preflight",
                             side_effect=narration.narration.NarrationError("alignment_unavailable", "Install local model", 503)), \
                patch.object(narration, "require_media_tools"), \
                patch("requests.get", side_effect=AssertionError("No remote capability probe")):
            result = narration.capabilities()
        self.assertTrue(result["provider_configured"])
        self.assertFalse(result["capability_verified"])
        self.assertFalse(result["alignment_available"])
        self.assertTrue(result["media_available"])
        self.assertNotIn("sample", result["voices"][0])
        self.assertNotIn("secret", result["voices"][0])

    def test_missing_encoder_is_reported_before_narration_action(self):
        with patch.object(narration, "list_cloned_voices", return_value=[]), \
                patch.object(narration, "is_voice_clone_available", return_value=False), \
                patch.object(narration.narration, "alignment_preflight", return_value="local-model"), \
                patch.object(narration, "require_media_tools",
                             side_effect=MediaPrerequisiteError("Install FFprobe")):
            result = narration.capabilities()
        self.assertFalse(result["media_available"])
        self.assertEqual(result["media_message"], "Install FFprobe")
